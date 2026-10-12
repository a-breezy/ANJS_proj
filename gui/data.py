"""Sample data and models used by the GUI.

Everything here is PLACEHOLDER data (invented titles and authors) so the
screens have something to show. Replace the functions in this module with
calls to the real catalogue / orders backend once it exists.
"""
from __future__ import annotations

from dataclasses import dataclass

CATEGORIES = ["All", "Fiction", "Non-fiction", "Textbooks"]


@dataclass(frozen=True)
class Book:
    id: int
    title: str
    author: str
    price: float
    category: str
    cover: int  # index into the theme's cover colours

    @property
    def price_text(self) -> str:
        return f"${self.price:.2f}"


@dataclass(frozen=True)
class User:
    name: str
    email: str

    @property
    def initial(self) -> str:
        return (self.name[:1] or "?").upper()


@dataclass(frozen=True)
class Order:
    number: int
    status: str
    progress: float  # 0.0 - 1.0


# Listed in bestseller order.
SAMPLE_BOOKS = [
    Book(1, "The Quiet Orchard", "Mara Ellison", 14.99, "Fiction", 0),
    Book(2, "Small Systems", "Priya Raman", 18.00, "Non-fiction", 1),
    Book(3, "Discrete Math Basics", "Daniel Whitford", 64.00, "Textbooks", 2),
    Book(4, "Lanterns at Low Tide", "Theo Marchetti", 16.50, "Fiction", 3),
    Book(5, "The Slow Map", "Callum Reyes", 21.95, "Non-fiction", 0),
    Book(6, "Paper Kingdoms", "Ines Okafor", 12.99, "Fiction", 1),
    Book(7, "Field Notes on Focus", "June Abara", 17.50, "Non-fiction", 2),
    Book(8, "Data Structures Lab", "Lina Cho", 58.75, "Textbooks", 3),
]

SAMPLE_ORDER = Order(number=1042, status="on the way", progress=0.6)


def books_in(category: str = "All") -> list[Book]:
    if category == "All":
        return list(SAMPLE_BOOKS)
    return [b for b in SAMPLE_BOOKS if b.category == category]


def bestsellers(category: str = "All", limit: int = 4) -> list[Book]:
    return books_in(category)[:limit]


def recommended() -> list[Book]:
    by_id = {b.id: b for b in SAMPLE_BOOKS}
    return [by_id[i] for i in (2, 1, 4, 5)]


def search(query: str, category: str = "All") -> list[Book]:
    q = query.strip().lower()
    return [b for b in books_in(category) if q in b.title.lower() or q in b.author.lower()]
