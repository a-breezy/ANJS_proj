"""Headless smoke tests for the GUI.  Run from the repo root:

    python -m unittest discover -s tests -v

Qt runs on the "offscreen" platform, so no display is needed. Each test gets a
fresh, empty account store in a temporary folder, and the chat tests replace
the LLM with a fake, so nothing here needs Ollama running.
"""
from __future__ import annotations

import os
import sys
import tempfile
import unittest
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from PySide6.QtTest import QTest  # noqa: E402
from PySide6.QtWidgets import QApplication, QPushButton  # noqa: E402

from gui import auth, llm  # noqa: E402
from gui.app import MainWindow  # noqa: E402
from gui.data import SAMPLE_BOOKS  # noqa: E402
from gui.pages import login as login_module  # noqa: E402
from gui.pages.catalog import GuestBookCard, UserBookCard, columns_for  # noqa: E402
from gui.store import Store  # noqa: E402
from gui.theme import build_qss, theme  # noqa: E402

_app = QApplication.instance() or QApplication([])
_app.setStyleSheet(build_qss(theme.palette))
theme.changed.connect(lambda: _app.setStyleSheet(build_qss(theme.palette)))

PASSWORD = "correct horse"


def _chip(window: MainWindow, text: str) -> QPushButton:
    return next(b for b in window.shell.home.findChildren(QPushButton) if b.text() == text)


def _wait_until(condition, timeout_ms: int = 2000) -> None:
    waited = 0
    while not condition() and waited < timeout_ms:
        QTest.qWait(20)
        waited += 20


