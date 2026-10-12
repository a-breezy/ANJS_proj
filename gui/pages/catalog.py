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


class BookGrid(QWidget):
    """Two-column grid that rebuilds from a list of books."""

    def __init__(self, factory, columns: int = 2) -> None:
        super().__init__()
        self._factory = factory
        self._columns = columns
        self._grid = QGridLayout(self)
        self._grid.setContentsMargins(0, 0, 0, 0)
        self._grid.setSpacing(12)
        for col in range(columns):
            self._grid.setColumnStretch(col, 1)

    def count(self) -> int:
        """Number of book cards currently shown."""
        return sum(1 for i in range(self._grid.count()) if self._grid.itemAt(i).widget() is not None)

    def set_books(self, books: list[Book]) -> None:
        while self._grid.count():
            item = self._grid.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.setParent(None)
                widget.deleteLater()
        for i, book in enumerate(books):
            self._grid.addWidget(self._factory(book), i // self._columns, i % self._columns, Qt.AlignmentFlag.AlignTop)
        self._grid.setRowStretch(len(books) // self._columns + 1, 1)


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
