"""Book catalogue and models used by the GUI.

The catalogue is ``catalog/catalog.json``, built from Project Gutenberg and
Open Library by ``scripts/build_catalog.py``. Without that file (or with
``ANJS_CATALOG=sample``) the app falls back to the invented SAMPLE_BOOKS below,
which is what the tests use. Accounts and orders live in :mod:`gui.store`.
"""
from __future__ import annotations

import json
import os
from dataclasses import dataclass
from datetime import date
from pathlib import Path

CATALOG_DIR = Path(__file__).resolve().parents[1] / "catalog"
CATALOG_FILE = CATALOG_DIR / "catalog.json"


@dataclass(frozen=True)
class Book:
    id: int
    title: str
    author: str
    price: float
    category: str
    cover: int  # index into the theme's cover colours
    description: str = ""
    rating: float | None = None  # Open Library average out of 5; None = not rated
    rating_count: int = 0
    year: int | None = None  # first published
    subjects: tuple[str, ...] = ()
    downloads: int = 0  # Gutenberg downloads; used as "bestseller" order
    cover_image: str = ""  # file in catalog/covers, "" = draw a placeholder cover

    @property
    def cover_path(self) -> Path | None:
        path = CATALOG_DIR / "covers" / self.cover_image if self.cover_image else None
        return path if path is not None and path.is_file() else None

    @property
    def price_text(self) -> str:
        return f"${self.price:.2f}"

    @property
    def rating_text(self) -> str:
        if self.rating is None:
            return "No ratings yet"
        noun = "rating" if self.rating_count == 1 else "ratings"
        return f"{self.rating:.1f} · {self.rating_count:,} {noun}"


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


# Listed in bestseller order. Descriptions are placeholders too.
SAMPLE_BOOKS = [
    Book(1, "The Quiet Orchard", "Mara Ellison", 14.99, "Fiction", 0,
         "After her grandmother's death, a botanist returns to the family apple orchard and finds a decades-old ledger that rewrites everything she knew about the town and the women who kept it running."),
    Book(2, "Small Systems", "Priya Raman", 18.00, "Non-fiction", 1,
         "A practical look at how small habits, tools and feedback loops shape the way teams and households actually work, with case studies from kitchens, clinics and start-ups."),
    Book(3, "Discrete Math Basics", "Daniel Whitford", 64.00, "Textbooks", 2,
         "An introductory textbook covering logic, sets, proofs, combinatorics, graphs and recurrence relations, with worked examples and exercises at the end of every chapter."),
    Book(4, "Lanterns at Low Tide", "Theo Marchetti", 16.50, "Fiction", 3,
         "A lighthouse keeper's son and a smuggler's daughter cross paths on a fog-bound island over one long summer, in a quiet novel about loyalty, tides and leaving home."),
    Book(5, "The Slow Map", "Callum Reyes", 21.95, "Non-fiction", 0,
         "A travel writer walks the old pilgrim and trade routes of three continents at three miles an hour and asks what we lose when we only ever arrive."),
    Book(6, "Paper Kingdoms", "Ines Okafor", 12.99, "Fiction", 1,
         "Two siblings build an imaginary kingdom out of library books and cardboard, until the games start spilling into their very real neighbourhood."),
    Book(7, "Field Notes on Focus", "June Abara", 17.50, "Non-fiction", 2,
         "Short, evidence-based chapters on attention, rest and deep work, with exercises for building a focus routine that survives a busy week."),
    Book(8, "Data Structures Lab", "Lina Cho", 58.75, "Textbooks", 3,
         "A hands-on lab manual for arrays, linked lists, stacks, queues, trees, hash tables and graphs, with step-by-step programming assignments in Python."),
]


SAMPLE_CATEGORIES = ["Fiction", "Non-fiction", "Textbooks"]


def load_catalog(path: Path = CATALOG_FILE) -> tuple[list[Book], list[str]]:
    """Books (most downloaded first) and category names from ``catalog.json``."""
    raw = json.loads(path.read_text(encoding="utf-8"))
    books = [
        Book(
            id=r["id"],
            title=r["title"],
            author=r["author"],
            price=r["price"],
            category=r["category"],
            cover=r["id"] % 4,
            description=r.get("description", ""),
            rating=r.get("rating"),
            rating_count=r.get("rating_count", 0),
            year=r.get("year"),
            subjects=tuple(r.get("subjects", ())),
            downloads=r.get("downloads", 0),
            cover_image=r.get("cover_image", ""),
        )
        for r in raw["books"]
    ]
    # Most downloaded first; Open Library's rating count breaks ties (and stands in
    # when Gutendex was down during the import and every download count is 0).
    books.sort(key=lambda b: (b.downloads, b.rating_count), reverse=True)
    return books, raw["categories"]


if os.environ.get("ANJS_CATALOG", "") != "sample" and CATALOG_FILE.is_file():
    BOOKS, _categories = load_catalog()
else:
    BOOKS, _categories = SAMPLE_BOOKS, SAMPLE_CATEGORIES
CATEGORIES = ["All", *_categories]
_BY_ID = {b.id: b for b in BOOKS}


def book_by_id(book_id: int) -> Book | None:
    return _BY_ID.get(book_id)


def books_in(category: str = "All") -> list[Book]:
    if category == "All":
        return list(BOOKS)
    return [b for b in BOOKS if b.category == category]


def bestsellers(category: str = "All", limit: int | None = None) -> list[Book]:
    books = books_in(category)
    return books if limit is None else books[:limit]


def recommended(count: int = 3, exclude: set[int] | None = None) -> list[Book]:
    """Best-rated books with enough ratings to trust, topped up from the catalog.

    ``exclude`` holds book ids (e.g. ones already bought) that must not appear.
    """
    skip = exclude or set()
    pool = [b for b in BOOKS if b.id not in skip]
    rated = [b for b in pool if b.rating is not None and b.rating_count >= 20]
    rated.sort(key=lambda b: b.rating, reverse=True)
    picks = rated[:count]
    picks += [b for b in pool if b not in picks][: count - len(picks)]
    return picks


def search(query: str, category: str = "All") -> list[Book]:
    from .search import catalog_index

    hits = catalog_index().search(query)
    return hits if category == "All" else [b for b in hits if b.category == category]
