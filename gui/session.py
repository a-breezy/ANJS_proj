"""In-memory app state: who is signed in, what is in the cart, and their orders."""
from __future__ import annotations

from PySide6.QtCore import QObject, Signal

from .data import Book, Order, User
from .store import Store


class Session(QObject):
    user_changed = Signal()
    cart_changed = Signal()
    orders_changed = Signal()

    def __init__(self, store: Store | None = None) -> None:
        super().__init__()
        self.store = store or Store()
        self.user: User | None = None
        self.cart: list[Book] = []

    @property
    def signed_in(self) -> bool:
        return self.user is not None

    def sign_in(self, user: User) -> None:
        self.user = user
        self.user_changed.emit()
        self.orders_changed.emit()

    def sign_out(self) -> None:
        self.user = None
        self.cart.clear()
        self.user_changed.emit()
        self.cart_changed.emit()
        self.orders_changed.emit()

    def add_to_cart(self, book: Book) -> None:
        self.cart.append(book)
        self.cart_changed.emit()

    def remove_from_cart(self, index: int) -> None:
        if 0 <= index < len(self.cart):
            del self.cart[index]
            self.cart_changed.emit()

    @property
    def cart_total(self) -> float:
        subtotal = sum(b.price for b in self.cart)
        discount = self.user.discount if self.user else 0.0
        return round(subtotal * (1 - discount), 2)

    # --- orders -----------------------------------------------------------
    @property
    def orders(self) -> list[Order]:
        """The signed-in user's orders, newest first."""
        if self.user is None:
            return []
        return [Order.from_record(r) for r in reversed(self.store.orders_for(self.user.email))]

    @property
    def active_orders(self) -> list[Order]:
        return [o for o in self.orders if o.active]

    @property
    def purchases(self) -> list[tuple[Book, Order]]:
        """Every book the user has bought, newest first."""
        return [(book, order) for order in self.orders for book in order.books]

    def checkout(self) -> Order | None:
        if self.user is None or self.user.is_visitor or not self.cart:
            return None
        order = Order.from_record(self.store.add_order(self.user.email, [b.id for b in self.cart]))
        updated_user = self.store.get_user(self.user.email)
        if updated_user is not None and updated_user["role"] != self.user.role:
            self.user = User(
                name=self.user.name,
                email=self.user.email,
                role=updated_user["role"]
            )
            self.user_changed.emit()
        self.cart.clear()
        self.cart_changed.emit()
        self.orders_changed.emit()
        return order
