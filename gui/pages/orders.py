"""Orders tab: tracking for orders on the way, and the history of every book bought."""
from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QFrame, QHBoxLayout, QStackedWidget, QVBoxLayout, QWidget

from .. import data
from ..session import Session
from ..widgets import Page, ProgressBar, SegmentedControl, make_button, make_label, scroll_column


def _clear(layout) -> None:
    while layout.count():
        widget = layout.takeAt(0).widget()
        if widget is not None:
            widget.setParent(None)
            widget.deleteLater()


class OrderStatusCard(QFrame):
    """Order number, status and a progress bar."""

    track_requested = Signal()

    def __init__(self, order: data.Order | None = None, show_track: bool = True) -> None:
        super().__init__()
        self.setProperty("card", True)
        col = QVBoxLayout(self)
        col.setContentsMargins(16, 14, 16, 16)
        col.setSpacing(10)
        row = QHBoxLayout()
        self.title = make_label("", "h3")
        row.addWidget(self.title)
        row.addStretch()
        track = make_button("Track", "linkbold", height=24)
        track.clicked.connect(self.track_requested)
        track.setVisible(show_track)
        row.addWidget(track)
        col.addLayout(row)
        self.detail = make_label("", "muted", wrap=True)
        col.addWidget(self.detail)
        self.progress = ProgressBar()
        col.addWidget(self.progress)
        if order is not None:
            self.set_order(order)

    def set_order(self, order: data.Order) -> None:
        self.title.setText(f"Order #{order.number}: {order.status}")
        books = order.books
        count = f"{len(books)} book" + ("" if len(books) == 1 else "s")
        self.detail.setText(f"Placed {order.placed_text} · {count}")
        self.progress.set_value(order.progress)


class HistoryRow(QFrame):
    """One book the user bought, with a 'Buy again' button."""

    buy_again = Signal(object)  # Book

    def __init__(self, book: data.Book, order: data.Order) -> None:
        super().__init__()
        self.setProperty("card", True)
        row = QHBoxLayout(self)
        row.setContentsMargins(14, 10, 14, 10)
        text = QVBoxLayout()
        text.setSpacing(0)
        text.addWidget(make_label(book.title, "book", wrap=True))
        text.addWidget(make_label(book.author, "author"))
        text.addWidget(make_label(f"Order #{order.number} · {order.placed_text}", "author"))
        row.addLayout(text, 1)
        row.addWidget(make_label(book.price_text, "price"))
        row.addSpacing(6)
        again = make_button("Buy again", "small", height=34)
        again.clicked.connect(lambda: self.buy_again.emit(book))
        row.addWidget(again)


class OrdersPage(Page):
    def __init__(self, session: Session) -> None:
        super().__init__()
        self.session = session
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        scroll, col = scroll_column(max_width=900)
        outer.addWidget(scroll)

        col.addWidget(make_label("Orders", "h2"))
        self.tabs = SegmentedControl([("tracking", "Tracking"), ("history", "History")])
        self.tabs.changed.connect(self._show)
        col.addWidget(self.tabs)

        self.panels = QStackedWidget()
        self.tracking, self.tracking_list, self.tracking_empty = self._panel("No orders on the way. Orders you place show up here.")
        self.history, self.history_list, self.history_empty = self._panel("No books yet. Every book you buy will be listed here.")
        self.panels.addWidget(self.tracking)
        self.panels.addWidget(self.history)
        col.addWidget(self.panels)
        col.addStretch()

        session.orders_changed.connect(self.refresh)
        self.refresh()

    @staticmethod
    def _panel(empty_text: str) -> tuple[QWidget, QVBoxLayout, QWidget]:
        panel = QWidget()
        col = QVBoxLayout(panel)
        col.setContentsMargins(0, 0, 0, 0)
        col.setSpacing(10)
        items = QVBoxLayout()
        items.setSpacing(10)
        col.addLayout(items)
        empty = make_label(empty_text, "caption", wrap=True)
        col.addWidget(empty)
        col.addStretch()
        return panel, items, empty

    def show_tab(self, key: str) -> None:
        self.tabs.set_current(key)
        self._show(key)

    def _show(self, key: str) -> None:
        self.panels.setCurrentWidget(self.tracking if key == "tracking" else self.history)

    def refresh(self) -> None:
        _clear(self.tracking_list)
        active = self.session.active_orders
        for order in active:
            self.tracking_list.addWidget(OrderStatusCard(order, show_track=False))
        self.tracking_empty.setVisible(not active)

        _clear(self.history_list)
        purchases = self.session.purchases
        for book, order in purchases:
            row = HistoryRow(book, order)
            row.buy_again.connect(self.session.add_to_cart)
            self.history_list.addWidget(row)
        self.history_empty.setVisible(not purchases)
