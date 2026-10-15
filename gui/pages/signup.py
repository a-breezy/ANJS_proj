"""Create-account screen, reached from "Create an account" on the sign-in page."""
from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QHBoxLayout, QLineEdit, QVBoxLayout

from .. import auth
from ..store import Store
from ..widgets import Column, IconButton, Logo, Page, make_button, make_label


class SignUpPage(Page):
    signed_up = Signal(object)  # data.User
    back_requested = Signal()
    sign_in_requested = Signal()

    def __init__(self, store: Store) -> None:
        super().__init__()
        self.store = store
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        column = Column(max_width=460, margins=(22, 20, 22, 18), spacing=0)
        outer.addWidget(column)
        root = column.col

        header = QHBoxLayout()
        self.back = IconButton(icon="chevron_left", token="text", size=22, variant="round")
        self.back.setFixedSize(44, 44)
        self.back.clicked.connect(self.back_requested)
        header.addWidget(self.back)
        header.addStretch()
        header.addWidget(Logo(40))
        header.addSpacing(10)
        header.addWidget(make_label("[App name]", "brand"))
        header.addStretch()
        header.addSpacing(44)
        root.addLayout(header)

        root.addSpacing(18)
        root.addWidget(make_label("Create an account", "h1", wrap=True))
        root.addSpacing(2)
        root.addWidget(make_label("Save books, check out and track your orders", "subtitle", wrap=True))
        root.addSpacing(18)

        self.name = self._field(root, "Name", "Your name")
        self.email = self._field(root, "Email", "you@example.com")
        self.password = self._field(root, "Password", f"At least {auth.MIN_PASSWORD} characters", secret=True)
        self.confirm = self._field(root, "Confirm password", "Type it again", secret=True)

        self.error = make_label("", "error", wrap=True)
        self.error.hide()
        root.addWidget(self.error)
        root.addSpacing(8)
        self.submit = make_button("Create account", "primary", height=56)
        self.submit.clicked.connect(self._submit)
        root.addWidget(self.submit)
        root.addStretch()

        have_row = QHBoxLayout()
        have_row.addStretch()
        have_row.addWidget(make_label("Already have an account?", "caption"))
        have_row.addSpacing(4)
        sign_in = make_button("Sign in", "linkbold", height=26)
        sign_in.clicked.connect(self.sign_in_requested)
        have_row.addWidget(sign_in)
        have_row.addStretch()
        root.addLayout(have_row)

        self.name.returnPressed.connect(self.email.setFocus)
        self.email.returnPressed.connect(self.password.setFocus)
        self.password.returnPressed.connect(self.confirm.setFocus)
        self.confirm.returnPressed.connect(self._submit)

    @staticmethod
    def _field(layout: QVBoxLayout, label: str, placeholder: str, secret: bool = False) -> QLineEdit:
        layout.addWidget(make_label(label, "field"))
        layout.addSpacing(6)
        field = QLineEdit()
        field.setPlaceholderText(placeholder)
        field.setFixedHeight(48)
        if secret:
            field.setEchoMode(QLineEdit.EchoMode.Password)
        layout.addWidget(field)
        layout.addSpacing(12)
        return field

    def reset(self) -> None:
        for field in (self.name, self.email, self.password, self.confirm):
            field.clear()
        self.error.hide()
        self.name.setFocus(Qt.FocusReason.OtherFocusReason)

    def _submit(self) -> None:
        if self.password.text() != self.confirm.text():
            return self._show_error("The passwords don't match.")
        try:
            user = auth.register(self.store, self.name.text(), self.email.text(), self.password.text())
        except auth.AuthError as exc:
            return self._show_error(str(exc))
        self.error.hide()
        self.signed_up.emit(user)

    def _show_error(self, message: str) -> None:
        self.error.setText(message)
        self.error.show()
