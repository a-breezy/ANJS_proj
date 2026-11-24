"""Landing page shared by visitors and signed-in users.

Everyone sees search, the category chips and the bestsellers. The personal
parts only appear once someone signs in: the greeting and cart button replace
the sign-in header, the order tracker shows when the user has an order on the
way, and "Recommended for you" replaces the sign-in banner.
"""
from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QButtonGroup, QHBoxLayout, QVBoxLayout, QWidget

from .. import data
from ..session import Session
from ..widgets import Avatar, BadgeButton, Banner, Logo, Page, SearchField, make_button, make_label, scroll_column
from .catalog import BookGrid, GuestBookCard, HorizontalRow, RecoCard, UserBookCard
from .orders import OrderStatusCard
<<<<<<< HEAD

PAGE_SIZE = 12  # books shown before "Show more"
BRAND_MIN_WIDTH = 460  # narrower windows show only the logo in the header

=======
from ..review_dialog import BookReviewsDialog
>>>>>>> origin

class HomePage(Page):
    sign_in_requested = Signal()
    sign_up_requested = Signal()
    book_requested = Signal(object)  # data.Book
    cart_requested = Signal()
    orders_requested = Signal()

    def __init__(self, session: Session) -> None:
        super().__init__()
        self.session = session
        self._category = "All"
        self._shown = PAGE_SIZE

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        scroll, col = scroll_column()
        outer.addWidget(scroll)

        # Header: brand + "Create account" / "Sign in" for visitors, greeting + cart once signed in
        self.guest_header = QWidget()
        header = QHBoxLayout(self.guest_header)
        header.setContentsMargins(0, 0, 0, 0)
        header.addWidget(Logo(38))
        header.addSpacing(10)
        self.brand = make_label("[App name]", "brand")
        header.addWidget(self.brand)
        header.addStretch()
        create = make_button("Create account", "outline", height=42)
        create.clicked.connect(self.sign_up_requested)
        header.addWidget(create)
        header.addSpacing(8)
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
        self.search.textChanged.connect(self._search_changed)
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
        reco_cards = [RecoCard(b) for b in data.recommended()]
        for card in reco_cards:
            card.open_requested.connect(self.book_requested)
        self.reco_row.set_widgets(reco_cards)
        reco.addWidget(self.reco_row)
        col.addWidget(self.reco_box)

        # Category chips, in a row that scrolls sideways when they don't fit
        chip_row = HorizontalRow(40)
        chip_row.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        group = QButtonGroup(self)
        group.setExclusive(True)
        chips = []
        for name in data.CATEGORIES:
            chip = make_button(name.replace("&", "&&"), "chip", height=38)  # "&" alone marks a shortcut key
            chip.setCheckable(True)
            chip.setChecked(name == "All")
            chip.clicked.connect(lambda _=False, n=name: self._set_category(n))
            group.addButton(chip)
            chips.append(chip)
        chip_row.set_widgets(chips)
        col.addWidget(chip_row)

        self.section_title = make_label("Bestsellers", "h2")
        col.addWidget(self.section_title)
        self.empty = make_label("", "caption", wrap=True)
        self.empty.hide()
        col.addWidget(self.empty)
        self.grid = BookGrid(self._make_card)
        col.addWidget(self.grid)
        self.more = make_button("Show more", "outline", height=42, token="outline")
        self.more.setMinimumWidth(180)
        self.more.clicked.connect(self._show_more)
        col.addWidget(self.more, 0, Qt.AlignmentFlag.AlignHCenter)
        col.addStretch()

        session.user_changed.connect(self.refresh)
        session.cart_changed.connect(self._update_badge)
        session.orders_changed.connect(self._update_order)
        self.refresh()

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        # On a phone-width window the name doesn't fit beside both header buttons.
        self.brand.setVisible(self.width() >= BRAND_MIN_WIDTH)

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
<<<<<<< HEAD
        card.open_requested.connect(self.book_requested)
=======
        card.reviews_requested.connect(self._open_reviews)
>>>>>>> origin
        return card

    def _open_reviews(self, book: data.Book) -> None:
        BookReviewsDialog(book, self.session, self).exec()
        
    def _update_badge(self) -> None:
        self.cart_btn.set_count(len(self.session.cart))

    def _update_order(self) -> None:
        active = self.session.active_orders
        self.order_card.setVisible(bool(active))
        if active:
            self.order_card.set_order(active[0])

    def _set_category(self, category: str) -> None:
        self._category = category
        self._shown = PAGE_SIZE
        self._refresh_books()

    def _show_more(self) -> None:
        self._shown += PAGE_SIZE
        self._refresh_books()

    def _search_changed(self) -> None:
        self._shown = PAGE_SIZE
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
        self.more.setVisible(len(books) > self._shown)
        self.grid.set_books(books[: self._shown])
