"""AI preferences: how the Ask assistant answers this customer (sub-page of Account)."""
from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QCheckBox, QHBoxLayout, QLineEdit, QVBoxLayout

from .. import data, llm
from ..session import Session
from ..widgets import Page, SegmentedControl, make_button, make_label, scroll_column


def set_status(label, message: str, ok: bool = False) -> None:
    """Show an inline error (red) or success (muted) line; empty text hides it."""
    label.setProperty("role", "muted" if ok else "error")
    label.style().unpolish(label)
    label.style().polish(label)
    label.setText(message)
    label.setVisible(bool(message))


class PreferencesPanel(Page):
    back_requested = Signal()

    def __init__(self, session: Session) -> None:
        super().__init__()
        self.session = session
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        scroll, col = scroll_column(max_width=560)
        outer.addWidget(scroll)

        header = QHBoxLayout()
        self.back = make_button("Back", "small", height=34, icon="chevron_left")
        self.back.clicked.connect(self.back_requested)
        header.addWidget(self.back)
        header.addStretch()
        col.addLayout(header)
        col.addWidget(make_label("AI preferences", "h2"))
        col.addWidget(make_label("How the Ask assistant answers you. Changes apply to your next message.", "muted", wrap=True))

        col.addWidget(make_label("Reply length", "field"))
        self.length = SegmentedControl([(k, k.title()) for k in llm.LENGTHS], height=38)
        col.addWidget(self.length)
        col.addWidget(make_label("Tone", "field"))
        self.tone = SegmentedControl([(k, k.title()) for k in llm.TONES], height=38)
        col.addWidget(self.tone)
        col.addWidget(make_label("Book suggestions per reply", "field"))
        self.suggestions = SegmentedControl([(str(n), str(n)) for n in range(1, 6)], height=38)
        col.addWidget(self.suggestions)
        col.addWidget(make_label("Creativity", "field"))
        self.creativity = SegmentedControl([(k, k.title()) for k in llm.CREATIVITY], height=38)
        col.addWidget(self.creativity)

        col.addWidget(make_label("Favourite categories", "field"))
        self.categories: dict[str, QCheckBox] = {}
        for name in (c for c in data.CATEGORIES if c != "All"):
            box = QCheckBox(name)
            self.categories[name] = box
            col.addWidget(box)

        self.use_history = QCheckBox("Use my purchase history for recommendations")
        col.addWidget(self.use_history)

        col.addWidget(make_label("Notes for the assistant", "field"))
        self.notes = QLineEdit()
        self.notes.setMaxLength(llm.MAX_NOTES)
        self.notes.setPlaceholderText("e.g. no horror")
        self.notes.setFixedHeight(48)
        col.addWidget(self.notes)
        col.addWidget(make_label(f"Up to {llm.MAX_NOTES} characters.", "muted"))

        self.status = make_label("", "error", wrap=True)
        self.status.hide()
        col.addWidget(self.status)
        row = QHBoxLayout()
        self.save_btn = make_button("Save", "primary", height=46)
        self.save_btn.clicked.connect(self.save)
        self.reset_btn = make_button("Reset to defaults", "outline", height=46)
        self.reset_btn.clicked.connect(self.reset_to_defaults)
        row.addWidget(self.save_btn, 1)
        row.addWidget(self.reset_btn, 1)
        col.addLayout(row)
        col.addStretch()
        self.load()

    # --- state <-> widgets ------------------------------------------------
    def current_prefs(self) -> dict:
        return llm.normalize_prefs({
            "length": self.length.current,
            "tone": self.tone.current,
            "suggestions": self.suggestions.current,
            "creativity": self.creativity.current,
            "categories": [n for n, box in self.categories.items() if box.isChecked()],
            "use_history": self.use_history.isChecked(),
            "notes": self.notes.text(),
        })

    def _show(self, prefs: dict) -> None:
        self.length.set_current(prefs["length"])
        self.tone.set_current(prefs["tone"])
        self.suggestions.set_current(str(prefs["suggestions"]))
        self.creativity.set_current(prefs["creativity"])
        for name, box in self.categories.items():
            box.setChecked(name in prefs["categories"])
        self.use_history.setChecked(prefs["use_history"])
        self.notes.setText(prefs["notes"])

    def load(self) -> None:
        """Show the signed-in user's saved preferences (defaults if none or nobody)."""
        user = self.session.user
        raw: dict = {}
        if user and not user.is_visitor:
            try:
                raw = self.session.store.get_profile(user.email)["llm_prefs"]
            except ValueError:
                raw = {}
        self._show(llm.normalize_prefs(raw))
        set_status(self.status, "")

    def _store(self, prefs: dict) -> bool:
        user = self.session.user
        if not user or user.is_visitor:
            return False
        try:
            self.session.store.update_profile(user.email, llm_prefs=prefs)
        except (ValueError, KeyError):
            set_status(self.status, "Couldn't save your preferences.")
            return False
        return True

    def save(self) -> None:
        if self._store(self.current_prefs()):
            set_status(self.status, "Preferences saved.", ok=True)

    def reset_to_defaults(self) -> None:
        defaults = llm.normalize_prefs({})
        self._show(defaults)
        if self._store(defaults):
            set_status(self.status, "Reset to defaults.", ok=True)
