"""Home recommendations: three cards, refreshed on sign-in and purchases."""
from __future__ import annotations

import os
import sys
import tempfile
import unittest
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("ANJS_CATALOG", "sample")
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from PySide6.QtWidgets import QApplication  # noqa: E402

from gui import auth, data  # noqa: E402
from gui.app import MainWindow  # noqa: E402
from gui.pages.catalog import RecoCard  # noqa: E402
from gui.store import Store  # noqa: E402

_app = QApplication.instance() or QApplication([])


class RecommendedDataTests(unittest.TestCase):
    def test_default_count_is_three(self) -> None:
        self.assertEqual(len(data.recommended()), 3)

    def test_exclude_removes_books_and_still_fills(self) -> None:
        first = data.recommended()
        again = data.recommended(exclude={first[0].id})
        self.assertEqual(len(again), 3)
        self.assertNotIn(first[0].id, {b.id for b in again})


class HomeRecommendationTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.store = Store(Path(self._tmp.name) / "store.json")
        self.win = MainWindow(self.store)
        self.home = self.win.shell.home

    def tearDown(self) -> None:
        self.win.close()
        self._tmp.cleanup()

    def _reco_ids(self) -> list[int]:
        return [c.book.id for c in self.home.reco_row.findChildren(RecoCard)]

    def test_purchased_book_leaves_recommendations(self) -> None:
        user = auth.register(self.store, "Jane Doe", "jane@example.com", "correct horse")
        self.win.session.sign_in(user)
        before = self._reco_ids()
        self.assertEqual(len(before), 3)
        book = next(b for b in data.BOOKS if b.id == before[0])
        self.win.session.add_to_cart(book)
        self.assertIsNotNone(self.win.session.checkout())
        after = self._reco_ids()
        self.assertEqual(len(after), 3)
        self.assertNotIn(book.id, after)


if __name__ == "__main__":
    unittest.main()