class GuiSmokeTests(unittest.TestCase):
    def setUp(self) -> None:
        theme.set_theme("dark")
        self._tmp = tempfile.TemporaryDirectory()
        self.store = Store(Path(self._tmp.name) / "store.json")
        self.win = MainWindow(self.store)
        self.win.show()

    def tearDown(self) -> None:
        self.win.close()
        self._tmp.cleanup()

    @property
    def home(self):
        return self.win.shell.home

    def sign_up(self, name: str = "Jane Doe", email: str = "jane.doe@example.com") -> None:
        self.win.show_signup()
        page = self.win.signup
        page.name.setText(name)
        page.email.setText(email)
        page.password.setText(PASSWORD)
        page.confirm.setText(PASSWORD)
        page.submit.click()

    def sign_in_with_password(self, email: str = "jane.doe@example.com", password: str = PASSWORD) -> None:
        self.win.show_login()
        self.win.login.seg_password.click()
        self.win.login.email.setText(email)
        self.win.login.password.setText(password)
        self.win.login._submit_password()

    # --- landing page -----------------------------------------------------
    def test_landing_page_shows_no_personal_info(self) -> None:
        self.assertIs(self.win.stack.currentWidget(), self.win.shell)
        self.assertIsNone(self.win.session.user)
        self.assertEqual(self.home.grid.count(), 4)
        self.assertEqual(len(self.home.grid.findChildren(GuestBookCard)), 4)
        self.assertEqual(self.home.grid.findChildren(UserBookCard), [])
        self.assertTrue(self.home.user_header.isHidden())
        self.assertTrue(self.home.order_card.isHidden())
        self.assertTrue(self.home.reco_box.isHidden())
        self.assertFalse(self.home.guest_header.isHidden())
        self.assertEqual(self.win.shell.nav.keys(), ["home", "search", "ask", "signin"])

    def test_members_only_tabs_send_visitors_to_sign_in(self) -> None:
        self.win.shell.show_tab("cart")
        self.assertIs(self.win.stack.currentWidget(), self.win.login)

    def test_category_chip_filters_books(self) -> None:
        _chip(self.win, "Textbooks").click()
        self.assertEqual(self.home.grid.count(), 2)
        _chip(self.win, "All").click()
        self.assertEqual(self.home.grid.count(), 4)

    def test_search_results_and_empty_state(self) -> None:
        self.home.search.setText("orchard")
        self.assertEqual(self.home.grid.count(), 1)
        self.home.search.setText("zzzz")
        self.assertEqual(self.home.grid.count(), 0)
        self.assertFalse(self.home.empty.isHidden())

    # --- responsive layout ------------------------------------------------
    def test_breakpoints(self) -> None:
        self.assertEqual([columns_for(w) for w in (360, 539, 540, 759, 760, 1400)], [2, 2, 3, 3, 4, 4])

    def test_grid_columns_follow_window_width(self) -> None:
        for width, columns in ((400, 2), (640, 3), (1100, 4)):
            self.win.resize(width, 800)
            QTest.qWait(50)
            self.assertEqual(self.home.grid.columns, columns, f"window width {width}")

    # --- accounts ---------------------------------------------------------
    def test_sign_in_buttons_open_login_and_back_returns(self) -> None:
        self.win.shell.nav._buttons["signin"].click()
        self.assertIs(self.win.stack.currentWidget(), self.win.login)
        self.win.login.back.click()
        self.assertIs(self.win.stack.currentWidget(), self.win.shell)

    def test_unknown_account_cannot_sign_in(self) -> None:
        self.sign_in_with_password()
        self.assertIs(self.win.stack.currentWidget(), self.win.login)
        self.assertFalse(self.win.login.pw_error.isHidden())

    def test_sign_up_then_sign_in(self) -> None:
        self.win.show_login()
        self.win.login.sign_up_requested.emit()
        self.assertIs(self.win.stack.currentWidget(), self.win.signup)

        self.sign_up()
        self.assertIs(self.win.stack.currentWidget(), self.win.shell)
        self.assertEqual(self.home.hello.text(), "Hi, Jane")
        self.assertFalse(self.home.user_header.isHidden())
        self.assertTrue(self.home.guest_header.isHidden())
        self.assertTrue(self.home.order_card.isHidden())  # no orders yet
        self.assertEqual(self.win.shell.nav.keys(), ["home", "search", "ask", "cart", "orders", "account"])

        self.win.shell.account.sign_out_requested.emit()
        self.sign_in_with_password(password="wrong password")
        self.assertIs(self.win.stack.currentWidget(), self.win.login)
        self.sign_in_with_password()
        self.assertIs(self.win.stack.currentWidget(), self.win.shell)

    def test_sign_up_validation(self) -> None:
        self.win.show_signup()
        page = self.win.signup
        page.submit.click()
        self.assertEqual(page.error.text(), "Enter your name.")
        page.name.setText("Jane")
        page.email.setText("jane@example.com")
        page.password.setText("short")
        page.confirm.setText("short")
        page.submit.click()
        self.assertIn("at least", page.error.text())
        page.password.setText(PASSWORD)
        page.submit.click()
        self.assertEqual(page.error.text(), "The passwords don't match.")

        self.sign_up(email="jane@example.com")
        with self.assertRaises(auth.AuthError):
            auth.register(self.store, "Other Jane", "JANE@example.com", PASSWORD)

    def test_password_is_not_stored_in_plain_text(self) -> None:
        self.sign_up()
        self.assertNotIn(PASSWORD, self.store.path.read_text())

    def test_face_scan_does_not_sign_in_without_enrolled_face(self) -> None:
        original = login_module.SCAN_MS
        login_module.SCAN_MS = 30
        try:
            self.win.show_login()
            self.win.login.scan_btn.click()
            self.assertFalse(self.win.login.scan_btn.isEnabled())
            QTest.qWait(200)
        finally:
            login_module.SCAN_MS = original
        self.assertIs(self.win.stack.currentWidget(), self.win.login)

    # --- cart, orders and history ----------------------------------------
    def test_add_to_cart_updates_badge_and_cart_page(self) -> None:
        self.sign_up()
        card = self.home.grid.findChildren(UserBookCard)[0]
        card.findChild(QPushButton).click()
        self.assertEqual(len(self.win.session.cart), 1)
        self.assertEqual(self.home.cart_btn._count, 1)
        self.win.shell.show_tab("cart")
        self.assertTrue(self.win.shell.cart.checkout.isEnabled())
        self.win.session.remove_from_cart(0)
        self.assertFalse(self.win.shell.cart.checkout.isEnabled())

    def test_checkout_creates_tracked_order_and_history(self) -> None:
        self.sign_up()
        self.win.session.add_to_cart(SAMPLE_BOOKS[0])
        self.win.session.add_to_cart(SAMPLE_BOOKS[2])
        self.win.shell.show_tab("cart")
        self.win.shell.cart.checkout.click()

        self.assertEqual(self.win.session.cart, [])
        self.assertEqual(self.win.shell.current_tab(), "orders")
        orders = self.win.shell.orders
        self.assertEqual(orders.tabs.current, "tracking")
        self.assertEqual(orders.tracking_list.count(), 1)
        self.assertFalse(self.home.order_card.isHidden())
        self.assertIn("#1001", self.home.order_card.title.text())

        orders.show_tab("history")
        self.assertEqual(orders.history_list.count(), 2)
        self.assertTrue(orders.history_empty.isHidden())

        # Orders persist across sessions and stay private to their owner.
        self.win.shell.account.sign_out_requested.emit()
        self.assertTrue(self.home.order_card.isHidden())
        self.sign_up(name="Sam Lee", email="sam@example.com")
        self.assertEqual(self.win.session.purchases, [])
        self.win.shell.account.sign_out_requested.emit()
        self.sign_in_with_password()
        self.assertEqual(len(self.win.session.purchases), 2)

    def test_sign_out_clears_session(self) -> None:
        self.sign_up()
        self.win.session.add_to_cart(SAMPLE_BOOKS[0])
        self.win.shell.show_tab("account")
        self.win.shell.account.sign_out_requested.emit()
        self.assertIs(self.win.stack.currentWidget(), self.win.shell)
        self.assertEqual(self.win.shell.current_tab(), "home")
        self.assertIsNone(self.win.session.user)
        self.assertEqual(self.win.session.cart, [])
        self.assertFalse(self.home.guest_header.isHidden())

    # --- chat -------------------------------------------------------------
    def test_chat_streams_reply_with_catalog_context(self) -> None:
        seen = {}

        def fake_stream(messages, **_kwargs):
            seen["messages"] = messages
            yield "Try "
            yield "*The Quiet Orchard*."

        original, llm.stream_chat = llm.stream_chat, fake_stream
        try:
            chat = self.win.shell.chat
            self.win.shell.show_tab("ask")
            chat.input.setText("Something gentle")
            chat.send_btn.click()
            self.assertTrue(chat.busy)
            _wait_until(lambda: not chat.busy)
        finally:
            llm.stream_chat = original
        self.assertFalse(chat.busy)
        self.assertEqual(seen["messages"][0]["role"], "system")
        self.assertIn("The Quiet Orchard", seen["messages"][0]["content"])
        self.assertEqual(seen["messages"][-1], {"role": "user", "content": "Something gentle"})
        self.assertEqual(chat._history[-1], {"role": "assistant", "content": "Try *The Quiet Orchard*."})

    def test_chat_shows_error_when_model_unreachable(self) -> None:
        def failing_stream(messages, **_kwargs):
            raise llm.LLMError("Can't reach the local model")
            yield  # pragma: no cover

        original, llm.stream_chat = llm.stream_chat, failing_stream
        try:
            chat = self.win.shell.chat
            chat.send("Hello")
            _wait_until(lambda: not chat.busy)
        finally:
            llm.stream_chat = original
        self.assertEqual(chat._history, [])
        self.assertTrue(chat.send_btn.isEnabled())

    # --- theme ------------------------------------------------------------
    def test_theme_switch_after_grids_rebuilt(self) -> None:
        _chip(self.win, "Fiction").click()  # rebuilds the grid, deleting old cards
        theme.set_theme("mint")
        self.assertIn("#E6F4EC", _app.styleSheet())
        self.home.grab()  # force a paint with the new palette
        theme.set_theme("dark")
        self.assertIn("#0F1830", _app.styleSheet())


if __name__ == "__main__":
    unittest.main()
