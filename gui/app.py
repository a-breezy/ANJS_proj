"""Main window and entry point."""
from __future__ import annotations

import argparse
import sys

from PySide6.QtGui import QAction, QFont, QKeySequence
from PySide6.QtWidgets import QApplication, QMainWindow, QStackedWidget

from .data import User
from .session import Session
from .shell import GuestShell, UserShell
from .pages.login import LoginPage
from .theme import FONT_FAMILIES, PALETTES, build_qss, theme


class MainWindow(QMainWindow):
    """Hosts the three screens: guest home, login and signed-in home."""

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("[App name] - Digital Bookstore")
        self.resize(410, 860)
        self.setMinimumSize(370, 640)

        self.session = Session()
        self.stack = QStackedWidget()
        self.setCentralWidget(self.stack)

        self.guest = GuestShell()
        self.login = LoginPage()
        self.user = UserShell(self.session)
        for screen in (self.guest, self.login, self.user):
            self.stack.addWidget(screen)

        self.guest.sign_in_requested.connect(self.show_login)
        self.login.back_requested.connect(self.show_guest)
        self.login.signed_in.connect(self._on_signed_in)
        self.user.sign_out_requested.connect(self._on_signed_out)

        self._build_menu()
        self.show_guest()

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
    def show_guest(self) -> None:
        self.stack.setCurrentWidget(self.guest)

    def show_login(self) -> None:
        self.login.reset()
        self.stack.setCurrentWidget(self.login)

    def _on_signed_in(self, user: User) -> None:
        self.session.sign_in(user)
        self.user.reset()
        self.stack.setCurrentWidget(self.user)

    def _on_signed_out(self) -> None:
        self.session.sign_out()
        self.guest.reset()
        self.show_guest()


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
