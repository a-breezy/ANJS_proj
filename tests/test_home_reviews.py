"""Home catalog cards open the reviews dialog."""
from __future__ import annotations

import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("ANJS_CATALOG", "sample")
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from PySide6.QtWidgets import QApplication, QPushButton  # noqa: E402

from gui import auth  # noqa: E402
from gui.app import MainWindow  # noqa: E402
from gui.pages.catalog import GuestBookCard, UserBookCard  # noqa: E402
from gui.store import Store  # noqa: E402

_app = QApplication.instance() or QApplication([])


class HomeReviewsTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.store = Store(Path(self._tmp.name) / "store.json")
        self.win = MainWindow(self.store)
        self.home = self.win.shell.home

    def tearDown(self) -> None:
        self.win.close()
        self._tmp.cleanup()

    def _click_reviews(self, card_type) -> None:
        card = self.home.grid.findChildren(card_type)[0]
        btn = next(b for b in card.findChildren(QPushButton) if b.text() == "Reviews & Ratings")
        with mock.patch("gui.pages.home.BookReviewsDialog") as dialog:
            btn.click()
        dialog.assert_called_once()
        self.assertIs(dialog.call_args.args[0], card.book)
        dialog.return_value.exec.assert_called_once()

    def test_guest_card_opens_reviews(self) -> None:
        self._click_reviews(GuestBookCard)

    def test_user_card_opens_reviews(self) -> None:
        user = auth.register(self.store, "Jane Doe", "jane@example.com", "correct horse")
        self.win.session.sign_in(user)
        self._click_reviews(UserBookCard)


if __name__ == "__main__":
    unittest.main()
