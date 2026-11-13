"""Dialogs for book reviews/ratings and Super-User (SU) moderation & order lists."""
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QMessageBox,
    QScrollArea,
    QTabWidget,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from .data import Book
from .reviews import ReviewService
from .session import Session
from .widgets import make_button, make_label


class BookReviewsDialog(QDialog):
    """Modal popup showing weighted star ratings, comments, and a review form."""

    def __init__(self, book: Book, session: Session, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.book = book
        self.session = session
        self.service = ReviewService(session.store)

        self.setWindowTitle(f"Reviews — {book.title}")
        self.resize(520, 620)

        root = QVBoxLayout(self)
        root.setSpacing(10)

        # Book header + weighted rating summary
        root.addWidget(make_label(book.title, "h2", wrap=True))
        root.addWidget(make_label(f"by {book.author}", "muted"))

        self.summary_label = make_label("", "field")
        root.addWidget(self.summary_label)

        # Scrollable review feed
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        feed_container = QWidget()
        self.feed_layout = QVBoxLayout(feed_container)
        self.feed_layout.setContentsMargins(0, 4, 4, 4)
        self.feed_layout.setSpacing(8)
        scroll.setWidget(feed_container)
        root.addWidget(scroll, 1)

        # Divider + write review section
        root.addWidget(make_label("Leave a Rating & Comment", "h3"))

        star_row = QHBoxLayout()
        star_row.addWidget(QLabel("Rating:"))
        self.star_combo = QComboBox()
        self.star_combo.addItems([
            "5 ★ — Excellent",
            "4 ★ — Good",
            "3 ★ — Average",
            "2 ★ — Poor",
            "1 ★ — Terrible",
        ])
        star_row.addWidget(self.star_combo, 1)

        user = self.session.user
        if user and not user.is_visitor and self.service.has_purchased(user.email, book.id):
            badge = make_label("✓ Verified Buyer (2x weight)", "caption")
            star_row.addWidget(badge)
        root.addLayout(star_row)

        self.comment_box = QTextEdit()
        self.comment_box.setPlaceholderText("Write your thoughts about this book...")
        self.comment_box.setFixedHeight(85)
        root.addWidget(self.comment_box)

        btn_row = QHBoxLayout()
        close_btn = make_button("Close", "outline", height=40)
        close_btn.clicked.connect(self.accept)
        submit_btn = make_button("Post Review", "primary", height=40)
        submit_btn.clicked.connect(self._on_submit)
        btn_row.addWidget(close_btn)
        btn_row.addWidget(submit_btn)
        root.addLayout(btn_row)

        self._refresh_reviews()

    def _refresh_reviews(self) -> None:
        avg, count = self.service.rating_summary(self.book.id)
        if count == 0:
            self.summary_label.setText("No ratings yet — be the first to review!")
        else:
            self.summary_label.setText(
                f"Weighted Rating: ★ {avg:.2f} / 5.0  ({count} review{'s' if count != 1 else ''}; "
                "verified buyers weighted 2x)"
            )

        while self.feed_layout.count():
            item = self.feed_layout.takeAt(0)
            if item.widget() is not None:
                item.widget().deleteLater()

        reviews = self.service.reviews_for(self.book.id)
        if not reviews:
            self.feed_layout.addWidget(make_label("No comments yet.", "muted"))
        else:
            for r in reviews:
                card = QFrame()
                card.setProperty("card", True)
                col = QVBoxLayout(card)
                col.setContentsMargins(10, 8, 10, 8)
                col.setSpacing(3)

                stars_str = "★" * int(r["stars"]) + "☆" * (5 - int(r["stars"]))
                verified_tag = "  •  ✓ Verified Buyer (2x)" if r.get("verified_buyer") else ""
                header = f"{r['author_name']}  {stars_str}{verified_tag}"
                col.addWidget(make_label(header, "field", wrap=True))
                col.addWidget(make_label(r["comment"], wrap=True))
                col.addWidget(make_label(r.get("placed", ""), "caption"))
                self.feed_layout.addWidget(card)

        self.feed_layout.addStretch()

    def _on_submit(self) -> None:
        text = self.comment_box.toPlainText().strip()
        if not text:
            QMessageBox.warning(self, "Empty Comment", "Please enter a comment before posting.")
            return

        stars = 5 - self.star_combo.currentIndex()
        user = self.session.user
        author_name = user.name if user else "Visitor"
        author_email = user.email if (user and not user.is_visitor) else None

        result = self.service.submit_review(
            book_id=self.book.id,
            author_name=author_name,
            author_email=author_email,
            stars=stars,
            comment=text,
        )

        # Sync role demotion (VC -> RC) or suspension immediately
        self.session.sync_user_from_store()

        if result["accepted"]:
            self.comment_box.clear()
            self._refresh_reviews()
            if result["masked_count"] > 0:
                QMessageBox.information(self, "Review Posted (Filtered)", result["message"])
            else:
                QMessageBox.information(self, "Review Posted", result["message"])
        else:
            QMessageBox.warning(self, "Comment Blocked", result["message"])
            if result["suspended"]:
                self.reject()


class SuperUserModerationDialog(QDialog):
    """SU-only dashboard for To-Order / No-Order lists, Taboo Words, and Suspensions."""

    def __init__(self, session: Session, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.session = session
        self.service = ReviewService(session.store)

        self.setWindowTitle("Super-User (SU) — Inventory & Moderation")
        self.resize(560, 520)

        root = QVBoxLayout(self)
        tabs = QTabWidget()
        root.addWidget(tabs)

        # Tab 1: To-Order & No-Order Lists
        order_tab = QWidget()
        order_col = QVBoxLayout(order_tab)
        order_col.addWidget(make_label("To-Order List (> 3 reviews & weighted avg > 4.0 ★)", "h3"))
        self.to_order_list = QListWidget()
        order_col.addWidget(self.to_order_list)

        order_col.addWidget(make_label("No-Order List (> 3 reviews & weighted avg < 2.0 ★)", "h3"))
        self.no_order_list = QListWidget()
        order_col.addWidget(self.no_order_list)
        tabs.addTab(order_tab, "Order Lists")

        # Tab 2: Taboo Words Management
        taboo_tab = QWidget()
        taboo_col = QVBoxLayout(taboo_tab)
        taboo_col.addWidget(make_label("Taboo Words (1-2 masked with *, 3+ blocks comment)", "muted", wrap=True))

        add_row = QHBoxLayout()
        self.word_input = QLineEdit()
        self.word_input.setPlaceholderText("Enter new taboo word...")
        add_btn = make_button("Add", "primary", height=36)
        add_btn.clicked.connect(self._add_word)
        add_row.addWidget(self.word_input, 1)
        add_row.addWidget(add_btn)
        taboo_col.addLayout(add_row)

        self.taboo_list = QListWidget()
        taboo_col.addWidget(self.taboo_list)

        rem_btn = make_button("Remove Selected Word", "outline", height=36)
        rem_btn.clicked.connect(self._remove_word)
        taboo_col.addWidget(rem_btn)
        tabs.addTab(taboo_tab, "Taboo Words")

        # Tab 3: Suspended Users
        susp_tab = QWidget()
        susp_col = QVBoxLayout(susp_tab)
        susp_col.addWidget(make_label("Suspended Accounts (2 warnings as RC)", "muted"))
        self.susp_list = QListWidget()
        susp_col.addWidget(self.susp_list)
        unsusp_btn = make_button("Reactivate Selected Account", "primary", height=36)
        unsusp_btn.clicked.connect(self._unsuspend_selected)
        susp_col.addWidget(unsusp_btn)
        tabs.addTab(susp_tab, "Suspended Users")

        close_btn = make_button("Close", "outline", height=40)
        close_btn.clicked.connect(self.accept)
        root.addWidget(close_btn, alignment=Qt.AlignmentFlag.AlignRight)

        self._refresh_all()

    def _refresh_all(self) -> None:
        self.to_order_list.clear()
        to_order = self.service.to_order_books()
        if not to_order:
            self.to_order_list.addItem("No books currently qualify for the To-Order list.")
        else:
            for book, avg, count in to_order:
                self.to_order_list.addItem(f"{book.title} by {book.author} — ★ {avg:.2f} ({count} reviews)")

        self.no_order_list.clear()
        no_order = self.service.no_order_books()
        if not no_order:
            self.no_order_list.addItem("No books currently qualify for the No-Order list.")
        else:
            for book, avg, count in no_order:
                self.no_order_list.addItem(f"{book.title} by {book.author} — ★ {avg:.2f} ({count} reviews)")

        self.taboo_list.clear()
        for w in self.service.taboo_words():
            self.taboo_list.addItem(w)

        self.susp_list.clear()
        suspended = self.service.suspended_users()
        if not suspended:
            self.susp_list.addItem("No suspended accounts.")
        else:
            for u in suspended:
                self.susp_list.addItem(f"{u['email']} ({u['name']})")

    def _add_word(self) -> None:
        if self.service.add_taboo_word(self.word_input.text()):
            self.word_input.clear()
            self._refresh_all()

    def _remove_word(self) -> None:
        item = self.taboo_list.currentItem()
        if item and self.service.remove_taboo_word(item.text()):
            self._refresh_all()

    def _unsuspend_selected(self) -> None:
        item = self.susp_list.currentItem()
        if not item or " (" not in item.text():
            return
        email = item.text().split(" (", 1)[0]
        self.service.unsuspend_user(email)
        self._refresh_all()