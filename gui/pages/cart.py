"""Cart tab: books waiting to be bought, and checkout."""
from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QFrame, QHBoxLayout, QVBoxLayout

from ..session import Session
from ..widgets import Column, Page, make_button, make_label


class CartPage(Page):
    checked_out = Signal(object)  # data.Order

    def __init__(self, session: Session) -> None:
        super().__init__()
        self.session = session
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        column = Column(max_width=900)
        outer.addWidget(column)
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
        session.cart_changed.connect(self.refresh)
        self.refresh()

    def _checkout(self) -> None:
        # Payment isn't built yet: checkout records the order straight away.
        order = self.session.checkout()
        if order is not None:
            self.checked_out.emit(order)

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
