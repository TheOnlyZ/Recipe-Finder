import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from scraper.catalog import download_catalog, filter_cookbooks
from scraper.downloader import download_text
from scraper.parser import parse_cookbook
from backend.database import init_db, get_session
from backend.models import Book as BookModel, Recipe as RecipeModel

DATA_DIR = Path(__file__).parent.parent / "data"
CATALOG_PATH = DATA_DIR / "pg_catalog.csv"
TEXT_CACHE = DATA_DIR / "texts"


def ensure_dirs():
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    TEXT_CACHE.mkdir(parents=True, exist_ok=True)


def run(max_books: int = 10):
    ensure_dirs()
    init_db()

    print("Step 1: Downloading catalog...")
    download_catalog(CATALOG_PATH)

    print("Step 2: Filtering cookbook entries...")
    books = filter_cookbooks(CATALOG_PATH, max_books=max_books)

    print("Step 3: Downloading texts...")
    all_recipes = []
    for book in books:
        path = download_text(book.id, book.text_url, TEXT_CACHE)
        if not path:
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        recipes = parse_cookbook(text, book.id, book.title)
        for r in recipes:
            r.source_title = book.title
        all_recipes.extend(recipes)

    print("Step 4: Storing in database...")
    session = get_session()
    try:
        for book in books:
            existing = session.query(BookModel).filter_by(gutenberg_id=book.id).first()
            if not existing:
                existing = BookModel(
                    gutenberg_id=book.id,
                    title=book.title,
                    author=book.authors,
                    subjects=book.subjects,
                )
                session.add(existing)
                session.flush()

            for r in all_recipes:
                if r.source_book_id == book.id:
                    recipe_model = RecipeModel(
                        title=r.title,
                        instructions=r.instructions,
                        book_id=existing.id,
                    )
                    recipe_model.set_ingredients(r.ingredients)
                    session.add(recipe_model)

        session.commit()
        print(f"  Stored {len(all_recipes)} recipes in database")
    except Exception as e:
        session.rollback()
        print(f"  Database error: {e}")
        raise
    finally:
        session.close()

    print(f"\nTotal recipes extracted: {len(all_recipes)}")
    return all_recipes


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--max-books", type=int, default=10)
    args = parser.parse_args()
    run(max_books=args.max_books)
