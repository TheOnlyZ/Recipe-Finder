import json
from sqlalchemy import Column, Integer, String, Text, ForeignKey
from sqlalchemy.orm import relationship
from backend.database import Base


class Book(Base):
    __tablename__ = "books"

    id = Column(Integer, primary_key=True, autoincrement=True)
    gutenberg_id = Column(Integer, unique=True, nullable=False)
    title = Column(String(500), nullable=False)
    author = Column(String(500), default="")
    subjects = Column(Text, default="")

    recipes = relationship("Recipe", back_populates="book", cascade="all, delete-orphan")


class Recipe(Base):
    __tablename__ = "recipes"

    id = Column(Integer, primary_key=True, autoincrement=True)
    title = Column(String(500), nullable=False)
    ingredients = Column(Text, default="[]")
    instructions = Column(Text, default="")
    book_id = Column(Integer, ForeignKey("books.id"), nullable=False)

    book = relationship("Book", back_populates="recipes")

    def get_ingredients(self) -> list[str]:
        return json.loads(self.ingredients) if self.ingredients else []

    def set_ingredients(self, items: list[str]):
        self.ingredients = json.dumps(items)
