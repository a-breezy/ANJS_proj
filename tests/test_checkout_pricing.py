"""Quote maths and what the store saves for a checkout."""
from __future__ import annotations

import json
import os
import sys
import tempfile
import unittest
from decimal import Decimal
from pathlib import Path

os.environ.setdefault("ANJS_CATALOG", "sample")
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from gui import auth, billing  # noqa: E402
from gui.checkout import quote  # noqa: E402
from gui.data import SAMPLE_BOOKS, Book  # noqa: E402
from gui.session import Session  # noqa: E402
from gui.store import Store  # noqa: E402

NYC = {"name": "Jane", "line1": "1 Main St", "city": "New York", "state": "NY", "zip": "10031"}
OREGON = {"name": "Jane", "line1": "2 Pine St", "city": "Portland", "state": "OR", "zip": "97201"}
CARD_NUMBER = "4242424242424242"


def _card():
    return billing.clean_card("Jane Doe", CARD_NUMBER, 12, 2099, "123")


class QuoteTests(unittest.TestCase):
    def test_tax_rounds_half_up(self):
        book = Book(99, "T", "A", 14.99, "Fiction", 0)
        q = quote([book], "RC", "10031")
        self.assertEqual(q.subtotal, Decimal("14.99"))
        self.assertEqual(q.tax_amount, Decimal("1.33"))  # 14.99 * 0.08875 = 1.3303...
        self.assertEqual(q.grand_total, Decimal("16.32"))
        half = Book(98, "T", "A", 0.40, "Fiction", 0)  # 0.40 * 0.08875 = 0.0355 -> 0.04
        self.assertEqual(quote([half], "RC", "10031").tax_amount, Decimal("0.04"))

    def test_vip_discount_comes_before_tax(self):
        books = [SAMPLE_BOOKS[2]]  # $64.00
        q = quote(books, "VC", "10031")
        self.assertEqual(q.discount, Decimal("6.40"))
        self.assertEqual(q.taxable, Decimal("57.60"))
        self.assertEqual(q.tax_amount, Decimal("5.11"))  # 57.60 * 0.08875 = 5.112
        self.assertEqual(q.grand_total, Decimal("62.71"))

    def test_zero_tax_case(self):
        q = quote([SAMPLE_BOOKS[0], SAMPLE_BOOKS[1]], "RC", "97201")
        self.assertIsNone(q.tax_rate)
        self.assertEqual(q.tax_amount, Decimal("0.00"))
        self.assertEqual(q.grand_total, q.subtotal)
        self.assertEqual(q.grand_total, Decimal("32.99"))
        self.assertIn("ZIP 97201 is not taxable", q.tax_note)

    def test_empty_cart(self):
        q = quote([], "RC", "10031")
        self.assertEqual((q.subtotal, q.grand_total, q.lines), (Decimal("0.00"), Decimal("0.00"), ()))


class StoreCheckoutTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.path = Path(self._tmp.name) / "store.json"
        self.store = Store(self.path)
        auth.register(self.store, "Jane Doe", "jane@example.com", "correct horse")

    def checkout_info(self, address=NYC):
        return {"shipping_address": address, "billing_address": address, "payment_card": _card()}

    def test_saves_tax_totals_addresses_and_card_summary(self):
        order = self.store.add_order("jane@example.com", [1, 3], self.checkout_info())
        self.assertEqual(order["subtotal"], 78.99)
        self.assertEqual(order["total"], 78.99)
        self.assertEqual(order["tax_rate"], 0.08875)
        self.assertEqual(order["tax_amount"], 7.01)
        self.assertEqual(order["grand_total"], 86.0)
        self.assertEqual(order["billing_address"], NYC)
        self.assertEqual(order["shipping_address"], NYC)
        self.assertEqual(order["payment_card"]["last4"], "4242")
        saved = self.store.orders_for("jane@example.com")[0]
        self.assertEqual(saved, order)
        summary = self.store.financial_summary()
        self.assertEqual(summary["total_tax"], 7.01)
        self.assertEqual(summary["total_sales"], 78.99)
        self.assertEqual(summary["total_orders"], 1)

    def test_store_file_never_has_card_number_or_cvv(self):
        self.store.add_order("jane@example.com", [1], self.checkout_info())
        text = self.path.read_text(encoding="utf-8")
        self.assertNotIn(CARD_NUMBER, text)
        self.assertNotIn('"cvv"', text)
        self.assertIn("4242", text)  # only the last 4

    def test_full_card_number_is_refused(self):
        info = self.checkout_info()
        info["payment_card"] = {**_card(), "number": CARD_NUMBER}
        with self.assertRaises(ValueError):
            self.store.add_order("jane@example.com", [1], info)
        self.assertEqual(self.store.orders_for("jane@example.com"), [])

    def test_order_without_checkout_info_is_unchanged(self):
        order = self.store.add_order("jane@example.com", [1])
        self.assertEqual(order["total"], 14.99)
        self.assertNotIn("grand_total", order)
        self.assertNotIn("tax_amount", order)
        self.assertEqual(self.store.financial_summary()["total_tax"], 0.0)

    def test_untaxable_zip_saves_note(self):
        order = self.store.add_order("jane@example.com", [1], self.checkout_info(OREGON))
        self.assertIsNone(order["tax_rate"])
        self.assertEqual(order["tax_amount"], 0.0)
        self.assertEqual(order["grand_total"], 14.99)
        self.assertIn("ZIP 97201 is not taxable", order["tax_note"])

    def test_screen_quote_equals_saved_order(self):
        self.store.set_role("jane@example.com", "VC")
        books = [SAMPLE_BOOKS[0], SAMPLE_BOOKS[2], SAMPLE_BOOKS[7]]
        shown = quote(books, "VC", billing.zip5(NYC))
        order = self.store.add_order("jane@example.com", [b.id for b in books], self.checkout_info())
        self.assertEqual(order["subtotal"], float(shown.subtotal))
        self.assertEqual(order["discount_amount"], float(shown.discount))
        self.assertEqual(order["total"], float(shown.taxable))
        self.assertEqual(order["tax_amount"], float(shown.tax_amount))
        self.assertEqual(order["grand_total"], float(shown.grand_total))

    def test_vip_promotion_uses_pre_tax_total(self):
        # Spending counts the pre-tax total only (tax would push Sam past $200).
        info = self.checkout_info()
        self.store.add_order("jane@example.com", [3, 8, 2], info)  # 140.75
        record = self.store.get_user("jane@example.com")
        self.assertEqual(record["total_spent"], 140.75)
        self.assertEqual(record["role"], "RC")
        self.store.add_order("jane@example.com", [3], info)  # 64 -> 204.75 > 200
        self.assertEqual(self.store.get_user("jane@example.com")["role"], "VC")

        other = Store(Path(self._tmp.name) / "b.json")
        auth.register(other, "Sam", "sam@example.com", "correct horse")
        other.add_order("sam@example.com", [3, 8, 4, 4], self.checkout_info())  # 64+58.75+33 = 155.75
        other.add_order("sam@example.com", [2, 7], self.checkout_info())  # +35.5 = 191.25; taxed ~208
        self.assertEqual(other.get_user("sam@example.com")["total_spent"], 191.25)
        self.assertEqual(other.get_user("sam@example.com")["role"], "RC")

    def test_session_checkout_returns_order_with_details(self):
        session = Session(self.store)
        session.sign_in(auth.authenticate_password(self.store, "jane@example.com", "correct horse"))
        session.add_to_cart(SAMPLE_BOOKS[0])
        order = session.checkout(NYC, NYC, _card())
        self.assertEqual(order.grand_total, 16.32)
        self.assertEqual(order.tax_amount, 1.33)
        self.assertEqual(order.payment_card["last4"], "4242")
        self.assertEqual(session.cart, [])
        self.assertEqual(session.orders[0].grand_total, 16.32)
        self.assertIsNone(Session(self.store).checkout(NYC, NYC, _card()))  # nobody signed in

    def test_old_orders_still_load(self):
        data = json.loads(json.dumps({"number": 5, "placed": "2026-01-02", "status": "processing",
                                      "progress": 0.1, "book_ids": [1], "total": 14.99}))
        from gui.checkout import ReceiptOrder
        order = ReceiptOrder.from_record(data)
        self.assertIsNone(order.grand_total)
        self.assertEqual(order.total_text, "$14.99")


if __name__ == "__main__":
    unittest.main()
