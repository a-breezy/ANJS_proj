"""Ask tab: chat with a locally hosted LLM to work out what to read next.

Replies stream in from Ollama (see :mod:`gui.llm`) on a background thread so
the window stays responsive. The model is told about the catalog and, when
someone is signed in, the books they have already bought.
"""
from __future__ import annotations

import threading

from PySide6.QtCore import QObject, Qt, QTimer, Signal
from PySide6.QtWidgets import QHBoxLayout, QLabel, QLineEdit, QVBoxLayout, QWidget

from .. import data, llm
from ..session import Session
from ..widgets import Page, make_button, make_label, scroll_column

SUGGESTIONS = [
    "Something cozy for a rainy weekend",
    "I loved a book about systems thinking. What next?",
    "Help me pick a textbook for discrete math",
]
GREETING = "Tell me what you've enjoyed lately, or what you're in the mood for, and I'll suggest a book."


class _Bridge(QObject):
    """Carries results from the worker thread back to the GUI thread."""

    chunk = Signal(int, str)
    failed = Signal(int, str)
    done = Signal(int)


def _emit(signal, *args) -> None:
    try:
        signal.emit(*args)
    except RuntimeError:  # the page was closed while the model was replying
        pass


def _stream(bridge: _Bridge, request_id: int, messages: list[dict]) -> None:
    try:
        for piece in llm.stream_chat(messages):
            _emit(bridge.chunk, request_id, piece)
    except llm.LLMError as exc:
        _emit(bridge.failed, request_id, str(exc))
    except Exception as exc:  # noqa: BLE001 - surface anything else in the chat too
        _emit(bridge.failed, request_id, f"Something went wrong talking to the model: {exc}")
    else:
        _emit(bridge.done, request_id)


class Bubble(QWidget):
    """One chat message, right-aligned for the user and left-aligned for the bot."""

    def __init__(self, text: str, role: str) -> None:
        super().__init__()
        row = QHBoxLayout(self)
        row.setContentsMargins(0, 0, 0, 0)
        self.label = QLabel()
        self.label.setProperty("role", f"bubble_{role}")
        self.label.setWordWrap(True)
        self.label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        self.label.setTextFormat(Qt.TextFormat.MarkdownText if role == "bot" else Qt.TextFormat.PlainText)
        self.set_text(text)
        if role == "user":
            row.addStretch(1)
            row.addWidget(self.label, 3)
        else:
            row.addWidget(self.label, 3)
            row.addStretch(1)

    def set_text(self, text: str) -> None:
        self.label.setText(text)


class ChatPage(Page):
    def __init__(self, session: Session) -> None:
        super().__init__()
        self.session = session
        self._history: list[dict] = []  # {"role": "user"|"assistant", "content": str}
        self._request_id = 0
        self._pending: Bubble | None = None
        self._reply = ""
        self._bridge = _Bridge(self)
        self._bridge.chunk.connect(self._on_chunk)
        self._bridge.failed.connect(self._on_failed)
        self._bridge.done.connect(self._on_done)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        self.scroll, col = scroll_column(max_width=820)
        outer.addWidget(self.scroll, 1)
        header = QHBoxLayout()
        title = QVBoxLayout()
        title.setSpacing(0)
        title.addWidget(make_label("Ask the bookseller", "h2"))
        title.addWidget(make_label(f"Runs on your computer with {llm.MODEL} (Ollama)", "muted", wrap=True))
        header.addLayout(title, 1)
        self.new_chat = make_button("New chat", "small", height=34)
        self.new_chat.clicked.connect(self.reset)
        header.addWidget(self.new_chat, 0, Qt.AlignmentFlag.AlignTop)
        col.addLayout(header)

        self.messages = QVBoxLayout()
        self.messages.setSpacing(10)
        col.addLayout(self.messages)

        self.suggestions = QWidget()
        sugg = QVBoxLayout(self.suggestions)
        sugg.setContentsMargins(0, 0, 0, 0)
        sugg.setSpacing(8)
        for text in SUGGESTIONS:
            chip = make_button(text, "chip", height=38)
            chip.clicked.connect(lambda _=False, t=text: self.send(t))
            sugg.addWidget(chip, 0, Qt.AlignmentFlag.AlignLeft)
        col.addWidget(self.suggestions)
        col.addStretch()

        # Input row, pinned below the conversation
        composer = QWidget()
        row = QHBoxLayout(composer)
        row.setContentsMargins(16, 8, 16, 12)
        row.setSpacing(8)
        self.input = QLineEdit()
        self.input.setPlaceholderText("Ask for a recommendation…")
        self.input.setFixedHeight(48)
        self.input.returnPressed.connect(self._send_input)
        row.addWidget(self.input, 1)
        self.send_btn = make_button("Send", "primary", height=48)
        self.send_btn.clicked.connect(self._send_input)
        row.addWidget(self.send_btn)
        outer.addWidget(composer)

        self.reset()

    # --- public -----------------------------------------------------------
    @property
    def busy(self) -> bool:
        return self._pending is not None

    def reset(self) -> None:
        """Start a new conversation (any reply still streaming is ignored)."""
        self._request_id += 1
        self._pending = None
        self._history.clear()
        while self.messages.count():
            widget = self.messages.takeAt(0).widget()
            if widget is not None:
                widget.setParent(None)
                widget.deleteLater()
        self.messages.addWidget(Bubble(GREETING, "bot"))
        self.suggestions.show()
        self._set_busy(False)

    def send(self, text: str) -> None:
        text = text.strip()
        if not text or self.busy:
            return
        self.suggestions.hide()
        self._history.append({"role": "user", "content": text})
        self.messages.addWidget(Bubble(text, "user"))
        self._pending = Bubble("Thinking…", "bot")
        self._reply = ""
        self.messages.addWidget(self._pending)
        self._set_busy(True)
        self._scroll_to_end()

        purchased = [book for book, _order in self.session.purchases]
        messages = [{"role": "system", "content": llm.system_prompt(data.SAMPLE_BOOKS, purchased)}, *self._history]
        threading.Thread(target=_stream, args=(self._bridge, self._request_id, messages), daemon=True).start()

    # --- internals --------------------------------------------------------
    def _send_input(self) -> None:
        text = self.input.text()
        if text.strip() and not self.busy:
            self.input.clear()
            self.send(text)

    def _set_busy(self, busy: bool) -> None:
        self.send_btn.setEnabled(not busy)
        self.send_btn.setText("…" if busy else "Send")

    def _scroll_to_end(self) -> None:
        bar = self.scroll.verticalScrollBar()
        QTimer.singleShot(0, lambda: bar.setValue(bar.maximum()))

    def _on_chunk(self, request_id: int, piece: str) -> None:
        if request_id != self._request_id or self._pending is None:
            return
        self._reply += piece
        self._pending.set_text(self._reply)
        self._scroll_to_end()

    def _on_failed(self, request_id: int, message: str) -> None:
        if request_id != self._request_id or self._pending is None:
            return
        self._pending.label.setProperty("role", "bubble_error")
        self._pending.label.setTextFormat(Qt.TextFormat.PlainText)
        self._pending.set_text(message)
        self._pending.label.style().unpolish(self._pending.label)
        self._pending.label.style().polish(self._pending.label)
        self._history.pop()  # let the user resend the same question
        self._pending = None
        self._set_busy(False)

    def _on_done(self, request_id: int) -> None:
        if request_id != self._request_id or self._pending is None:
            return
        self._history.append({"role": "assistant", "content": self._reply})
        if not self._reply:
            self._pending.set_text("(The model didn't reply. Try asking another way.)")
        self._pending = None
        self._set_busy(False)
