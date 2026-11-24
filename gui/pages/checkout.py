"""Checkout screens used inside the Cart tab: details, then confirmation.

Neither screen keeps a full card number or CVV once you leave the details
screen: only the safe summary from billing.clean_card is passed on.
"""
from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QButtonGroup, QCheckBox, QFrame, QHBoxLayout, QLineEdit, QRadioButton, QVBoxLayout, QWidget,
)

from .. import billing
from ..checkout import Quote, quote
from ..session import Session
from ..widgets import make_button, make_label, scroll_column


def _clear(layout) -> None:
    while layout.count():
        item = layout.takeAt(0)
        widget = item.widget()
        if widget is not None:
            widget.setParent(None)
            widget.deleteLater()
        elif item.layout() is not None:
            _clear(item.layout())


def _field(placeholder: str, width: int | None = None) -> QLineEdit:
    edit = QLineEdit()
    edit.setPlaceholderText(placeholder)
    edit.setMinimumHeight(44)
    if width:
        edit.setMaximumWidth(width)
    return edit


def _error_label() -> QWidget:
    label = make_label("", "caption", wrap=True)
    label.setStyleSheet("color: #d64545;")
    label.hide()
    return label


def _set_error(label, text: str) -> None:
    label.setText(text)
    label.setVisible(bool(text))


class AddressForm(QWidget):
    """The six address fields."""

    def __init__(self) -> None:
        super().__init__()
        col = QVBoxLayout(self)
        col.setContentsMargins(0, 0, 0, 0)
        col.setSpacing(8)
        self.name = _field("Full name")
        self.line1 = _field("Street address")
        self.line2 = _field("Apartment, suite (optional)")
        self.city = _field("City")
        self.state = _field("State (e.g. NY)", 120)
        self.state.setMaxLength(2)
        self.zip = _field("ZIP code", 160)
        for edit in (self.name, self.line1, self.line2, self.city):
            col.addWidget(edit)
        row = QHBoxLayout()
        row.addWidget(self.state)
        row.addWidget(self.zip)
        row.addStretch()
        col.addLayout(row)

    def set_address(self, address: dict | None) -> None:
        address = address or {}
        for key in billing.ADDRESS_FIELDS:
            getattr(self, key).setText(str(address.get(key) or ""))

    def raw(self) -> dict:
        return {key: getattr(self, key).text() for key in billing.ADDRESS_FIELDS}


