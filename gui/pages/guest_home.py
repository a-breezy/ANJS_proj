"""Home screen for visitors who are not signed in (wireframe 2)."""
from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QButtonGroup, QHBoxLayout, QScrollArea, QVBoxLayout, QWidget

from .. import data
from ..widgets import Banner, Logo, Page, SearchField, make_button, make_label
from .catalog import BookGrid, GuestBookCard


class GuestHomePage(Page):
    sign_in_requested = Signal()

    def __init__(self) -> None:
        super().__init__()
        self._category = "All"

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

        # Header
        header = QHBoxLayout()
        header.addWidget(Logo(38))
        header.addSpacing(10)
        header.addWidget(make_label("[App name]", "brand"))
        header.addStretch()
        sign_in = make_button("Sign in", "primary", height=42)
        sign_in.setMinimumWidth(92)
        sign_in.clicked.connect(self.sign_in_requested)
        header.addWidget(sign_in)
        col.addLayout(header)

        self.search = SearchField()
        self.search.textChanged.connect(self._refresh)
        col.addWidget(self.search)

        # Banner
        banner = Banner()
        banner.setFixedHeight(66)
        banner_row = QHBoxLayout(banner)
        banner_row.setContentsMargins(18, 0, 14, 0)
        banner_text = make_label("Browse freely. Sign in to buy and save books.", "onhighlight", wrap=True)
        banner_text.setMaximumWidth(200)
        banner_row.addWidget(banner_text, 1)
        banner_row.addSpacing(8)
        banner_btn = make_button("Sign in", "dark", height=40)
        banner_btn.setMinimumWidth(92)
        banner_btn.clicked.connect(self.sign_in_requested)
        banner_row.addWidget(banner_btn)
        col.addWidget(banner)

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
        self._refresh()

    def focus_search(self) -> None:
        self.search.setFocus()

    def reset(self) -> None:
        self.search.clear()

    def _make_card(self, book: data.Book) -> GuestBookCard:
        card = GuestBookCard(book)
        card.sign_in_requested.connect(self.sign_in_requested)
        return card

    def _set_category(self, category: str) -> None:
        self._category = category
        self._refresh()

    def _refresh(self) -> None:
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
