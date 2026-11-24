"""Headless tests for the Account page and its AI preferences sub-page."""
import os
import tempfile
import unittest
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("ANJS_CATALOG", "sample")

from PySide6.QtWidgets import QApplication

from gui import auth, llm
from gui.data import User
from gui.pages.account import AccountPage
from gui.session import Session
from gui.store import Store

app = QApplication.instance() or QApplication([])
PASSWORD = "correct-horse"
CARD = "4242424242424242"


class AccountPageTests(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.addCleanup(self.folder.cleanup)
        self.path = Path(self.folder.name) / "store.json"
        self.store = Store(self.path)
        auth.register(self.store, "Sam Student", "sam@example.com", PASSWORD)
        auth.register(self.store, "Ann Other", "ann@example.com", PASSWORD)
        self.session = Session(self.store)
        self.page = AccountPage(self.session)
        self.session.sign_in(User(name="Sam Student", email="sam@example.com"))

    def _fill_address(self, form, **over):
        values = {"name": "Sam Student", "line1": "160 Convent Ave", "line2": "", "city": "New York", "state": "ny", "zip": "10031"}
        values.update(over)
        for key, value in values.items():
            form.fields[key].setText(value)

    def test_save_shipping_and_prefill(self):
        self._fill_address(self.page.shipping)
        self.page.shipping.save_btn.click()
        saved = self.store.get_profile("sam@example.com")["shipping_address"]
        self.assertEqual(saved["state"], "NY")
        self.page.refresh()
        self.assertEqual(self.page.shipping.fields["city"].text(), "New York")

    def test_bad_zip_shows_inline_error(self):
        self._fill_address(self.page.shipping, zip="abc")
        self.page.shipping.save_btn.click()
        self.assertFalse(self.page.shipping.status.isHidden())
        self.assertIsNone(self.store.get_profile("sam@example.com")["shipping_address"])

    def test_billing_same_as_shipping(self):
        self._fill_address(self.page.shipping)
        self.page.shipping.save_btn.click()
        self.page.same_as_shipping.setChecked(True)
        self.page.billing.save_btn.click()
        profile = self.store.get_profile("sam@example.com")
        self.assertEqual(profile["billing_address"], profile["shipping_address"])

    def test_card_stores_only_summary(self):
        p = self.page
        p.card_name.setText("Sam Student")
        p.card_number.setText(CARD)
        p.card_month.setText("12")
        p.card_year.setText("2099")
        p.card_cvv.setText("123")
        p.card_save_btn.click()
        card = self.store.get_profile("sam@example.com")["payment_card"]
        self.assertEqual(card["last4"], "4242")
        text = self.path.read_text()
        self.assertNotIn(CARD, text)
        self.assertNotIn('"123"', text)
        self.assertEqual(p.card_number.text(), "")
        self.assertEqual(p.card_cvv.text(), "")
        self.assertIn("4242", p.card_label.text())
        self.assertEqual(p.card_cvv.echoMode(), p.card_cvv.EchoMode.Password)
        p.remove_btn.click()
        self.assertIsNone(self.store.get_profile("sam@example.com")["payment_card"])

    def test_bad_card_rejected(self):
        p = self.page
        p.card_name.setText("Sam")
        p.card_number.setText("1234567812345678")
        p.card_month.setText("12")
        p.card_year.setText("2099")
        p.card_cvv.setText("123")
        p.card_save_btn.click()
        self.assertFalse(p.card_section.status.isHidden())
        self.assertIsNone(self.store.get_profile("sam@example.com")["payment_card"])

    def test_change_email_updates_session(self):
        self.store.add_order("sam@example.com", [1])
        self.page.new_email.setText("sam2@example.com")
        self.page.email_password.setText(PASSWORD)
        self.page.email_btn.click()
        self.assertEqual(self.session.user.email, "sam2@example.com")
        self.assertEqual(len(self.session.orders), 1)
        self.assertEqual(self.page.email.text(), "sam2@example.com")

    def test_change_email_wrong_password_inline_error(self):
        self.page.new_email.setText("sam2@example.com")
        self.page.email_password.setText("wrong-wrong")
        self.page.email_btn.click()
        self.assertEqual(self.session.user.email, "sam@example.com")
        self.assertFalse(self.page.email_section.status.isHidden())

    def test_change_password_clears_fields(self):
        p = self.page
        p.current_pw.setText(PASSWORD)
        p.new_pw.setText("another-pass1")
        p.confirm_pw.setText("another-pass1")
        p.password_btn.click()
        self.assertEqual(p.new_pw.text(), "")
        self.assertIsNotNone(auth.authenticate_password(self.store, "sam@example.com", "another-pass1"))
        p.current_pw.setText("another-pass1")
        p.new_pw.setText("something-else")
        p.confirm_pw.setText("mismatch-here")
        p.password_btn.click()
        self.assertFalse(p.password_section.status.isHidden())

    def test_preferences_round_trip(self):
        self.page.open_preferences()
        self.assertEqual(self.page.stack.currentIndex(), 1)
        panel = self.page.prefs_panel
        panel.tone.set_current("concise")
        panel.suggestions.set_current("5")
        panel.use_history.setChecked(False)
        panel.notes.setText("no horror")
        panel.save_btn.click()
        stored = self.store.get_profile("sam@example.com")["llm_prefs"]
        self.assertEqual((stored["tone"], stored["suggestions"], stored["use_history"], stored["notes"]),
                         ("concise", 5, False, "no horror"))
        panel.tone.set_current("friendly")
        panel.load()
        self.assertEqual(panel.tone.current, "concise")
        panel.reset_btn.click()
        self.assertEqual(self.store.get_profile("sam@example.com")["llm_prefs"], llm.DEFAULT_PREFS)
        panel.back.click()
        self.assertEqual(self.page.stack.currentIndex(), 0)

    def test_page_clears_for_next_user(self):
        self._fill_address(self.page.shipping)
        self.page.shipping.save_btn.click()
        self.page.new_pw.setText("leftover")
        self.session.sign_in(User(name="Ann Other", email="ann@example.com"))
        self.assertEqual(self.page.shipping.fields["city"].text(), "")
        self.assertEqual(self.page.new_pw.text(), "")
        self.assertEqual(self.page.name.text(), "Ann Other")
        self.session.sign_out()
        self.assertEqual(self.page.email.text(), "")
        self.assertTrue(self.page.shipping.isHidden())


if __name__ == "__main__":
    unittest.main()
