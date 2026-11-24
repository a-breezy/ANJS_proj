"""Shared address/card helpers and the Store profile API (no PySide needed)."""
import os
import sys
import tempfile
import unittest
from datetime import date
from pathlib import Path

os.environ.setdefault("ANJS_CATALOG", "sample")
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from gui import auth, billing  # noqa: E402
from gui.store import Store  # noqa: E402

ADDRESS = {"name": "Sam", "line1": "160 Convent Ave", "city": "New York", "state": "ny", "zip": "10031"}
TODAY = date(2026, 11, 24)


class BillingTests(unittest.TestCase):
    def test_clean_address(self):
        a = billing.clean_address(ADDRESS)
        self.assertEqual((a["state"], a["line2"], billing.zip5(a)), ("NY", "", "10031"))
        for bad in ({**ADDRESS, "zip": "1003"}, {**ADDRESS, "state": "New York"}, {**ADDRESS, "city": " "}):
            with self.assertRaises(billing.BillingError):
                billing.clean_address(bad)

    def test_card_summary_never_keeps_number_or_cvv(self):
        card = billing.clean_card("Sam", "4242 4242 4242 4242", "4", "28", "123", today=TODAY)
        self.assertEqual(card, {"cardholder": "Sam", "brand": "Visa", "last4": "4242", "exp_month": 4, "exp_year": 2028})
        self.assertEqual(billing.card_label(card), "Visa •••• 4242 (exp 04/2028)")

    def test_bad_cards(self):
        cases = [
            ("Sam", "4242424242424241", 4, 2028, "123"),  # fails Luhn
            ("Sam", "4242424242424242", 10, 2026, "123"),  # expired
            ("Sam", "4242424242424242", 13, 2028, "123"),  # bad month
            ("Sam", "4242424242424242", 4, 2028, "12"),  # bad CVV
            ("", "4242424242424242", 4, 2028, "123"),  # no name
            ("Sam", "378282246310005", 4, 2028, "123"),  # Amex needs 4-digit CVV
        ]
        for args in cases:
            with self.assertRaises(billing.BillingError, msg=args):
                billing.clean_card(*args, today=TODAY)


class ProfileTests(unittest.TestCase):
    def setUp(self):
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        self.path = Path(folder.name) / "store.json"
        self.store = Store(self.path)
        auth.register(self.store, "Sam", "sam@example.com", "password123")

    def test_profile_round_trip_and_clear(self):
        p = self.store.get_profile("sam@example.com")
        self.assertEqual(p, {"shipping_address": None, "billing_address": None, "payment_card": None, "llm_prefs": {}})
        card = billing.clean_card("Sam", "4242424242424242", 4, 2028, "123", today=TODAY)
        self.store.update_profile("sam@example.com", shipping_address=billing.clean_address(ADDRESS), payment_card=card)
        p = Store(self.path).get_profile("sam@example.com")
        self.assertEqual(p["payment_card"]["last4"], "4242")
        self.assertEqual(p["shipping_address"]["zip"], "10031")
        self.assertNotIn("4242424242424242", self.path.read_text())
        self.store.update_profile("sam@example.com", payment_card=None)
        self.assertIsNone(self.store.get_profile("sam@example.com")["payment_card"])

    def test_profile_rejects_unknown_fields_and_full_card(self):
        with self.assertRaises(KeyError):
            self.store.update_profile("sam@example.com", role="SU")
        with self.assertRaises(ValueError):
            self.store.update_profile("sam@example.com", payment_card={"number": "4242424242424242"})

    def test_change_email_moves_orders_and_reviews(self):
        self.store.add_order("sam@example.com", [1])
        self.store.add_review(1, {"author_email": "sam@example.com", "stars": 5})
        self.store.change_email("sam@example.com", "New@Example.com")
        self.assertIsNone(self.store.get_user("sam@example.com"))
        self.assertEqual(self.store.get_user("new@example.com")["email"], "new@example.com")
        self.assertEqual(len(self.store.orders_for("new@example.com")), 1)
        self.assertEqual(self.store.get_reviews(1)[0]["author_email"], "new@example.com")

    def test_change_email_refuses_taken_or_missing(self):
        auth.register(self.store, "Kim", "kim@example.com", "password123")
        with self.assertRaises(ValueError):
            self.store.change_email("sam@example.com", "kim@example.com")
        with self.assertRaises(ValueError):
            self.store.change_email("nobody@example.com", "x@example.com")


if __name__ == "__main__":
    unittest.main()
