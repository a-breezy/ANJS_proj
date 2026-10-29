"""Sample data and models used by the GUI.

Everything here is PLACEHOLDER data (invented titles and authors) so the
screens have something to show. Replace the functions in this module with
calls to the real catalogue backend once it exists. Accounts and orders are
not sample data any more; they live in :mod:`gui.store`.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date

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
    role: str = "RC"

    @property
    def initial(self) -> str:
        return (self.name[:1] or "?").upper()

    @property
    def is_admin(self) -> bool:
        return self.role == "SU"

    @property
    def is_vip(self) -> bool:
        return self.role == "VC"

    @property
    def discount(self) -> float:
        return 0.10 if self.is_vip else 0.0

    @property
    def can_use_ai(self) -> bool:
        return self.role in ("RC", "VC", "SU")

    @property
    def is_visitor(self) -> bool:
        return self.role == "VS"

    @property
    def can_manage_books(self) -> bool:
        return self.role == "SU"

    @property
    def can_view_history(self) -> bool:
        return self.role in ("RC", "VC", "SU")

@dataclass(frozen=True)
class Order:
    number: int
    placed: str  # ISO date
    status: str
    progress: float  # 0.0 - 1.0
    book_ids: tuple[int, ...]
    total: float = 0.0
    discount_amount: float = 0.0

    @classmethod
    def from_record(cls, record: dict) -> "Order":
        return cls(
            record["number"],
            record["placed"],
            record["status"],
            record["progress"],
            tuple(record["book_ids"]),
            record.get("total", 0.0),
            record.get("discount_amount", 0.0),
        )

    @property
    def books(self) -> list[Book]:
        return [b for b in map(book_by_id, self.book_ids) if b is not None]

    @property
    def active(self) -> bool:
        return self.status != "delivered"

    @property
    def placed_text(self) -> str:
        d = date.fromisoformat(self.placed)
        return f"{d:%b} {d.day}, {d.year}"


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


def book_by_id(book_id: int) -> Book | None:
    return next((b for b in SAMPLE_BOOKS if b.id == book_id), None)


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
