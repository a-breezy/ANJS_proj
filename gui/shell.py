"""The app shell: a content area above a bottom navigation bar.

There is one shell for everybody. Its tabs follow the session: visitors get
Home / Search / Ask / Sign in, and signed-in users get Cart, Orders and
Account in place of Sign in.
"""
from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QStackedWidget, QVBoxLayout

from .pages.account import AccountPage
from .pages.cart import CartPage
from .pages.chat import ChatPage
from .pages.home import HomePage
from .pages.orders import OrdersPage
from .session import Session
from .widgets import NavBar, Page

GUEST_TABS = [("home", "Home", "home"), ("search", "Search", "search"), ("ask", "Ask", "bubble"), ("signin", "Sign in", "user")]
USER_TABS = [
    ("home", "Home", "home"),
    ("search", "Search", "search"),
    ("ask", "Ask", "bubble"),
    ("cart", "Cart", "cart"),
    ("orders", "Orders", "bag"),
    ("account", "Account", "user"),
]
_MEMBERS_ONLY = {"cart", "orders", "account"}


class AppShell(Page):
    sign_in_requested = Signal()
    sign_out_requested = Signal()

    def __init__(self, session: Session) -> None:
        super().__init__()
        self.session = session
        col = QVBoxLayout(self)
        col.setContentsMargins(0, 0, 0, 0)
        col.setSpacing(0)
        self.stack = QStackedWidget()
        self.home = HomePage(session)
        self.chat = ChatPage(session)
        self.cart = CartPage(session)
        self.orders = OrdersPage(session)
        self.account = AccountPage(session)
        self._pages = {"home": self.home, "ask": self.chat, "cart": self.cart, "orders": self.orders, "account": self.account}
        for page in self._pages.values():
            self.stack.addWidget(page)
        col.addWidget(self.stack, 1)
        self.nav = NavBar(GUEST_TABS)
        self.nav.selected.connect(self.show_tab)
        col.addWidget(self.nav)

        self.home.sign_in_requested.connect(self.sign_in_requested)
        self.home.cart_requested.connect(lambda: self.show_tab("cart"))
        self.home.orders_requested.connect(lambda: self.show_tab("orders"))
        self.cart.checked_out.connect(lambda _order: self.show_orders("tracking"))
        self.account.sign_out_requested.connect(self.sign_out_requested)
        session.user_changed.connect(self._sync_tabs)
        self._sync_tabs()

    def reset(self) -> None:
        self.home.reset()
        self.chat.reset()
        self.show_tab("home")

    def current_tab(self) -> str:
        return next(k for k, page in self._pages.items() if page is self.stack.currentWidget())

    def show_tab(self, key: str) -> None:
        if key == "signin" or (key in _MEMBERS_ONLY and not self.session.signed_in):
            self.nav.set_current(self.current_tab())
            self.sign_in_requested.emit()
            return
        if key == "search":
            self.stack.setCurrentWidget(self.home)
            self.nav.set_current("search")
            self.home.focus_search()
            return
        if key == "home":
            self.home.search.clearFocus()
        self.stack.setCurrentWidget(self._pages[key])
        self.nav.set_current(key)

    def show_orders(self, tab: str) -> None:
        self.orders.show_tab(tab)
        self.show_tab("orders")

    def _sync_tabs(self) -> None:
        self.nav.set_items(USER_TABS if self.session.signed_in else GUEST_TABS)
        current = self.current_tab()
        if current in _MEMBERS_ONLY and not self.session.signed_in:
            current = "home"
        self.show_tab(current)
