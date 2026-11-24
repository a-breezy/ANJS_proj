"""Headless tests for the cart -> details -> confirmation -> place order flow."""
from __future__ import annotations

import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("ANJS_CATALOG", "sample")
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from PySide6.QtWidgets import QApplication, QLabel  # noqa: E402

from gui import auth, billing  # noqa: E402
from gui.app import MainWindow  # noqa: E402
from gui.data import SAMPLE_BOOKS  # noqa: E402
from gui.store import Store  # noqa: E402
from gui.theme import build_qss, theme  # noqa: E402

_app = QApplication.instance() or QApplication([])
_app.setStyleSheet(build_qss(theme.palette))

EMAIL = "jane@example.com"
NYC = {"name": "Jane Doe", "line1": "1 Main St", "line2": "", "city": "New York", "state": "NY", "zip": "10031"}
CARD_NUMBER = "4242 4242 4242 4242"


def texts(widget) -> list[str]:
    return [label.text() for label in widget.findChildren(QLabel)]


class CheckoutGuiTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.path = Path(self._tmp.name) / "store.json"
        self.store = Store(self.path)
        self.win = MainWindow(self.store)
        self.win.show()
        self.session = self.win.session
        self.session.sign_in(auth.register(self.store, "Jane Doe", EMAIL, "correct horse"))
        self.cart = self.win.shell.cart
        self.details = self.cart.details
        self.confirm = self.cart.confirm
        self.win.shell.show_tab("cart")

    def tearDown(self):
        self.win.close()
        self._tmp.cleanup()

    def fill_address(self, form, address=NYC):
        form.set_address(address)

    def fill_card(self):
        d = self.details
        d.card_name.setText("Jane Doe")
        d.card_number.setText(CARD_NUMBER)
        d.exp_month.setText("12")
        d.exp_year.setText("2099")
        d.cvv.setText("123")

    def start(self, books=(0, 2)):
        for i in books:
            self.session.add_to_cart(SAMPLE_BOOKS[i])
        self.cart.checkout.click()

    def to_confirmation(self, address=NYC, books=(0, 2)):
        self.start(books)
        self.fill_address(self.details.shipping, address)
        self.fill_card()
        self.details.continue_btn.click()
        self.assertEqual(self.cart.step, "confirm")

    def test_checkout_button_opens_details_without_ordering(self):
        self.start()
        self.assertEqual(self.cart.step, "details")
        self.assertEqual(self.store.orders_for(EMAIL), [])
        self.assertEqual(len(self.session.cart), 2)
        self.details.back_btn.click()
        self.assertEqual(self.cart.step, "cart")

    def test_validation_errors_are_inline(self):
        self.start()
        self.details.continue_btn.click()
        self.assertEqual(self.cart.step, "details")
        self.assertFalse(self.details.shipping_error.isHidden())
        self.assertFalse(self.details.card_error.isHidden())
        self.assertIn("full name", self.details.shipping_error.text())
        self.fill_address(self.details.shipping)
        self.details.same_as_shipping.setChecked(False)
        self.details.billing.set_address({**NYC, "zip": "abc"})
        self.fill_card()
        self.details.cvv.setText("1")
        self.details.continue_btn.click()
        self.assertEqual(self.cart.step, "details")
        self.assertTrue(self.details.shipping_error.isHidden())
        self.assertIn("ZIP", self.details.billing_error.text())
        self.assertIn("security code", self.details.card_error.text())

    def test_confirmation_shows_items_tax_and_total(self):
        self.to_confirmation()
        shown = texts(self.confirm)
        for book in (SAMPLE_BOOKS[0], SAMPLE_BOOKS[2]):
            self.assertIn(book.title, shown)
            self.assertIn(book.author, shown)
            self.assertIn(book.price_text, shown)
        self.assertIn("$78.99", shown)  # subtotal
        self.assertIn("Sales tax (8.875%)", shown)
        self.assertIn("$7.01", shown)
        self.assertIn("$86.00", shown)  # grand total
        self.assertTrue(any("Visa •••• 4242" in t for t in shown))
        self.assertTrue(any("1 Main St" in t for t in shown))
        self.assertFalse(any("not taxable" in t for t in shown))

    def test_vip_discount_line(self):
        self.store.set_role(EMAIL, "VC")
        self.session.sync_user_from_store()
        self.to_confirmation()
        shown = texts(self.confirm)
        self.assertIn("VIP discount (10%)", shown)
        self.assertIn("-$7.90", shown)

    def test_not_taxable_zip_note(self):
        self.to_confirmation({**NYC, "state": "OR", "zip": "97201"})
        shown = texts(self.confirm)
        self.assertIn("ZIP 97201 is not taxable, so no sales tax was charged.", shown)
        self.assertIn("$78.99", shown)

    def test_tax_uses_billing_zip_not_shipping(self):
        self.start()
        self.fill_address(self.details.shipping)  # NYC
        self.details.same_as_shipping.setChecked(False)
        self.details.billing.set_address({**NYC, "state": "OR", "zip": "97201"})
        self.fill_card()
        self.details.continue_btn.click()
        self.assertIn("ZIP 97201 is not taxable, so no sales tax was charged.", texts(self.confirm))

    def test_place_order_then_view_orders(self):
        self.to_confirmation()
        screen_total = self.confirm._quote.grand_total
        emitted = []
        self.cart.checked_out.connect(emitted.append)
        self.confirm.place_btn.click()

        self.assertEqual(self.session.cart, [])
        saved = self.store.orders_for(EMAIL)
        self.assertEqual(len(saved), 1)
        self.assertEqual(saved[0]["grand_total"], float(screen_total))
        self.assertEqual(saved[0]["billing_address"], NYC)
        self.assertEqual(self.cart.step, "confirm")  # receipt stays
        self.assertEqual(self.confirm.title.text(), "Order #1001 placed")
        self.assertIn("Total", texts(self.confirm))
        self.assertIn("The Quiet Orchard", texts(self.confirm))
        self.assertTrue(self.confirm.place_btn.isHidden())
        self.assertFalse(self.confirm.orders_btn.isHidden())
        self.assertEqual(emitted, [])

        self.confirm.orders_btn.click()
        self.assertEqual(len(emitted), 1)
        self.assertEqual(emitted[0].number, 1001)
        self.assertEqual(self.win.shell.current_tab(), "orders")
        self.assertEqual(self.cart.step, "cart")

    def test_orders_page_shows_grand_total_and_old_orders(self):
        self.store.add_order(EMAIL, [1])  # an old-style order, no tax fields
        self.to_confirmation()
        self.confirm.place_btn.click()
        self.session.orders_changed.emit()
        orders = self.win.shell.orders
        shown = texts(orders)
        self.assertTrue(any("Total $86.00 (incl. $7.01 tax)" in t for t in shown), shown)
        self.assertTrue(any("Total $14.99" in t for t in shown), shown)

    def test_new_checkout_starts_clean(self):
        self.to_confirmation()
        self.confirm.place_btn.click()
        self.confirm.orders_btn.click()
        self.start((1,))
        self.assertEqual(self.cart.step, "details")
        self.assertEqual(self.details.shipping.line1.text(), "")
        self.assertEqual(self.details.card_number.text(), "")
        self.assertFalse(self.confirm.placed)

    def test_sign_out_resets_flow_and_clears_card_inputs(self):
        self.start()
        self.fill_card()
        self.session.sign_out()
        self.assertEqual(self.cart.step, "cart")
        self.assertEqual(self.details.card_number.text(), "")
        self.assertEqual(self.details.cvv.text(), "")

    def test_card_number_and_cvv_not_kept_after_continue(self):
        self.to_confirmation()
        self.assertEqual(self.details.card_number.text(), "")
        self.assertEqual(self.details.cvv.text(), "")
        self.confirm.back_btn.click()
        self.assertEqual(self.cart.step, "details")
        self.assertTrue(self.details.use_entered.isChecked())
        self.details.continue_btn.click()  # re-use the entered card without retyping
        self.assertEqual(self.cart.step, "confirm")
        self.confirm.place_btn.click()
        text = self.path.read_text(encoding="utf-8")
        self.assertNotIn("4242424242424242", text)
        order = self.session.orders[0]
        self.assertNotIn("number", order.payment_card)
        self.assertEqual(order.payment_card["last4"], "4242")

    def test_saved_profile_prefills(self):
        card = billing.clean_card("Jane Doe", "4242424242424242", 12, 2099, "123")
        ship = billing.clean_address(NYC)
        bill = billing.clean_address({**NYC, "line1": "9 Billing Rd", "zip": "10001"})
        self.store.update_profile(EMAIL, shipping_address=ship, billing_address=bill, payment_card=card)
        self.start()
        self.assertEqual(self.details.shipping.line1.text(), "1 Main St")
        self.assertFalse(self.details.same_as_shipping.isChecked())
        self.assertEqual(self.details.billing.line1.text(), "9 Billing Rd")
        self.assertFalse(self.details.use_saved.isHidden())
        self.assertIn("Visa •••• 4242", self.details.use_saved.text())
        self.assertTrue(self.details.use_saved.isChecked())
        self.assertTrue(self.details.card_form.isHidden())
        self.details.continue_btn.click()  # saved card: nothing to re-enter
        self.assertEqual(self.cart.step, "confirm")
        self.assertTrue(any("9 Billing Rd" in t for t in texts(self.confirm)))

    def test_save_addresses_and_card_stores_only_summary(self):
        self.start()
        self.fill_address(self.details.shipping)
        self.fill_card()
        self.details.save_addresses.setChecked(True)
        self.details.save_card.setChecked(True)
        self.details.continue_btn.click()
        self.confirm.back_btn.click()
        self.details.continue_btn.click()
        self.confirm.place_btn.click()
        profile = self.store.get_profile(EMAIL)
        self.assertEqual(profile["shipping_address"], NYC)
        self.assertEqual(profile["billing_address"], NYC)
        self.assertEqual(
            profile["payment_card"],
            {"cardholder": "Jane Doe", "brand": "Visa", "last4": "4242", "exp_month": 12, "exp_year": 2099},
        )
        text = self.path.read_text(encoding="utf-8")
        self.assertNotIn("4242424242424242", text)
        self.assertNotIn('"cvv"', text)

    def test_unchecked_save_leaves_profile_empty(self):
        self.to_confirmation()
        self.confirm.place_btn.click()
        profile = self.store.get_profile(EMAIL)
        self.assertIsNone(profile["shipping_address"])
        self.assertIsNone(profile["payment_card"])

    def test_cart_change_during_confirmation_reprices(self):
        self.to_confirmation(books=(0,))
        self.session.add_to_cart(SAMPLE_BOOKS[1])
        self.assertEqual(self.cart.step, "confirm")
        self.assertIn(SAMPLE_BOOKS[1].title, texts(self.confirm))
        self.session.remove_from_cart(0)
        self.session.remove_from_cart(0)
        self.assertEqual(self.cart.step, "cart")


if __name__ == "__main__":
    unittest.main()
