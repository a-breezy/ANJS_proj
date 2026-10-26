"""Sign-in screen: Face ID tab and password tab (wireframe 1)."""
from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QButtonGroup,
    QFrame,
    QHBoxLayout,
    QLineEdit,
    QMessageBox,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from .. import auth
from ..face_dialog import FaceScanDialog
from ..store import Store
from ..widgets import Column, IconButton, Logo, Page, Viewfinder, make_button, make_label

CAPTION_IDLE = "Look straight at the camera and hold still"


class LoginPage(Page):
    signed_in = Signal(object)  # data.User
    back_requested = Signal()
    sign_up_requested = Signal()

    def __init__(self, store: Store) -> None:
        super().__init__()
        self.store = store
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        column = Column(max_width=460, margins=(22, 20, 22, 18), spacing=0)
        outer.addWidget(column)
        root = column.col

        # Header: back button, centred logo + name
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
        root.addWidget(make_label("Welcome back", "h1"))
        root.addSpacing(2)
        root.addWidget(make_label("Sign in to keep browsing and buying", "subtitle"))
        root.addSpacing(18)

        # Face | Password segmented control
        segment = QFrame()
        segment.setObjectName("segment")
        seg_row = QHBoxLayout(segment)
        seg_row.setContentsMargins(4, 4, 4, 4)
        seg_row.setSpacing(4)
        self.seg_face = IconButton("Face", "face", "muted", variant="segment", height=44, token_checked="on_seg_active")
        self.seg_password = IconButton("Password", "lock", "muted", variant="segment", height=44, token_checked="on_seg_active")
        for btn in (self.seg_face, self.seg_password):
            btn.setCheckable(True)
            seg_row.addWidget(btn, 1)
        group = QButtonGroup(self)
        group.setExclusive(True)
        group.addButton(self.seg_face)
        group.addButton(self.seg_password)
        self.seg_face.clicked.connect(lambda: self._set_mode(face=True))
        self.seg_password.clicked.connect(lambda: self._set_mode(face=False))
        root.addWidget(segment)
        root.addSpacing(14)

        self.panels = QStackedWidget()
        self.panels.addWidget(self._build_face_panel())
        self.panels.addWidget(self._build_password_panel())
        root.addWidget(self.panels)
        root.addStretch()

        # Footer links
        self.alt_link = make_button("", "link", height=26)
        self.alt_link.clicked.connect(lambda: self._set_mode(face=self.panels.currentIndex() == 1))
        root.addWidget(self.alt_link, 0, Qt.AlignmentFlag.AlignHCenter)
        root.addSpacing(6)
        new_row = QHBoxLayout()
        new_row.addStretch()
        new_row.addWidget(make_label("New here?", "caption"))
        new_row.addSpacing(4)
        create = make_button("Create an account", "linkbold", height=26)
        create.clicked.connect(self.sign_up_requested)
        new_row.addWidget(create)
        new_row.addStretch()
        root.addLayout(new_row)

        self._set_mode(face=True)

    # --- panels ---------------------------------------------------------
    def _build_face_panel(self) -> QWidget:
        panel = QWidget()
        col = QVBoxLayout(panel)
        col.setContentsMargins(0, 0, 0, 0)
        col.setSpacing(0)
        self.viewfinder = Viewfinder()
        col.addWidget(self.viewfinder)
        col.addSpacing(14)
        self.caption = make_label(CAPTION_IDLE, "caption", Qt.AlignmentFlag.AlignHCenter, wrap=True)
        col.addWidget(self.caption)
        col.addSpacing(14)
        self.scan_btn = make_button("Scan my face", "primary", height=56, icon="face", token="on_primary")
        self.scan_btn.clicked.connect(self._start_scan)
        col.addWidget(self.scan_btn)
        return panel

    def _build_password_panel(self) -> QWidget:
        panel = QWidget()
        col = QVBoxLayout(panel)
        col.setContentsMargins(0, 4, 0, 0)
        col.setSpacing(6)
        col.addWidget(make_label("Email", "field"))
        self.email = QLineEdit()
        self.email.setPlaceholderText("you@example.com")
        self.email.setFixedHeight(48)
        col.addWidget(self.email)
        col.addSpacing(8)
        col.addWidget(make_label("Password", "field"))
        pw_row = QHBoxLayout()
        pw_row.setSpacing(8)
        self.password = QLineEdit()
        self.password.setPlaceholderText("Password")
        self.password.setEchoMode(QLineEdit.EchoMode.Password)
        self.password.setFixedHeight(48)
        pw_row.addWidget(self.password, 1)
        self.show_pw = make_button("Show", "small", height=48)
        self.show_pw.setCheckable(True)
        self.show_pw.toggled.connect(self._toggle_password)
        pw_row.addWidget(self.show_pw)
        col.addLayout(pw_row)
        forgot = make_button("Forgot password?", "link", height=26)
        forgot.clicked.connect(
            lambda: QMessageBox.information(self, "Reset password", "Password reset isn't built yet.")
        )
        col.addWidget(forgot, 0, Qt.AlignmentFlag.AlignLeft)
        self.pw_error = make_label("", "error", wrap=True)
        self.pw_error.hide()
        col.addWidget(self.pw_error)
        col.addSpacing(6)
        submit = make_button("Sign in with password", "primary", height=56)
        submit.clicked.connect(self._submit_password)
        col.addWidget(submit)
        col.addStretch()
        self.email.returnPressed.connect(self.password.setFocus)
        self.password.returnPressed.connect(self._submit_password)
        return panel

    # --- behaviour ------------------------------------------------------
    def reset(self) -> None:
        """Return to a clean Face tab (called whenever the page is shown)."""
        self._cancel_scan()
        self.email.clear()
        self.password.clear()
        self.show_pw.setChecked(False)
        self.pw_error.hide()
        self.caption.setText(CAPTION_IDLE)
        self._set_mode(face=True)

    def _set_mode(self, face: bool) -> None:
        self._cancel_scan()
        self.caption.setText(CAPTION_IDLE)
        self.seg_face.setChecked(face)
        self.seg_password.setChecked(not face)
        self.panels.setCurrentIndex(0 if face else 1)
        self.alt_link.setText(
            "Camera not working? Use password instead" if face else "Prefer your face? Use Face ID instead"
        )
        if not face:
            self.email.setFocus()

    def _toggle_password(self, shown: bool) -> None:
        self.password.setEchoMode(QLineEdit.EchoMode.Normal if shown else QLineEdit.EchoMode.Password)
        self.show_pw.setText("Hide" if shown else "Show")

    def _start_scan(self) -> None:
        if not self.store.enrolled_face_accounts():
            self.caption.setText("No face enrolled yet. Create an account and run the enrollment script first.")
            return

        self.scan_btn.setEnabled(False)
        self.scan_btn.setText("Scanning...")
        self.caption.setText("Camera window opened. Look straight at it.")
        try:
            dialog = FaceScanDialog(self.store, self)
            if dialog.exec() == dialog.DialogCode.Accepted and dialog.user is not None:
                self.signed_in.emit(dialog.user)
            else:
                self.caption.setText("Scan canceled or not recognized. Try again or use password.")
        finally:
            self._cancel_scan()

    def _cancel_scan(self) -> None:
        self.viewfinder.stop()
        self.scan_btn.setEnabled(True)
        self.scan_btn.setText("Scan my face")

    def _submit_password(self) -> None:
        email, password = self.email.text(), self.password.text()
        if not email.strip():
            return self._show_pw_error("Enter your email address.")
        if not password:
            return self._show_pw_error("Enter your password.")
        user = auth.authenticate_password(self.store, email, password)
        if user is None:
            return self._show_pw_error("That email or password doesn't look right.")
        self.pw_error.hide()
        self.signed_in.emit(user)

    def _show_pw_error(self, message: str) -> None:
        self.pw_error.setText(message)
        self.pw_error.show()
