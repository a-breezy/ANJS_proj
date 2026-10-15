"""Main window and entry point."""
from __future__ import annotations

import argparse
import sys

from PySide6.QtGui import QAction, QFont, QKeySequence
from PySide6.QtWidgets import QApplication, QMainWindow, QStackedWidget

from .data import User
from .session import Session
from .shell import AppShell
from .pages.login import LoginPage
from .pages.signup import SignUpPage
from .store import Store
from .theme import FONT_FAMILIES, PALETTES, build_qss, theme


class MainWindow(QMainWindow):
    """Hosts the three screens: the app shell (home and tabs), sign in and sign up."""

    def __init__(self, store: Store | None = None) -> None:
        super().__init__()
        self.setWindowTitle("Digital Bookstore")
        self.resize(1100, 800)
        self.setMinimumSize(370, 640)

        self.session = Session(store)
        self.stack = QStackedWidget()
        self.setCentralWidget(self.stack)

        self.shell = AppShell(self.session)
        self.login = LoginPage(self.session.store)
        self.signup = SignUpPage(self.session.store)
        for screen in (self.shell, self.login, self.signup):
            self.stack.addWidget(screen)

        self.shell.sign_in_requested.connect(self.show_login)
        self.shell.sign_out_requested.connect(self._on_signed_out)
        self.login.back_requested.connect(self.show_home)
        self.login.sign_up_requested.connect(self.show_signup)
        self.login.signed_in.connect(self._on_signed_in)
        self.signup.back_requested.connect(self.show_login)
        self.signup.sign_in_requested.connect(self.show_login)
        self.signup.signed_up.connect(self._on_signed_in)

        self._build_menu()
        self.show_home()

    def _build_menu(self) -> None:
        view = self.menuBar().addMenu("&View")
        self.mint_action = QAction("Mint theme", self, checkable=True)
        self.mint_action.setShortcut(QKeySequence("Ctrl+T"))
        self.mint_action.setChecked(theme.key == "mint")
        self.mint_action.toggled.connect(lambda on: theme.set_theme("mint" if on else "dark"))
        theme.changed.connect(self._sync_menu)
        view.addAction(self.mint_action)

    def _sync_menu(self) -> None:
        self.mint_action.blockSignals(True)
        self.mint_action.setChecked(theme.key == "mint")
        self.mint_action.blockSignals(False)

    # --- navigation -----------------------------------------------------
    def show_home(self) -> None:
        self.stack.setCurrentWidget(self.shell)

    def show_login(self) -> None:
        self.login.reset()
        self.stack.setCurrentWidget(self.login)

    def show_signup(self) -> None:
        self.signup.reset()
        self.stack.setCurrentWidget(self.signup)

    def _on_signed_in(self, user: User) -> None:
        self.session.sign_in(user)
        self.shell.reset()
        self.show_home()

    def _on_signed_out(self) -> None:
        self.session.sign_out()
        self.shell.reset()
        self.show_home()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Digital Bookstore GUI")
    parser.add_argument("--theme", choices=sorted(PALETTES), default="dark", help="starting colour theme")
    args, qt_args = parser.parse_known_args(argv if argv is not None else sys.argv[1:])

    app = QApplication([sys.argv[0], *qt_args])
    app.setApplicationName("Digital Bookstore")
    font = QFont()
    font.setFamilies(FONT_FAMILIES)
    font.setPixelSize(14)
    app.setFont(font)

    theme.set_theme(args.theme)
    app.setStyleSheet(build_qss(theme.palette))
    theme.changed.connect(lambda: app.setStyleSheet(build_qss(theme.palette)))

    window = MainWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
