"""Book detail page: large cover, title, price, buy button and description.

Opened by clicking any book card on the home page. Visitors see a locked
"Sign in to buy" button; signed-in users can add the book to their cart.
"""
from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QHBoxLayout, QSizePolicy, QVBoxLayout

from ..data import Book
from ..session import Session
from ..widgets import BookCover, IconButton, Page, StarRating, make_button, make_label, scroll_column

COVER_WIDTH = 200
BUTTON_WIDTH = (200, 260)  # min, max
NO_DESCRIPTION = "No description is available for this book yet."


class BookPage(Page):
    back_requested = Signal()
    sign_in_requested = Signal()

    def __init__(self, session: Session) -> None:
        super().__init__()
        self.session = session
        self.book: Book | None = None

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        scroll, col = scroll_column(max_width=900, spacing=16)
        outer.addWidget(scroll)

        self.back = IconButton(icon="chevron_left", token="text", size=22, variant="round")
        self.back.setFixedSize(44, 44)
        self.back.clicked.connect(self.back_requested)
        col.addWidget(self.back)

        # Cover on the left, details and buy button on the right
        top = QHBoxLayout()
        top.setSpacing(20)
        self.cover = BookCover(0, 290)
        self.cover.setFixedWidth(COVER_WIDTH)
        self.cover.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        top.addWidget(self.cover, 0, Qt.AlignmentFlag.AlignTop)
        info = QVBoxLayout()
        info.setSpacing(6)
        self.title = make_label("", "h1", wrap=True)
        info.addWidget(self.title)
        self.author = make_label("", "subtitle", wrap=True)
        info.addWidget(self.author)
        self.category = make_label("", "muted")
        info.addWidget(self.category)
        rating_row = QHBoxLayout()
        rating_row.setSpacing(8)
        self.stars = StarRating(18)
        rating_row.addWidget(self.stars)
        self.rating = make_label("", "muted")
        rating_row.addWidget(self.rating)
        rating_row.addStretch()
        info.addLayout(rating_row)
        info.addSpacing(6)
        self.price = make_label("", "price")
        info.addWidget(self.price)
        info.addSpacing(6)
        self.add_btn = make_button("Add to cart", "primary", height=44)
        self.add_btn.setMinimumWidth(BUTTON_WIDTH[0])
        self.add_btn.setMaximumWidth(BUTTON_WIDTH[1])
        self.add_btn.clicked.connect(self._add_to_cart)
        info.addWidget(self.add_btn, 0, Qt.AlignmentFlag.AlignLeft)
        self.sign_in_btn = make_button("Sign in to buy", "outline", height=44, icon="lock", token="outline")
        self.sign_in_btn.setMinimumWidth(BUTTON_WIDTH[0])
        self.sign_in_btn.setMaximumWidth(BUTTON_WIDTH[1])
        self.sign_in_btn.clicked.connect(self.sign_in_requested)
        info.addWidget(self.sign_in_btn, 0, Qt.AlignmentFlag.AlignLeft)
        self.added = make_label("Added to your cart.", "muted")
        self.added.hide()
        info.addWidget(self.added)
        info.addStretch()
        top.addLayout(info, 1)
        col.addLayout(top)

        col.addSpacing(4)
        col.addWidget(make_label("About this book", "h2"))
        self.description = make_label("", "caption", wrap=True)
        self.description.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        col.addWidget(self.description)
        self.subjects = make_label("", "muted", wrap=True)
        col.addWidget(self.subjects)
        col.addStretch()

        session.user_changed.connect(self._sync_buttons)
        self._sync_buttons()

    def show_book(self, book: Book) -> None:
        self.book = book
        self.cover.set_cover(book.cover, book.cover_path)
        self.title.setText(book.title)
        self.author.setText(f"by {book.author}")
        self.category.setText(f"{book.category} · {book.year}" if book.year else book.category)
        self.subjects.setText(" · ".join(book.subjects[:6]))
        self.subjects.setVisible(bool(book.subjects))
        self.stars.set_rating(book.rating)
        self.rating.setText(book.rating_text)
        self.price.setText(book.price_text)
        self.description.setText(book.description or NO_DESCRIPTION)
        self.added.hide()
        self._sync_buttons()

    def _sync_buttons(self) -> None:
        signed_in = self.session.signed_in
        self.add_btn.setVisible(signed_in)
        self.sign_in_btn.setVisible(not signed_in)

    def _add_to_cart(self) -> None:
        if self.book is not None:
            self.session.add_to_cart(self.book)
            self.added.show()
