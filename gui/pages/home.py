"""Landing page shared by visitors and signed-in users.

Everyone sees search, the category chips and the bestsellers. The personal
parts only appear once someone signs in: the greeting and cart button replace
the sign-in header, the order tracker shows when the user has an order on the
way, and "Recommended for you" replaces the sign-in banner.
"""
from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QButtonGroup, QHBoxLayout, QVBoxLayout, QWidget

from .. import data
from ..session import Session
from ..widgets import Avatar, BadgeButton, Banner, Logo, Page, SearchField, make_button, make_label, scroll_column
from .catalog import BookGrid, GuestBookCard, HorizontalRow, RecoCard, UserBookCard
from .orders import OrderStatusCard


class HomePage(Page):
    sign_in_requested = Signal()
    cart_requested = Signal()
    orders_requested = Signal()

    def __init__(self, session: Session) -> None:
        super().__init__()
        self.session = session
        self._category = "All"

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        scroll, col = scroll_column()
        outer.addWidget(scroll)

        # Header: brand + "Sign in" for visitors, greeting + cart once signed in
        self.guest_header = QWidget()
        header = QHBoxLayout(self.guest_header)
        header.setContentsMargins(0, 0, 0, 0)
        header.addWidget(Logo(38))
        header.addSpacing(10)
        header.addWidget(make_label("[App name]", "brand"))
        header.addStretch()
        sign_in = make_button("Sign in", "primary", height=42)
        sign_in.setMinimumWidth(92)
        sign_in.clicked.connect(self.sign_in_requested)
        header.addWidget(sign_in)
        col.addWidget(self.guest_header)

        self.user_header = QWidget()
        header = QHBoxLayout(self.user_header)
        header.setContentsMargins(0, 0, 0, 0)
        self.avatar = Avatar("?", 48)
        header.addWidget(self.avatar)
        header.addSpacing(10)
        greet = QVBoxLayout()
        greet.setSpacing(0)
        self.hello = make_label("", "h2")
        greet.addWidget(self.hello)
        greet.addWidget(make_label("What are you reading next?", "muted"))
        header.addLayout(greet)
        header.addStretch()
        self.cart_btn = BadgeButton("cart")
        self.cart_btn.clicked.connect(self.cart_requested)
        header.addWidget(self.cart_btn)
        col.addWidget(self.user_header)

        self.search = SearchField()
        self.search.textChanged.connect(self._refresh_books)
        col.addWidget(self.search)

        # Visitors only: sign-in banner
        self.banner = Banner()
        self.banner.setFixedHeight(66)
        banner_row = QHBoxLayout(self.banner)
        banner_row.setContentsMargins(18, 0, 14, 0)
        banner_text = make_label("Browse freely. Sign in to buy and save books.", "onhighlight", wrap=True)
        banner_row.addWidget(banner_text, 1)
        banner_row.addSpacing(8)
        banner_btn = make_button("Sign in", "dark", height=40)
        banner_btn.setMinimumWidth(92)
        banner_btn.clicked.connect(self.sign_in_requested)
        banner_row.addWidget(banner_btn)
        col.addWidget(self.banner)

        # Signed-in only: latest order on the way, and recommendations
        self.order_card = OrderStatusCard()
        self.order_card.track_requested.connect(self.orders_requested)
        col.addWidget(self.order_card)
        self.reco_box = QWidget()
        reco = QVBoxLayout(self.reco_box)
        reco.setContentsMargins(0, 0, 0, 0)
        reco.setSpacing(12)
        reco.addWidget(make_label("Recommended for you", "h2"))
        self.reco_row = HorizontalRow(190)
        self.reco_row.set_widgets([RecoCard(b) for b in data.recommended()])
        reco.addWidget(self.reco_row)
        col.addWidget(self.reco_box)

        # Category chips
        chips = QHBoxLayout()
        chips.setSpacing(8)
        group = QButtonGroup(self)
        group.setExclusive(True)
        for name in data.CATEGORIES:
            chip = make_button(name, "chip", height=38)
            chip.setCheckable(True)
            chip.setChecked(name == "All")
            chip.clicked.connect(lambda _=False, n=name: self._set_category(n))
            group.addButton(chip)
            chips.addWidget(chip)
        chips.addStretch()
        col.addLayout(chips)

        self.section_title = make_label("Bestsellers", "h2")
        col.addWidget(self.section_title)
        self.empty = make_label("", "caption", wrap=True)
        self.empty.hide()
        col.addWidget(self.empty)
        self.grid = BookGrid(self._make_card)
        col.addWidget(self.grid)
        col.addStretch()

        session.user_changed.connect(self.refresh)
        session.cart_changed.connect(self._update_badge)
        session.orders_changed.connect(self._update_order)
        self.refresh()

    # --- public -----------------------------------------------------------
    def focus_search(self) -> None:
        self.search.setFocus()

    def reset(self) -> None:
        self.search.clear()

    def refresh(self) -> None:
        """Show or hide the personal sections for the current session."""
        user = self.session.user
        signed_in = user is not None
        self.guest_header.setVisible(not signed_in)
        self.banner.setVisible(not signed_in)
        self.user_header.setVisible(signed_in)
        self.reco_box.setVisible(signed_in)
        if user is not None:
            self.hello.setText(f"Hi, {user.name.split()[0]}")
            self.avatar.set_initial(user.initial)
        self._update_badge()
        self._update_order()
        self._refresh_books()

    # --- internals --------------------------------------------------------
    def _make_card(self, book: data.Book):
        if self.session.signed_in:
            card = UserBookCard(book)
            card.add_requested.connect(self.session.add_to_cart)
        else:
            card = GuestBookCard(book)
            card.sign_in_requested.connect(self.sign_in_requested)
        return card

    def _update_badge(self) -> None:
        self.cart_btn.set_count(len(self.session.cart))

    def _update_order(self) -> None:
        active = self.session.active_orders
        self.order_card.setVisible(bool(active))
        if active:
            self.order_card.set_order(active[0])

    def _set_category(self, category: str) -> None:
        self._category = category
        self._refresh_books()

    def _refresh_books(self) -> None:
        query = self.search.text().strip()
        if query:
            books = data.search(query, self._category)
            self.section_title.setText("Results")
            self.empty.setText(f"No books match “{query}”." if not books else "")
            self.empty.setVisible(not books)
        else:
            books = data.bestsellers(self._category)
            self.section_title.setText("Bestsellers")
            self.empty.hide()
        self.grid.set_books(books)
