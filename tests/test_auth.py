"""Password authentication tests (suspension must not leak before the password check)."""
import os
import tempfile
import unittest
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("ANJS_CATALOG", "sample")

from gui import auth
from gui.store import Store

PASSWORD = "correct-horse"


class AuthPasswordTests(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.addCleanup(self.folder.cleanup)
        self.store = Store(Path(self.folder.name) / "store.json")
        auth.register(self.store, "Sam Student", "sam@example.com", PASSWORD)

    def _suspend(self):
        self.store.update_user("sam@example.com", lambda r: r.__setitem__("suspended", True))

    def test_wrong_password_suspended_returns_none(self):
        self._suspend()
        self.assertIsNone(auth.authenticate_password(self.store, "sam@example.com", "wrong-password"))

    def test_right_password_suspended_raises(self):
        self._suspend()
        with self.assertRaises(auth.AuthError) as ctx:
            auth.authenticate_password(self.store, "sam@example.com", PASSWORD)
        self.assertIn("suspended", str(ctx.exception).lower())

    def test_right_password_active_returns_user_with_role(self):
        self.store.set_role("sam@example.com", "SU")
        user = auth.authenticate_password(self.store, "sam@example.com", PASSWORD)
        self.assertEqual(user.email, "sam@example.com")
        self.assertEqual(user.role, "SU")

    def test_unknown_email_returns_none(self):
        self.assertIsNone(auth.authenticate_password(self.store, "nobody@example.com", PASSWORD))

    def test_register_creates_rc_account(self):
        self.assertEqual(self.store.get_user("sam@example.com")["role"], "RC")


class LoginPageSuspendedTests(unittest.TestCase):
    def test_suspended_message_shown_for_correct_password(self):
        from PySide6.QtWidgets import QApplication
        from gui.pages.login import LoginPage

        app = QApplication.instance() or QApplication([])  # noqa: F841
        with tempfile.TemporaryDirectory() as tmp:
            store = Store(Path(tmp) / "store.json")
            auth.register(store, "Sam Student", "sam@example.com", PASSWORD)
            store.update_user("sam@example.com", lambda r: r.__setitem__("suspended", True))
            page = LoginPage(store)
            page.email.setText("sam@example.com")
            page.password.setText(PASSWORD)
            page._submit_password()
            self.assertIn("suspended", page.pw_error.text().lower())
            self.assertFalse(page.pw_error.isHidden())


if __name__ == "__main__":
    unittest.main()


class AuthAccountChangeTests(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.addCleanup(self.folder.cleanup)
        self.store = Store(Path(self.folder.name) / "store.json")
        auth.register(self.store, "Sam Student", "sam@example.com", PASSWORD)

    def test_change_password_success(self):
        old_salt = self.store.get_user("sam@example.com")["salt"]
        auth.change_password(self.store, "sam@example.com", PASSWORD, "brand-new-pass")
        self.assertIsNone(auth.authenticate_password(self.store, "sam@example.com", PASSWORD))
        self.assertIsNotNone(auth.authenticate_password(self.store, "sam@example.com", "brand-new-pass"))
        self.assertNotEqual(old_salt, self.store.get_user("sam@example.com")["salt"])

    def test_change_password_wrong_current(self):
        with self.assertRaises(auth.AuthError):
            auth.change_password(self.store, "sam@example.com", "nope-nope", "brand-new-pass")
        self.assertIsNotNone(auth.authenticate_password(self.store, "sam@example.com", PASSWORD))

    def test_change_password_too_short(self):
        with self.assertRaises(auth.AuthError):
            auth.change_password(self.store, "sam@example.com", PASSWORD, "short")

    def test_change_email_success_moves_orders(self):
        self.store.add_order("sam@example.com", [1])
        user = auth.change_email(self.store, "sam@example.com", PASSWORD, "  New@Example.com ")
        self.assertEqual(user.email, "new@example.com")
        self.assertEqual(user.name, "Sam Student")
        self.assertIsNone(self.store.get_user("sam@example.com"))
        self.assertEqual(len(self.store.orders_for("new@example.com")), 1)
        self.assertEqual(self.store.orders_for("sam@example.com"), [])
        self.assertIsNotNone(auth.authenticate_password(self.store, "new@example.com", PASSWORD))

    def test_change_email_wrong_password(self):
        with self.assertRaises(auth.AuthError):
            auth.change_email(self.store, "sam@example.com", "wrong-wrong", "new@example.com")

    def test_change_email_invalid_and_taken(self):
        auth.register(self.store, "Other", "other@example.com", PASSWORD)
        with self.assertRaises(auth.AuthError):
            auth.change_email(self.store, "sam@example.com", PASSWORD, "not-an-email")
        with self.assertRaises(auth.AuthError) as ctx:
            auth.change_email(self.store, "sam@example.com", PASSWORD, "Other@example.com")
        self.assertIn("already", str(ctx.exception))
