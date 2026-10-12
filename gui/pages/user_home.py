"""Signed-in home screen (wireframe 3) and the tabs behind its nav bar."""
from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QFrame, QHBoxLayout, QMessageBox, QScrollArea, QVBoxLayout, QWidget

from .. import data
from ..session import Session
from ..widgets import (
    Avatar,
    BadgeButton,
    Page,
    ProgressBar,
    SearchField,
    ThemeSwitch,
    make_button,
    make_label,
)
from .catalog import BookGrid, HorizontalRow, RecoCard, UserBookCard


def _scroll_page(margins=(16, 14, 16, 18), spacing=12) -> tuple[Page, QVBoxLayout]:
    """A Page containing a vertical scroll area; returns (page, content layout)."""
    page = Page()
    outer = QVBoxLayout(page)
    outer.setContentsMargins(0, 0, 0, 0)
    scroll = QScrollArea()
    scroll.setWidgetResizable(True)
    scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
    outer.addWidget(scroll)
    content = QWidget()
    col = QVBoxLayout(content)
    col.setContentsMargins(*margins)
    col.setSpacing(spacing)
    scroll.setWidget(content)
    return page, col


class OrderStatusCard(QFrame):
    track_requested = Signal()

    def __init__(self, order: data.Order) -> None:
        super().__init__()
        self.setProperty("card", True)
        col = QVBoxLayout(self)
        col.setContentsMargins(16, 14, 16, 16)
        col.setSpacing(10)
        row = QHBoxLayout()
        row.addWidget(make_label(f"Order #{order.number}: {order.status}", "h3"))
        row.addStretch()
        track = make_button("Track", "linkbold", height=24)
        track.clicked.connect(self.track_requested)
        row.addWidget(track)
        col.addLayout(row)
        col.addWidget(ProgressBar(order.progress))


class UserHomePage(Page):
    cart_requested = Signal()
    orders_requested = Signal()

    def __init__(self, session: Session) -> None:
        super().__init__()
        self.session = session
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        outer.addWidget(scroll)
        content = QWidget()
        col = QVBoxLayout(content)
        col.setContentsMargins(16, 14, 16, 18)
        col.setSpacing(12)
        scroll.setWidget(content)

        # Greeting row
        header = QHBoxLayout()
        self.avatar = Avatar("N", 48)
        header.addWidget(self.avatar)
        header.addSpacing(10)
        greet = QVBoxLayout()
        greet.setSpacing(0)
        self.hello = make_label("Hi, [Name]", "h2")
        greet.addWidget(self.hello)
        greet.addWidget(make_label("What are you reading next?", "muted"))
        header.addLayout(greet)
        header.addStretch()
        self.cart_btn = BadgeButton("cart")
        self.cart_btn.clicked.connect(self.cart_requested)
        header.addWidget(self.cart_btn)
        col.addLayout(header)

        self.search = SearchField()
        self.search.textChanged.connect(self._refresh)
        col.addWidget(self.search)

        # Sections shown when not searching
        self.browse = QWidget()
        browse = QVBoxLayout(self.browse)
        browse.setContentsMargins(0, 0, 0, 0)
        browse.setSpacing(12)
        order_card = OrderStatusCard(data.SAMPLE_ORDER)
        order_card.track_requested.connect(self.orders_requested)
        browse.addWidget(order_card)
        browse.addWidget(make_label("Recommended for you", "h2"))
        row = HorizontalRow(190)
        row.set_widgets([RecoCard(b) for b in data.recommended()])
        browse.addWidget(row)
        browse.addWidget(make_label("Bestsellers", "h2"))
        self.bestsellers = BookGrid(self._make_card)
        browse.addWidget(self.bestsellers)
        col.addWidget(self.browse)

        # Search results
        self.results_box = QWidget()
        results = QVBoxLayout(self.results_box)
        results.setContentsMargins(0, 0, 0, 0)
        results.setSpacing(12)
        results.addWidget(make_label("Results", "h2"))
        self.empty = make_label("", "caption", wrap=True)
        results.addWidget(self.empty)
        self.results = BookGrid(self._make_card)
        results.addWidget(self.results)
        col.addWidget(self.results_box)
        col.addStretch()

        session.user_changed.connect(self.refresh_user)
        session.cart_changed.connect(self._update_badge)
        self.refresh_user()
        self._refresh()

    def _make_card(self, book: data.Book) -> UserBookCard:
        card = UserBookCard(book)
        card.add_requested.connect(self.session.add_to_cart)
        return card

    def focus_search(self) -> None:
        self.search.setFocus()

    def refresh_user(self) -> None:
        user = self.session.user
        first = user.name.split()[0] if user and user.name else "there"
        self.hello.setText(f"Hi, {first}")
        self.avatar.set_initial(user.initial if user else "?")
        self._update_badge()

    def _update_badge(self) -> None:
        self.cart_btn.set_count(len(self.session.cart))

    def _refresh(self) -> None:
        query = self.search.text().strip()
        searching = bool(query)
        self.browse.setVisible(not searching)
        self.results_box.setVisible(searching)
        if searching:
            books = data.search(query)
            self.empty.setText(f"No books match “{query}”.")
            self.empty.setVisible(not books)
            self.results.set_books(books)
        else:
            self.bestsellers.set_books(data.bestsellers())


