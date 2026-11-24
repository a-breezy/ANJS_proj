"""Cart tab: books waiting to be bought, and checkout."""
from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QFrame, QHBoxLayout, QStackedWidget, QVBoxLayout

from ..session import Session
from ..widgets import Column, Page, make_button, make_label
from .checkout import CheckoutConfirmPage, CheckoutDetailsPage


class CartPage(Page):
    checked_out = Signal(object)  # data.Order

    def __init__(self, session: Session) -> None:
        super().__init__()
        self.session = session
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        # Steps: 0 cart, 1 checkout details, 2 confirmation / receipt.
        self.steps = QStackedWidget()
        outer.addWidget(self.steps)
        column = Column(max_width=900)
        self.steps.addWidget(column)
        col = column.col
        col.addWidget(make_label("Your cart", "h2"))
        self.items = QVBoxLayout()
        self.items.setSpacing(10)
        col.addLayout(self.items)
        self.empty = make_label("Your cart is empty. Add a book from Home.", "caption", wrap=True)
        col.addWidget(self.empty)
        col.addStretch()
        self.total = make_label("", "h3")
        col.addWidget(self.total)
        self.checkout = make_button("Checkout", "primary", height=54)
        self.checkout.clicked.connect(self._checkout)
        col.addWidget(self.checkout)

        self.details = CheckoutDetailsPage(session)
        self.confirm = CheckoutConfirmPage(session)
        self.steps.addWidget(self.details)
        self.steps.addWidget(self.confirm)
        self.details.back_requested.connect(self.show_cart)
        self.details.continued.connect(self._show_confirmation)
        self.confirm.back_requested.connect(self._edit_details)
        self.confirm.orders_requested.connect(self._view_orders)
        session.cart_changed.connect(self._cart_changed)
        session.user_changed.connect(self.show_cart)  # sign in/out starts clean
        self.refresh()

    # --- checkout flow -------------------------------------------------------
    @property
    def step(self) -> str:
        return ("cart", "details", "confirm")[self.steps.currentIndex()]

    def show_cart(self) -> None:
        """Back to the cart, with a clean checkout for next time."""
        self.details.reset()
        self.confirm.reset()
        self.steps.setCurrentIndex(0)

    def _checkout(self) -> None:
        if self.session.cart and self.session.user is not None and not self.session.user.is_visitor:
            self.details.reset()
            self.confirm.reset()
            self.steps.setCurrentIndex(1)

    def _show_confirmation(self, details: dict) -> None:
        self.confirm.show_details(details)
        self.steps.setCurrentIndex(2)

    def _edit_details(self) -> None:
        self.steps.setCurrentIndex(1)

    def _view_orders(self) -> None:
        order = self.confirm.order
        self.show_cart()
        if order is not None:
            self.checked_out.emit(order)

    def _cart_changed(self) -> None:
        self.refresh()
        if self.confirm.placing:
            return
        if self.confirm.placed:
            # The order has been placed. A later cart change means a new shopping trip.
            if self.session.cart:
                self.show_cart()
        elif self.step != "cart":
            if not self.session.cart:
                self.show_cart()
            else:
                self.confirm.refresh()

    def hideEvent(self, event) -> None:
        if self.confirm.placed:
            self.show_cart()
        super().hideEvent(event)

    def refresh(self) -> None:
        while self.items.count():
            widget = self.items.takeAt(0).widget()
            if widget is not None:
                widget.setParent(None)
                widget.deleteLater()
        for index, book in enumerate(self.session.cart):
            card = QFrame()
            card.setProperty("card", True)
            row = QHBoxLayout(card)
            row.setContentsMargins(14, 10, 14, 10)
            text = QVBoxLayout()
            text.setSpacing(0)
            text.addWidget(make_label(book.title, "book"))
            text.addWidget(make_label(book.author, "author"))
            row.addLayout(text, 1)
            row.addWidget(make_label(book.price_text, "price"))
            remove = make_button("Remove", "link", height=24)
            remove.clicked.connect(lambda _=False, i=index: self.session.remove_from_cart(i))
            row.addWidget(remove)
            self.items.addWidget(card)
        has_items = bool(self.session.cart)
        self.empty.setVisible(not has_items)
        self.total.setVisible(has_items)
        self.checkout.setEnabled(has_items)
        self.total.setText(f"Total: ${self.session.cart_total:.2f}")
