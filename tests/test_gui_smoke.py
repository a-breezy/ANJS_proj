"""Headless smoke tests for the GUI.  Run from the repo root:

    python -m unittest discover -s tests -v

Qt runs on the "offscreen" platform, so no display is needed.
"""
from __future__ import annotations

import os
import sys
import unittest
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from PySide6.QtTest import QTest  # noqa: E402
from PySide6.QtWidgets import QApplication, QPushButton  # noqa: E402

from gui.app import MainWindow  # noqa: E402
from gui.data import SAMPLE_BOOKS  # noqa: E402
from gui.pages import login as login_module  # noqa: E402
from gui.pages.catalog import UserBookCard  # noqa: E402
from gui.theme import build_qss, theme  # noqa: E402

_app = QApplication.instance() or QApplication([])
_app.setStyleSheet(build_qss(theme.palette))
theme.changed.connect(lambda: _app.setStyleSheet(build_qss(theme.palette)))


def _chip(window: MainWindow, text: str) -> QPushButton:
    return next(b for b in window.guest.home.findChildren(QPushButton) if b.text() == text)


class GuiSmokeTests(unittest.TestCase):
    def setUp(self) -> None:
        theme.set_theme("dark")
        self.win = MainWindow()
        self.win.show()

    def tearDown(self) -> None:
        self.win.close()

    def sign_in_with_password(self, email: str = "jane.doe@example.com") -> None:
        self.win.show_login()
        self.win.login.seg_password.click()
        self.win.login.email.setText(email)
        self.win.login.password.setText("anything")
        self.win.login._submit_password()

    def test_starts_on_guest_home_with_four_bestsellers(self) -> None:
        self.assertIs(self.win.stack.currentWidget(), self.win.guest)
        self.assertEqual(self.win.guest.home.grid.count(), 4)

    def test_category_chip_filters_books(self) -> None:
        _chip(self.win, "Textbooks").click()
        self.assertEqual(self.win.guest.home.grid.count(), 2)
        _chip(self.win, "All").click()
        self.assertEqual(self.win.guest.home.grid.count(), 4)

    def test_search_results_and_empty_state(self) -> None:
        home = self.win.guest.home
        home.search.setText("orchard")
        self.assertEqual(home.grid.count(), 1)
        home.search.setText("zzzz")
        self.assertEqual(home.grid.count(), 0)
        self.assertFalse(home.empty.isHidden())

    def test_sign_in_buttons_open_login_and_back_returns(self) -> None:
        self.win.guest.nav._buttons["signin"].click()
        self.assertIs(self.win.stack.currentWidget(), self.win.login)
        self.win.login.back.click()
        self.assertIs(self.win.stack.currentWidget(), self.win.guest)

    def test_password_validation_and_success(self) -> None:
        self.win.show_login()
        self.win.login.seg_password.click()
        self.win.login._submit_password()
        self.assertFalse(self.win.login.pw_error.isHidden())
        self.assertIs(self.win.stack.currentWidget(), self.win.login)

        self.sign_in_with_password()
        self.assertIs(self.win.stack.currentWidget(), self.win.user)
        self.assertEqual(self.win.user.home.hello.text(), "Hi, Jane")

    def test_face_scan_signs_in(self) -> None:
        original = login_module.SCAN_MS
        login_module.SCAN_MS = 30
        try:
            self.win.show_login()
            self.win.login.scan_btn.click()
            self.assertFalse(self.win.login.scan_btn.isEnabled())
            QTest.qWait(200)
        finally:
            login_module.SCAN_MS = original
        self.assertIs(self.win.stack.currentWidget(), self.win.user)

    def test_add_to_cart_updates_badge_and_cart_page(self) -> None:
        self.sign_in_with_password()
        card = self.win.user.home.findChildren(UserBookCard)[0]
        card.findChild(QPushButton).click()
        self.assertEqual(len(self.win.session.cart), 1)
        self.assertEqual(self.win.user.home.cart_btn._count, 1)
        self.win.user.show_tab("cart")
        self.assertTrue(self.win.user.cart.checkout.isEnabled())
        self.win.session.remove_from_cart(0)
        self.assertFalse(self.win.user.cart.checkout.isEnabled())

    def test_theme_switch_after_grids_rebuilt(self) -> None:
        _chip(self.win, "Fiction").click()  # rebuilds the grid, deleting old cards
        theme.set_theme("mint")
        self.assertIn("#E6F4EC", _app.styleSheet())
        self.win.guest.home.grab()  # force a paint with the new palette
        theme.set_theme("dark")
        self.assertIn("#0F1830", _app.styleSheet())

    def test_sign_out_clears_session(self) -> None:
        self.sign_in_with_password()
        self.win.session.add_to_cart(SAMPLE_BOOKS[0])
        self.win.user.account.sign_out_requested.emit()
        self.assertIs(self.win.stack.currentWidget(), self.win.guest)
        self.assertIsNone(self.win.session.user)
        self.assertEqual(self.win.session.cart, [])


if __name__ == "__main__":
    unittest.main()