class CartPage(Page):
    def __init__(self, session: Session) -> None:
        super().__init__()
        self.session = session
        outer = QVBoxLayout(self)
        outer.setContentsMargins(16, 14, 16, 18)
        outer.setSpacing(12)
        outer.addWidget(make_label("Your cart", "h2"))
        self.items = QVBoxLayout()
        self.items.setSpacing(10)
        outer.addLayout(self.items)
        self.empty = make_label("Your cart is empty. Add a book from Home.", "caption", wrap=True)
        outer.addWidget(self.empty)
        outer.addStretch()
        self.total = make_label("", "h3")
        outer.addWidget(self.total)
        self.checkout = make_button("Checkout", "primary", height=54)
        self.checkout.clicked.connect(
            lambda: QMessageBox.information(self, "Checkout", "Checkout isn't built yet.")
        )
        outer.addWidget(self.checkout)
        session.cart_changed.connect(self.refresh)
        self.refresh()

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


class OrdersPage(Page):
    def __init__(self) -> None:
        super().__init__()
        outer = QVBoxLayout(self)
        outer.setContentsMargins(16, 14, 16, 18)
        outer.setSpacing(12)
        outer.addWidget(make_label("Orders", "h2"))
        outer.addWidget(OrderStatusCard(data.SAMPLE_ORDER))
        outer.addWidget(make_label("Full order history and tracking are coming soon.", "caption", wrap=True))
        outer.addStretch()


class AccountPage(Page):
    sign_out_requested = Signal()

    def __init__(self, session: Session) -> None:
        super().__init__()
        self.session = session
        outer = QVBoxLayout(self)
        outer.setContentsMargins(16, 14, 16, 18)
        outer.setSpacing(12)
        outer.addWidget(make_label("Account", "h2"))
        row = QHBoxLayout()
        self.avatar = Avatar("N", 56)
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
        outer.addLayout(row)
        outer.addSpacing(8)
        outer.addWidget(make_label("Appearance", "field"))
        outer.addWidget(ThemeSwitch())
        outer.addStretch()
        sign_out = make_button("Sign out", "outline", height=50)
        sign_out.clicked.connect(self.sign_out_requested)
        outer.addWidget(sign_out)
        session.user_changed.connect(self.refresh)
        self.refresh()

    def refresh(self) -> None:
        user = self.session.user
        self.avatar.set_initial(user.initial if user else "?")
        self.name.setText(user.name if user else "")
        self.email.setText(user.email if user else "")
