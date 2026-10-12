"""Screen containers: a content area with the bottom navigation bar."""
from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QStackedWidget, QVBoxLayout

from .pages.guest_home import GuestHomePage
from .pages.user_home import AccountPage, CartPage, OrdersPage, UserHomePage
from .session import Session
from .widgets import NavBar, Page


class GuestShell(Page):
    """Visitor view: Home / Search / Sign in."""

    sign_in_requested = Signal()

    def __init__(self) -> None:
        super().__init__()
        col = QVBoxLayout(self)
        col.setContentsMargins(0, 0, 0, 0)
        col.setSpacing(0)
        self.home = GuestHomePage()
        self.home.sign_in_requested.connect(self.sign_in_requested)
        col.addWidget(self.home, 1)
        self.nav = NavBar([("home", "Home", "home"), ("search", "Search", "search"), ("signin", "Sign in", "user")])
        self.nav.selected.connect(self._on_nav)
        col.addWidget(self.nav)
        self.nav.set_current("home")

    def reset(self) -> None:
        self.home.reset()
        self.nav.set_current("home")

    def _on_nav(self, key: str) -> None:
        if key == "signin":
            self.nav.set_current("home")
            self.sign_in_requested.emit()
            return
        self.nav.set_current(key)
        if key == "search":
            self.home.focus_search()
        else:
            self.home.search.clearFocus()


class UserShell(Page):
    """Signed-in view: Home / Search / Cart / Orders / Account."""

    sign_out_requested = Signal()

    def __init__(self, session: Session) -> None:
        super().__init__()
        col = QVBoxLayout(self)
        col.setContentsMargins(0, 0, 0, 0)
        col.setSpacing(0)
        self.stack = QStackedWidget()
        self.home = UserHomePage(session)
        self.cart = CartPage(session)
        self.orders = OrdersPage()
        self.account = AccountPage(session)
        self._pages = {"home": self.home, "cart": self.cart, "orders": self.orders, "account": self.account}
        for page in self._pages.values():
            self.stack.addWidget(page)
        col.addWidget(self.stack, 1)
        self.nav = NavBar(
            [
                ("home", "Home", "home"),
                ("search", "Search", "search"),
                ("cart", "Cart", "cart"),
                ("orders", "Orders", "bag"),
                ("account", "Account", "user"),
            ]
        )
        self.nav.selected.connect(self.show_tab)
        col.addWidget(self.nav)
        self.home.cart_requested.connect(lambda: self.show_tab("cart"))
        self.home.orders_requested.connect(lambda: self.show_tab("orders"))
        self.account.sign_out_requested.connect(self.sign_out_requested)
        self.show_tab("home")

    def reset(self) -> None:
        self.home.search.clear()
        self.show_tab("home")

    def show_tab(self, key: str) -> None:
        if key == "search":
            self.stack.setCurrentWidget(self.home)
            self.nav.set_current("search")
            self.home.focus_search()
            return
        self.stack.setCurrentWidget(self._pages[key])
        self.nav.set_current(key)
