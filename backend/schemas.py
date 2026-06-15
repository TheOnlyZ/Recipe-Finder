from pydantic import BaseModel


class RecipeOut(BaseModel):
    id: int
    title: str
    ingredients: list[str]
    instructions: str
    book_id: int

    class Config:
        from_attributes = True


class BookOut(BaseModel):
    id: int
    gutenberg_id: int
    title: str
    author: str
    recipe_count: int = 0


class RecipeSearchResult(BaseModel):
    recipe: RecipeOut
    match_count: int
    total_ingredients: int
    match_ratio: float
