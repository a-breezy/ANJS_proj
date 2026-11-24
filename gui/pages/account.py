"""Account tab: who is signed in, appearance, and sign out."""
from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QHBoxLayout, QVBoxLayout

from ..session import Session
from ..widgets import Avatar, Column, Page, ThemeSwitch, make_button, make_label
from ..review_dialog import SuperUserModerationDialog

class AccountPage(Page):
    sign_out_requested = Signal()

    def __init__(self, session: Session) -> None:
        super().__init__()
        self.session = session
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        column = Column(max_width=560)
        outer.addWidget(column)
        col = column.col
        col.addWidget(make_label("Account", "h2"))
        row = QHBoxLayout()
        self.avatar = Avatar("?", 56)
        row.addWidget(self.avatar)
        row.addSpacing(12)
        who = QVBoxLayout()
        who.setSpacing(0)
        self.name = make_label("", "h3")
        self.email = make_label("", "muted")
        who.addWidget(self.name)
        who.addWidget(self.email)
        row.addLayout(who)
        row.addStretch()
        col.addLayout(row)
        col.addSpacing(8)
        col.addWidget(make_label("Appearance", "field"))
        col.addWidget(ThemeSwitch())
        self.su_btn = make_button("SU: Order Lists & Taboo Words", "primary", height=46)
        self.su_btn.clicked.connect(lambda: SuperUserModerationDialog(self.session, self).exec())
        col.addWidget(self.su_btn)
        col.addStretch()
        sign_out = make_button("Sign out", "outline", height=50)
        sign_out.clicked.connect(self.sign_out_requested)
        col.addWidget(sign_out)
        session.user_changed.connect(self.refresh)
        self.refresh()

    def refresh(self) -> None:
        user = self.session.user
        self.avatar.set_initial(user.initial if user else "?")
        self.name.setText(user.name if user else "")
        self.email.setText(user.email if user else "")
        self.su_btn.setVisible(bool(user and user.is_admin))
