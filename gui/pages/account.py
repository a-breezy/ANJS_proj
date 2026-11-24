"""Account tab: profile, email, password, addresses, saved card, AI preferences, sign out.

Card handling: the full number and CVV exist only in the input boxes and in
local variables inside ``_save_card``; only ``billing.clean_card``'s summary
is stored, and the boxes are cleared right after saving.
"""
from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QCheckBox, QHBoxLayout, QLineEdit, QStackedWidget, QVBoxLayout, QWidget

from .. import auth, billing
from ..data import User
from ..review_dialog import SuperUserModerationDialog
from ..session import Session
from ..widgets import Avatar, Page, ThemeSwitch, make_button, make_label, scroll_column
from .preferences import PreferencesPanel, set_status


def _line(placeholder: str = "", secret: bool = False, max_length: int | None = None) -> QLineEdit:
    field = QLineEdit()
    field.setPlaceholderText(placeholder)
    field.setFixedHeight(44)
    if secret:
        field.setEchoMode(QLineEdit.EchoMode.Password)
    if max_length:
        field.setMaxLength(max_length)
    return field


class _Section(QWidget):
    """A titled block with an inline status line (error or success)."""

    def __init__(self, title: str, hint: str = "") -> None:
        super().__init__()
        self.body = QVBoxLayout(self)
        self.body.setContentsMargins(0, 8, 0, 0)
        self.body.setSpacing(8)
        self.body.addWidget(make_label(title, "h3"))
        if hint:
            self.body.addWidget(make_label(hint, "muted", wrap=True))
        self.status = make_label("", "error", wrap=True)
        self.status.hide()

    def field(self, label: str, widget: QLineEdit) -> QLineEdit:
        self.body.addWidget(make_label(label, "field"))
        self.body.addWidget(widget)
        return widget

    def finish(self, *buttons) -> None:
        """Add the status line and the action buttons at the bottom."""
        self.body.addWidget(self.status)
        row = QHBoxLayout()
        for button in buttons:
            row.addWidget(button)
        row.addStretch()
        self.body.addLayout(row)

    def ok(self, message: str) -> None:
        set_status(self.status, message, ok=True)

    def fail(self, message: str) -> None:
        set_status(self.status, message)


class _AddressForm(_Section):
    def __init__(self, title: str, hint: str = "") -> None:
        super().__init__(title, hint)
        self.fields: dict[str, QLineEdit] = {}

    def build(self, *extra_widgets: QWidget) -> None:
        for widget in extra_widgets:
            self.body.addWidget(widget)
        self.fields["name"] = self.field("Full name", _line())
        self.fields["line1"] = self.field("Street address", _line())
        self.fields["line2"] = self.field("Apt / suite (optional)", _line())
        self.fields["city"] = self.field("City", _line())
        row = QHBoxLayout()
        self.fields["state"] = _line("NY", max_length=2)
        self.fields["zip"] = _line("10031", max_length=10)
        for label, key in (("State", "state"), ("ZIP code", "zip")):
            box = QVBoxLayout()
            box.addWidget(make_label(label, "field"))
            box.addWidget(self.fields[key])
            row.addLayout(box, 1)
        self.body.addLayout(row)
        self.save_btn = make_button("Save", "primary", height=44)
        self.finish(self.save_btn)

    def values(self) -> dict:
        return {key: field.text() for key, field in self.fields.items()}

    def show_address(self, address: dict | None) -> None:
        address = address or {}
        for key, field in self.fields.items():
            field.setText(str(address.get(key, "") or ""))

    def set_editable(self, editable: bool) -> None:
        for field in self.fields.values():
            field.setEnabled(editable)


