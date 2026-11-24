"""Review, moderation and order-list tests: no PySide, camera, or network needed."""
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

os.environ.setdefault("ANJS_CATALOG", "sample")

from gui import data
from gui.reviews import ReviewService
from gui.store import Store

# Always the real catalog, whatever ANJS_CATALOG says for the rest of the suite.
REAL_BOOKS, _ = data.load_catalog()


class ReviewTestCase(unittest.TestCase):
    def setUp(self):
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        self.path = Path(folder.name) / "store.json"
        self.store = Store(self.path)
        self.service = ReviewService(self.store)
        patches = [
            mock.patch.object(data, "BOOKS", REAL_BOOKS),
            mock.patch.object(data, "_BY_ID", {b.id: b for b in REAL_BOOKS}),
        ]
        for p in patches:
            p.start()
            self.addCleanup(p.stop)

    def visitor_reviews(self, book, stars_list):
        for stars in stars_list:
            self.service.submit_review(book.id, "Visitor", None, stars, "ok")


class OrderListTests(ReviewTestCase):
    def test_order_lists_use_real_catalog(self):
        low, high, few = REAL_BOOKS[5], REAL_BOOKS[6], REAL_BOOKS[7]
        self.visitor_reviews(low, [1] * 4)
        self.visitor_reviews(high, [5] * 4)
        self.visitor_reviews(few, [1] * 3)
        self.assertEqual([b.id for b, _, _ in self.service.no_order_books()], [low.id])
        self.assertEqual([b.id for b, _, _ in self.service.to_order_books()], [high.id])

    def test_boundaries_are_strict(self):
        a, b = REAL_BOOKS[8], REAL_BOOKS[9]
        self.visitor_reviews(a, [1, 3, 1, 3])  # avg exactly 2.0
        self.visitor_reviews(b, [5, 3, 5, 3])  # avg exactly 4.0
        self.assertEqual(self.service.no_order_books(), [])
        self.assertEqual(self.service.to_order_books(), [])


if __name__ == "__main__":
    unittest.main()
