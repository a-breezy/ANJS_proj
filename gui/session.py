"""In-memory app state: who is signed in and what is in the cart."""
from __future__ import annotations

from PySide6.QtCore import QObject, Signal

from .data import Book, User


class Session(QObject):
    user_changed = Signal()
    cart_changed = Signal()

    def __init__(self) -> None:
        super().__init__()
        self.user: User | None = None
        self.cart: list[Book] = []

    def sign_in(self, user: User) -> None:
        self.user = user
        self.user_changed.emit()

    def sign_out(self) -> None:
        self.user = None
        self.cart.clear()
        self.user_changed.emit()
        self.cart_changed.emit()

    def add_to_cart(self, book: Book) -> None:
        self.cart.append(book)
        self.cart_changed.emit()

    def remove_from_cart(self, index: int) -> None:
        if 0 <= index < len(self.cart):
            del self.cart[index]
            self.cart_changed.emit()

    @property
    def cart_total(self) -> float:
        return sum(b.price for b in self.cart)