class AccountPage(Page):
    sign_out_requested = Signal()

    def __init__(self, session: Session) -> None:
        super().__init__()
        self.session = session
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        self.stack = QStackedWidget()
        outer.addWidget(self.stack)

        scroll, col = scroll_column(max_width=560)
        self.stack.addWidget(scroll)
        self.prefs_panel = PreferencesPanel(session)
        self.prefs_panel.back_requested.connect(lambda: self.stack.setCurrentIndex(0))
        self.stack.addWidget(self.prefs_panel)

        col.addWidget(make_label("Account", "h2"))
        row = QHBoxLayout()
        self.avatar = Avatar("?", 56)
        row.addWidget(self.avatar)
        row.addSpacing(12)
        who = QVBoxLayout()
        who.setSpacing(0)
        self.name = make_label("", "h3")
        self.email = make_label("", "muted")
        who.addWidget(self.name)
        who.addWidget(self.email)
        row.addLayout(who)
        row.addStretch()
        col.addLayout(row)
        col.addSpacing(8)
        col.addWidget(make_label("Appearance", "field"))
        col.addWidget(ThemeSwitch())
        self.su_btn = make_button("SU: Order Lists & Taboo Words", "primary", height=46)
        self.su_btn.clicked.connect(lambda: SuperUserModerationDialog(self.session, self).exec())
        col.addWidget(self.su_btn)
        self.prefs_btn = make_button("AI preferences", "outline", height=46)
        self.prefs_btn.clicked.connect(self.open_preferences)
        col.addWidget(self.prefs_btn)

        # Email
        self.email_section = _Section("Email", "Changing it needs your current password.")
        self.new_email = self.email_section.field("New email", _line())
        self.email_password = self.email_section.field("Current password", _line(secret=True))
        self.email_btn = make_button("Change email", "primary", height=44)
        self.email_btn.clicked.connect(self._change_email)
        self.email_section.finish(self.email_btn)
        col.addWidget(self.email_section)

        # Password
        self.password_section = _Section("Password")
        self.current_pw = self.password_section.field("Current password", _line(secret=True))
        self.new_pw = self.password_section.field("New password", _line(f"At least {auth.MIN_PASSWORD} characters", secret=True))
        self.confirm_pw = self.password_section.field("Re-enter new password", _line(secret=True))
        self.password_btn = make_button("Change password", "primary", height=44)
        self.password_btn.clicked.connect(self._change_password)
        self.password_section.finish(self.password_btn)
        col.addWidget(self.password_section)

        # Addresses
        self.shipping = _AddressForm("Shipping address")
        self.shipping.build()
        self.shipping.save_btn.clicked.connect(self._save_shipping)
        col.addWidget(self.shipping)

        self.billing = _AddressForm("Billing address")
        self.same_as_shipping = QCheckBox("Same as shipping")
        self.same_as_shipping.toggled.connect(self._same_toggled)
        self.billing.build(self.same_as_shipping)
        self.billing.save_btn.clicked.connect(self._save_billing)
        col.addWidget(self.billing)

        # Saved card
        self.card_section = _Section("Saved card", "Only the last 4 digits and expiry are saved.")
        self.card_label = make_label("", "field")
        self.card_section.body.addWidget(self.card_label)
        self.replace_btn = make_button("Replace", "outline", height=40)
        self.remove_btn = make_button("Remove", "outline", height=40)
        self.replace_btn.clicked.connect(lambda: self._show_card_form(True))
        self.remove_btn.clicked.connect(self._remove_card)
        card_row = QHBoxLayout()
        card_row.addWidget(self.replace_btn)
        card_row.addWidget(self.remove_btn)
        card_row.addStretch()
        self.card_actions = QWidget()
        self.card_actions.setLayout(card_row)
        card_row.setContentsMargins(0, 0, 0, 0)
        self.card_section.body.addWidget(self.card_actions)
        self.card_form = QWidget()
        form = QVBoxLayout(self.card_form)
        form.setContentsMargins(0, 0, 0, 0)
        form.setSpacing(8)
        self.card_name = _line()
        self.card_number = _line("Card number", max_length=23)
        self.card_month = _line("MM", max_length=2)
        self.card_year = _line("YYYY", max_length=4)
        self.card_cvv = _line(secret=True, max_length=4)
        for label, widget in (("Name on card", self.card_name), ("Card number", self.card_number)):
            form.addWidget(make_label(label, "field"))
            form.addWidget(widget)
        exp = QHBoxLayout()
        for label, widget in (("Expiry month", self.card_month), ("Expiry year", self.card_year), ("CVV", self.card_cvv)):
            box = QVBoxLayout()
            box.addWidget(make_label(label, "field"))
            box.addWidget(widget)
            exp.addLayout(box, 1)
        form.addLayout(exp)
        self.card_save_btn = make_button("Save card", "primary", height=44)
        self.card_save_btn.clicked.connect(self._save_card)
        form.addWidget(self.card_save_btn)
        self.card_section.body.addWidget(self.card_form)
        self.card_section.finish()
        col.addWidget(self.card_section)

        col.addSpacing(8)
        sign_out = make_button("Sign out", "outline", height=50)
        sign_out.clicked.connect(self.sign_out_requested)
        col.addWidget(sign_out)
        col.addStretch()

        session.user_changed.connect(self.refresh)
        self.refresh()

    # --- helpers ----------------------------------------------------------
    @property
    def _member(self) -> User | None:
        user = self.session.user
        return user if user and not user.is_visitor else None

    def _profile(self) -> dict:
        user = self._member
        if user is None:
            return {"shipping_address": None, "billing_address": None, "payment_card": None, "llm_prefs": {}}
        try:
            return self.session.store.get_profile(user.email)
        except ValueError:
            return {"shipping_address": None, "billing_address": None, "payment_card": None, "llm_prefs": {}}

    def open_preferences(self) -> None:
        self.prefs_panel.load()
        self.stack.setCurrentIndex(1)

    # --- refresh (user switched, signed in or out) -------------------------
    def refresh(self) -> None:
        user = self.session.user
        self.stack.setCurrentIndex(0)
        self.avatar.set_initial(user.initial if user else "?")
        self.name.setText(user.name if user else "")
        self.email.setText(user.email if user else "")
        self.su_btn.setVisible(bool(user and user.is_admin))
        member = self._member is not None
        for widget in (self.prefs_btn, self.email_section, self.password_section, self.shipping, self.billing, self.card_section):
            widget.setVisible(member)
        for field in (self.new_email, self.email_password, self.current_pw, self.new_pw, self.confirm_pw,
                      self.card_name, self.card_number, self.card_month, self.card_year, self.card_cvv):
            field.clear()
        for section in (self.email_section, self.password_section, self.shipping, self.billing, self.card_section):
            section.status.hide()
        profile = self._profile()
        self.shipping.show_address(profile["shipping_address"])
        self.billing.show_address(profile["billing_address"])
        shipping, billing_addr = profile["shipping_address"], profile["billing_address"]
        self.same_as_shipping.blockSignals(True)
        self.same_as_shipping.setChecked(bool(shipping) and shipping == billing_addr)
        self.same_as_shipping.blockSignals(False)
        self._same_toggled(self.same_as_shipping.isChecked())
        self._show_card(profile["payment_card"])
        self.prefs_panel.load()

    # --- email / password -------------------------------------------------
    def _change_email(self) -> None:
        user = self._member
        if user is None:
            return
        try:
            updated = auth.change_email(self.session.store, user.email, self.email_password.text(), self.new_email.text())
        except auth.AuthError as exc:
            return self.email_section.fail(str(exc))
        self.session.sign_in(User(name=updated.name, email=updated.email, role=updated.role))
        self.email_section.ok("Email changed.")

    def _change_password(self) -> None:
        user = self._member
        if user is None:
            return
        if self.new_pw.text() != self.confirm_pw.text():
            return self.password_section.fail("The new passwords don't match.")
        try:
            auth.change_password(self.session.store, user.email, self.current_pw.text(), self.new_pw.text())
        except auth.AuthError as exc:
            return self.password_section.fail(str(exc))
        for field in (self.current_pw, self.new_pw, self.confirm_pw):
            field.clear()
        self.password_section.ok("Password changed.")

    # --- addresses --------------------------------------------------------
    def _save_address(self, form: _AddressForm, key: str, values: dict, message: str) -> dict | None:
        user = self._member
        if user is None:
            return None
        try:
            address = billing.clean_address(values)
            self.session.store.update_profile(user.email, **{key: address})
        except (billing.BillingError, ValueError) as exc:
            form.fail(str(exc))
            return None
        form.show_address(address)
        form.ok(message)
        return address

    def _save_shipping(self) -> None:
        address = self._save_address(self.shipping, "shipping_address", self.shipping.values(), "Shipping address saved.")
        if address and self.same_as_shipping.isChecked():
            self._save_billing()

    def _same_toggled(self, same: bool) -> None:
        self.billing.set_editable(not same)
        if same:
            self.billing.show_address(self.shipping.values())

    def _save_billing(self) -> None:
        same = self.same_as_shipping.isChecked()
        values = self.shipping.values() if same else self.billing.values()
        self._save_address(self.billing, "billing_address", values, "Billing address saved.")

    # --- saved card -------------------------------------------------------
    def _show_card(self, card: dict | None) -> None:
        self.card_label.setText(billing.card_label(card) if card else "")
        self.card_label.setVisible(bool(card))
        self.card_actions.setVisible(bool(card))
        self._show_card_form(not card)

    def _show_card_form(self, visible: bool) -> None:
        self.card_form.setVisible(visible)

    def _save_card(self) -> None:
        user = self._member
        if user is None:
            return
        try:
            summary = billing.clean_card(
                self.card_name.text(), self.card_number.text(),
                self.card_month.text(), self.card_year.text(), self.card_cvv.text(),
            )
            self.session.store.update_profile(user.email, payment_card=summary)
        except (billing.BillingError, ValueError) as exc:
            return self.card_section.fail(str(exc))
        for field in (self.card_name, self.card_number, self.card_cvv, self.card_month, self.card_year):
            field.clear()
        self._show_card(summary)
        self.card_section.ok("Card saved.")

    def _remove_card(self) -> None:
        user = self._member
        if user is None:
            return
        self.session.store.update_profile(user.email, payment_card=None)
        self._show_card(None)
        self.card_section.ok("Card removed.")