class CheckoutDetailsPage(QWidget):
    """Step 2: shipping, billing and payment."""

    back_requested = Signal()
    continued = Signal(dict)  # details, see collect()

    def __init__(self, session: Session) -> None:
        super().__init__()
        self.session = session
        self._entered_card: dict | None = None  # safe summary of a card typed earlier
        self._save_entered = False
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        scroll, col = scroll_column(max_width=900)
        outer.addWidget(scroll)

        col.addWidget(make_label("Checkout", "h2"))
        col.addWidget(make_label("Shipping address", "h3"))
        self.shipping = AddressForm()
        col.addWidget(self.shipping)
        self.shipping_error = _error_label()
        col.addWidget(self.shipping_error)

        col.addWidget(make_label("Billing address", "h3"))
        self.same_as_shipping = QCheckBox("Same as shipping")
        self.same_as_shipping.setChecked(True)
        self.same_as_shipping.toggled.connect(lambda on: self.billing.setVisible(not on))
        col.addWidget(self.same_as_shipping)
        self.billing = AddressForm()
        self.billing.hide()
        col.addWidget(self.billing)
        self.billing_error = _error_label()
        col.addWidget(self.billing_error)

        col.addWidget(make_label("Payment", "h3"))
        self.use_saved = QRadioButton()
        self.use_entered = QRadioButton()
        self.use_new = QRadioButton("Use a new card")
        self.card_choice = QButtonGroup(self)
        for button in (self.use_saved, self.use_entered, self.use_new):
            self.card_choice.addButton(button)
            col.addWidget(button)
            button.toggled.connect(self._sync_card_form)
        self.card_form = QWidget()
        form = QVBoxLayout(self.card_form)
        form.setContentsMargins(0, 0, 0, 0)
        form.setSpacing(8)
        self.card_name = _field("Name on card")
        self.card_number = _field("Card number")
        self.card_number.setMaxLength(23)
        self.exp_month = _field("MM", 90)
        self.exp_month.setMaxLength(2)
        self.exp_year = _field("YYYY", 110)
        self.exp_year.setMaxLength(4)
        self.cvv = _field("CVV", 100)
        self.cvv.setMaxLength(4)
        self.cvv.setEchoMode(QLineEdit.EchoMode.Password)
        form.addWidget(self.card_name)
        form.addWidget(self.card_number)
        row = QHBoxLayout()
        for edit in (self.exp_month, self.exp_year, self.cvv):
            row.addWidget(edit)
        row.addStretch()
        form.addLayout(row)
        col.addWidget(self.card_form)
        self.card_error = _error_label()
        col.addWidget(self.card_error)

        self.save_addresses = QCheckBox("Save these addresses to my account")
        self.save_card = QCheckBox("Save this card for future purchases")
        col.addWidget(self.save_addresses)
        col.addWidget(self.save_card)

        buttons = QHBoxLayout()
        self.back_btn = make_button("Back to cart", "secondary", height=50)
        self.back_btn.clicked.connect(self._back)
        self.continue_btn = make_button("Continue", "primary", height=50)
        self.continue_btn.clicked.connect(self._continue)
        buttons.addWidget(self.back_btn)
        buttons.addWidget(self.continue_btn, 1)
        col.addLayout(buttons)
        col.addStretch()
        self.reset()

    # --- state ---------------------------------------------------------------
    def reset(self) -> None:
        """Start clean and prefill from the signed-in user's saved profile."""
        self._entered_card = None
        self._save_entered = False
        for edit in self.findChildren(QLineEdit):
            edit.clear()
        for box in (self.save_addresses, self.save_card):
            box.setChecked(False)
        for label in (self.shipping_error, self.billing_error, self.card_error):
            _set_error(label, "")
        profile = self._profile()
        shipping, billing_address = profile["shipping_address"], profile["billing_address"]
        self.shipping.set_address(shipping)
        self.billing.set_address(billing_address)
        self.same_as_shipping.setChecked(not billing_address or billing_address == shipping)
        self.billing.setVisible(not self.same_as_shipping.isChecked())
        self._refresh_card_options(profile["payment_card"])

    def _profile(self) -> dict:
        empty = {"shipping_address": None, "billing_address": None, "payment_card": None}
        user = self.session.user
        if user is None or user.is_visitor:
            return empty
        try:
            return self.store_profile(user.email)
        except ValueError:
            return empty

    def store_profile(self, email: str) -> dict:
        return self.session.store.get_profile(email)

    def _refresh_card_options(self, saved: dict | None) -> None:
        self._saved_card = saved
        self.use_saved.setText(f"Use saved card ({billing.card_label(saved)})" if saved else "")
        self.use_saved.setVisible(bool(saved))
        entered = self._entered_card
        self.use_entered.setText(f"Use the card you entered ({billing.card_label(entered)})" if entered else "")
        self.use_entered.setVisible(bool(entered))
        self.use_new.setText("Use a new card" if (saved or entered) else "Pay with a card")
        first = self.use_entered if entered else self.use_saved if saved else self.use_new
        first.setChecked(True)
        self._sync_card_form()

    def _sync_card_form(self, *_args) -> None:
        new = self.use_new.isChecked()
        self.card_form.setVisible(new)
        self.save_card.setVisible(new)
        if not new:
            self.save_card.setChecked(False)

    def clear_card_inputs(self) -> None:
        for edit in (self.card_name, self.card_number, self.exp_month, self.exp_year, self.cvv):
            edit.clear()

    def hideEvent(self, event) -> None:
        self.clear_card_inputs()  # never leave a card number sitting in a hidden form
        super().hideEvent(event)

    def _back(self) -> None:
        self.clear_card_inputs()
        self.back_requested.emit()

    # --- validate and continue -------------------------------------------------
    def collect(self) -> dict | None:
        """Validate every section and show inline errors.

        Returns {"shipping_address", "billing_address", "payment_card" (safe
        summary), "save_addresses", "save_card"} or None if something is invalid."""
        ok = True
        shipping = billing_address = card = None
        try:
            shipping = billing.clean_address(self.shipping.raw())
            _set_error(self.shipping_error, "")
        except billing.BillingError as exc:
            _set_error(self.shipping_error, f"Shipping address: {exc}")
            ok = False
        if self.same_as_shipping.isChecked():
            billing_address = shipping
            _set_error(self.billing_error, "")
        else:
            try:
                billing_address = billing.clean_address(self.billing.raw())
                _set_error(self.billing_error, "")
            except billing.BillingError as exc:
                _set_error(self.billing_error, f"Billing address: {exc}")
                ok = False
        new_card = self.use_new.isChecked()
        try:
            if self.use_saved.isChecked() and self._saved_card:
                card = dict(self._saved_card)
            elif self.use_entered.isChecked() and self._entered_card:
                card = dict(self._entered_card)
            else:
                card = billing.clean_card(
                    self.card_name.text(), self.card_number.text(),
                    self.exp_month.text(), self.exp_year.text(), self.cvv.text(),
                )
            _set_error(self.card_error, "")
        except billing.BillingError as exc:
            _set_error(self.card_error, f"Payment: {exc}")
            ok = False
        if not ok:
            return None
        details = {
            "shipping_address": shipping,
            "billing_address": billing_address,
            "payment_card": card,
            "save_addresses": self.save_addresses.isChecked(),
            "save_card": (new_card and self.save_card.isChecked())
            or (self.use_entered.isChecked() and self._save_entered),
        }
        if new_card:
            self._save_entered = details["save_card"]
            self._entered_card = dict(card)
            self.clear_card_inputs()
            self._refresh_card_options(self._saved_card)
            self.use_entered.setChecked(True)
        return details

    def _continue(self) -> None:
        details = self.collect()
        if details is not None:
            self.continued.emit(details)


