import re
import mimetypes
from pathlib import Path
from fastapi import FastAPI, Query
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware

from backend.database import init_db, get_session
from backend.models import Book, Recipe
from backend.schemas import RecipeOut, BookOut, RecipeSearchResult

FRONTEND_DIR = Path(__file__).parent.parent / "frontend"

app = FastAPI(title="Recipe Recommender")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def startup():
    init_db()


def _find_ingredient_words(ingredients: list[str]) -> set[str]:
    words = set()
    for line in ingredients:
        parts = re.split(r"[\s,;]+", line.lower())
        for p in parts:
            p = p.strip(".,;:'\"")
            if p and not p[0].isdigit():
                words.add(p)
    return words


@app.get("/api/books", response_model=list[BookOut])
def list_books():
    session = get_session()
    try:
        books = session.query(Book).all()
        result = []
        for b in books:
            result.append(
                BookOut(
                    id=b.id,
                    gutenberg_id=b.gutenberg_id,
                    title=b.title,
                    author=b.author,
                    recipe_count=len(b.recipes),
                )
            )
        return result
    finally:
        session.close()


@app.get("/api/recipes/{recipe_id}", response_model=RecipeOut)
def get_recipe(recipe_id: int):
    session = get_session()
    try:
        recipe = session.query(Recipe).filter(Recipe.id == recipe_id).first()
        if not recipe:
            from fastapi import HTTPException
            raise HTTPException(status_code=404, detail="Recipe not found")
        return RecipeOut(
            id=recipe.id,
            title=recipe.title,
            ingredients=recipe.get_ingredients(),
            instructions=recipe.instructions,
            book_id=recipe.book_id,
        )
    finally:
        session.close()


@app.get("/api/search", response_model=list[RecipeSearchResult])
def search_recipes(
    ingredients: str = Query("", description="Comma-separated ingredients"),
    min_match: float = Query(0.0, ge=0.0, le=1.0),
    limit: int = Query(100, ge=1, le=1000),
):
    session = get_session()
    try:
        query_terms = set(
            t.strip().lower() for t in ingredients.split(",") if t.strip()
        )
        if not query_terms:
            return []

        recipes = session.query(Recipe).all()
        results = []

        for r in recipes:
            recipe_ings = r.get_ingredients()
            recipe_words = _find_ingredient_words(recipe_ings)

            instr_lower = r.instructions.lower()
            matches = query_terms & recipe_words

            full_matches = set()
            for qt in query_terms:
                if qt in recipe_words:
                    full_matches.add(qt)
                elif qt in instr_lower:
                    full_matches.add(qt)

            match_count = len(full_matches)
            ratio = match_count / len(query_terms)

            if ratio < min_match or match_count == 0:
                continue

            results.append(
                RecipeSearchResult(
                    recipe=RecipeOut(
                        id=r.id,
                        title=r.title,
                        ingredients=recipe_ings,
                        instructions=r.instructions,
                        book_id=r.book_id,
                    ),
                    match_count=match_count,
                    total_ingredients=len(recipe_ings),
                    match_ratio=round(ratio, 2),
                )
            )

        results.sort(key=lambda x: (-x.match_count, -x.match_ratio))
        return results[:limit]
    finally:
        session.close()


@app.get("/api/recipes", response_model=list[RecipeOut])
def list_recipes():
    session = get_session()
    try:
        recipes = session.query(Recipe).all()
        return [
            RecipeOut(
                id=r.id,
                title=r.title,
                ingredients=r.get_ingredients(),
                instructions=r.instructions,
                book_id=r.book_id,
            )
            for r in recipes
        ]
    finally:
        session.close()


@app.get("/{path:path}", include_in_schema=False)
def serve_frontend(path: str):
    if not FRONTEND_DIR.exists():
        from fastapi import HTTPException
        raise HTTPException(status_code=404)
    if not path:
        path = "index.html"
    file_path = FRONTEND_DIR / path
    if file_path.is_file():
        return FileResponse(str(file_path))
    index = FRONTEND_DIR / "index.html"
    if index.exists():
        return HTMLResponse(index.read_text(encoding="utf-8"))
    from fastapi import HTTPException
    raise HTTPException(status_code=404)
