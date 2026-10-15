"""Book cards and grids shared by the guest and signed-in home screens."""
from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QFrame, QGridLayout, QHBoxLayout, QScrollArea, QVBoxLayout, QWidget

from ..data import Book
from ..widgets import BookCover, make_button, make_label


class GuestBookCard(QFrame):
    """Cover, title, author, price and a locked 'Sign in to buy' button."""

    sign_in_requested = Signal()

    def __init__(self, book: Book) -> None:
        super().__init__()
        self.setProperty("card", True)
        col = QVBoxLayout(self)
        col.setContentsMargins(8, 8, 8, 10)
        col.setSpacing(3)
        col.addWidget(BookCover(book.cover, 86))
        col.addSpacing(4)
        col.addWidget(make_label(book.title, "book", wrap=True))
        col.addWidget(make_label(book.author, "author", wrap=True))
        col.addWidget(make_label(book.price_text, "price"))
        col.addSpacing(2)
        buy = make_button("Sign in to buy", "outline", height=38, icon="lock", token="outline")
        buy.clicked.connect(self.sign_in_requested)
        col.addWidget(buy)
        col.addStretch()


class UserBookCard(QFrame):
    """Title, price and an 'Add to cart' button."""

    add_requested = Signal(object)  # Book

    def __init__(self, book: Book) -> None:
        super().__init__()
        self.setProperty("card", True)
        col = QVBoxLayout(self)
        col.setContentsMargins(14, 12, 14, 12)
        col.setSpacing(4)
        col.addWidget(make_label(book.title, "book", wrap=True))
        col.addWidget(make_label(book.author, "author", wrap=True))
        col.addWidget(make_label(book.price_text, "price"))
        col.addSpacing(4)
        add = make_button("Add to cart", "primary", height=42)
        add.clicked.connect(lambda: self.add_requested.emit(book))
        col.addWidget(add)
        col.addStretch()


class RecoCard(QWidget):
    """Square cover with title and price (horizontal 'Recommended' row)."""

    def __init__(self, book: Book) -> None:
        super().__init__()
        self.setFixedWidth(106)
        col = QVBoxLayout(self)
        col.setContentsMargins(0, 0, 0, 0)
        col.setSpacing(2)
        col.addWidget(BookCover(book.cover, 112, square=True))
        col.addSpacing(4)
        title = make_label(book.title, "book", wrap=True)
        col.addWidget(title)
        col.addWidget(make_label(book.price_text, "price"))
        col.addStretch()


# (minimum grid width in px, columns), widest first. A phone-sized window
# shows two cards per row; the row grows to three and then four on desktop.
BREAKPOINTS = ((760, 4), (540, 3), (0, 2))
MAX_COLUMNS = BREAKPOINTS[0][1]


def columns_for(width: int) -> int:
    return next(cols for min_width, cols in BREAKPOINTS if width >= min_width)


class BookGrid(QWidget):
    """Responsive grid of book cards that rebuilds from a list of books."""

    def __init__(self, factory) -> None:
        super().__init__()
        self._factory = factory
        self._cards: list[QWidget] = []
        self._columns = columns_for(0)
        self._grid = QGridLayout(self)
        self._grid.setContentsMargins(0, 0, 0, 0)
        self._grid.setSpacing(12)

    @property
    def columns(self) -> int:
        return self._columns

    def count(self) -> int:
        """Number of book cards currently shown."""
        return len(self._cards)

    def set_factory(self, factory) -> None:
        self._factory = factory

    def set_books(self, books: list[Book]) -> None:
        for card in self._cards:
            self._grid.removeWidget(card)
            card.setParent(None)
            card.deleteLater()
        self._cards = [self._factory(book) for book in books]
        self._place()

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        columns = columns_for(self.width())
        if columns != self._columns:
            self._columns = columns
            self._place()

    def _place(self) -> None:
        for card in self._cards:
            self._grid.removeWidget(card)
        for col in range(MAX_COLUMNS):
            self._grid.setColumnStretch(col, 1 if col < self._columns else 0)
        for i, card in enumerate(self._cards):
            self._grid.addWidget(card, i // self._columns, i % self._columns, Qt.AlignmentFlag.AlignTop)


class HorizontalRow(QScrollArea):
    """Horizontally scrolling strip of widgets."""

    def __init__(self, height: int) -> None:
        super().__init__()
        self.setWidgetResizable(True)
        self.setFixedHeight(height)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setFrameShape(QFrame.Shape.NoFrame)
        inner = QWidget()
        self._row = QHBoxLayout(inner)
        self._row.setContentsMargins(0, 0, 0, 0)
        self._row.setSpacing(12)
        self.setWidget(inner)

    def set_widgets(self, widgets: list[QWidget]) -> None:
        while self._row.count():
            widget = self._row.takeAt(0).widget()
            if widget is not None:
                widget.setParent(None)
                widget.deleteLater()
        for w in widgets:
            self._row.addWidget(w)
        self._row.addStretch()