class CheckoutConfirmPage(QWidget):
    """Step 3: itemised receipt, then Place order."""

    back_requested = Signal()
    order_placed = Signal(object)  # data.Order
    orders_requested = Signal()

    def __init__(self, session: Session) -> None:
        super().__init__()
        self.session = session
        self._details: dict | None = None
        self._quote: Quote | None = None
        self.order = None
        self.placing = False  # True while the order is being saved (the cart empties meanwhile)
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        scroll, col = scroll_column(max_width=900)
        outer.addWidget(scroll)
        self.title = make_label("Review your order", "h2")
        col.addWidget(self.title)
        self.receipt = QVBoxLayout()
        self.receipt.setSpacing(8)
        col.addLayout(self.receipt)
        self.error = _error_label()
        col.addWidget(self.error)
        buttons = QHBoxLayout()
        self.back_btn = make_button("Back", "secondary", height=50)
        self.back_btn.clicked.connect(self.back_requested)
        self.place_btn = make_button("Place order", "primary", height=50)
        self.place_btn.clicked.connect(self._place)
        self.orders_btn = make_button("View my orders", "primary", height=50)
        self.orders_btn.clicked.connect(self.orders_requested)
        buttons.addWidget(self.back_btn)
        buttons.addWidget(self.place_btn, 1)
        buttons.addWidget(self.orders_btn, 1)
        col.addLayout(buttons)
        col.addStretch()
        self.reset()

    @property
    def placed(self) -> bool:
        return self.order is not None

    def reset(self) -> None:
        self._details = None
        self._quote = None
        self.order = None
        self.title.setText("Review your order")
        _clear(self.receipt)
        _set_error(self.error, "")
        self._sync_buttons()

    def _sync_buttons(self) -> None:
        self.back_btn.setVisible(not self.placed)
        self.place_btn.setVisible(not self.placed)
        self.orders_btn.setVisible(self.placed)

    def show_details(self, details: dict) -> None:
        """Price the current cart with the billing ZIP and show the receipt."""
        self._details = details
        self.refresh()

    def refresh(self) -> None:
        if self._details is None or self.placed:
            return
        role = self.session.user.role if self.session.user else "RC"
        zip_code = billing.zip5(self._details["billing_address"])
        self._quote = quote(list(self.session.cart), role, zip_code)
        self._render()

    def _row(self, left: str, right: str, role: str | None = None) -> None:
        row = QHBoxLayout()
        row.addWidget(make_label(left, role, wrap=True), 1)
        row.addWidget(make_label(right, role))
        self.receipt.addLayout(row)

    def _render(self) -> None:
        q, details = self._quote, self._details
        _clear(self.receipt)
        for line in q.lines:
            card = QFrame()
            card.setProperty("card", True)
            row = QHBoxLayout(card)
            row.setContentsMargins(14, 10, 14, 10)
            text = QVBoxLayout()
            text.setSpacing(0)
            text.addWidget(make_label(line.title, "book", wrap=True))
            text.addWidget(make_label(line.author, "author"))
            row.addLayout(text, 1)
            row.addWidget(make_label(f"${line.price:.2f}", "price"))
            self.receipt.addWidget(card)
        self._row("Subtotal", f"${q.subtotal:.2f}")
        if q.discount:
            self._row("VIP discount (10%)", f"-${q.discount:.2f}")
        if q.tax_rate is not None:
            percent = f"{q.tax_rate * 100:.3f}".rstrip("0").rstrip(".")
            self._row(f"Sales tax ({percent}%)", f"${q.tax_amount:.2f}")
        else:
            self._row("Sales tax", f"${q.tax_amount:.2f}")
            self.receipt.addWidget(make_label(q.tax_note, "caption", wrap=True))
        self._row("Total", f"${q.grand_total:.2f}", "h3")
        self.receipt.addWidget(make_label("Ship to", "h3"))
        self.receipt.addWidget(make_label(billing.format_address(details["shipping_address"]), "muted", wrap=True))
        self.receipt.addWidget(make_label("Bill to", "h3"))
        self.receipt.addWidget(make_label(billing.format_address(details["billing_address"]), "muted", wrap=True))
        self.receipt.addWidget(make_label("Payment", "h3"))
        self.receipt.addWidget(make_label(billing.card_label(details["payment_card"]), "muted"))

    def _place(self) -> None:
        if self._details is None or self._quote is None or self.placed:
            return
        self.refresh()  # the cart may have changed since this screen opened
        details = self._details
        self.placing = True
        try:
            order = self.session.checkout(
                details["shipping_address"], details["billing_address"], details["payment_card"]
            )
        finally:
            self.placing = False
        if order is None:
            _set_error(self.error, "Your cart is empty or your account can't place orders.")
            return
        self._save_to_profile(details)
        self.order = order
        self.title.setText(f"Order #{order.number} placed")
        self._sync_buttons()
        self.order_placed.emit(order)

    def _save_to_profile(self, details: dict) -> None:
        fields = {}
        if details.get("save_addresses"):
            fields["shipping_address"] = details["shipping_address"]
            fields["billing_address"] = details["billing_address"]
        if details.get("save_card"):
            fields["payment_card"] = details["payment_card"]
        if fields and self.session.user is not None:
            try:
                self.session.store.update_profile(self.session.user.email, **fields)
            except (ValueError, KeyError):
                pass  # the order is already placed; saving details is a convenience
