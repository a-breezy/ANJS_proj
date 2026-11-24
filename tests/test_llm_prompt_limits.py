"""The chat prompt stays bounded however big the catalog or conversation gets."""
from __future__ import annotations

import os
import sys
import tempfile
import unittest
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("ANJS_CATALOG", "sample")
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from PySide6.QtTest import QTest  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

from gui import auth, data, llm  # noqa: E402
from gui.app import MainWindow  # noqa: E402
from gui.store import Store  # noqa: E402

_app = QApplication.instance() or QApplication([])


def _books(n: int) -> list[data.Book]:
    return [data.Book(i + 1000, f"Title {i}", f"Author {i}", 9.99, "Fiction", 0, downloads=i) for i in range(n)]


def _catalog_lines(prompt: str) -> list[str]:
    return [line for line in prompt.splitlines() if line.startswith("- ") and " by " in line]


class PromptLimitTests(unittest.TestCase):
    def test_catalog_lines_capped(self) -> None:
        prompt = llm.system_prompt(_books(100))
        self.assertEqual(len(_catalog_lines(prompt)), llm.MAX_PROMPT_BOOKS)
        self.assertEqual(llm.MAX_PROMPT_BOOKS, 40)

    def test_small_catalog_listed_fully(self) -> None:
        self.assertEqual(len(_catalog_lines(llm.system_prompt(_books(8)))), 8)

    def test_purchased_books_are_kept(self) -> None:
        books = _books(100)
        prompt = llm.system_prompt(books, purchased=[books[0]])  # least popular book
        self.assertIn("Title 0 by", prompt)
        self.assertLessEqual(len(_catalog_lines(prompt)), llm.MAX_PROMPT_BOOKS)

    def test_query_matches_are_kept(self) -> None:
        books = _books(100)
        target = data.Book(5000, "Quantum Gardening", "Zed", 5.0, "Fiction", 0, downloads=0)
        books.append(target)
        original = data.search
        data.search = lambda q, category="All": [target]
        try:
            prompt = llm.system_prompt(books, query="quantum")
        finally:
            data.search = original
        self.assertIn("Quantum Gardening", prompt)
        self.assertEqual(len(_catalog_lines(prompt)), llm.MAX_PROMPT_BOOKS)

    def test_role_prompts_still_work(self) -> None:
        self.assertIn("registered customer", llm.system_prompt(_books(3), role="RC"))
        self.assertIn("VIP customer", llm.system_prompt(_books(3), role="VC"))
        summary = dict(total_orders=2, total_sales=10.0, total_discounts=1.0, books_sold=3)
        self.assertIn("financial report", llm.system_prompt(_books(3), role="SU", financial_summary=summary))


class ChatHistoryTests(unittest.TestCase):
    def test_only_last_12_history_messages_sent(self) -> None:
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        store = Store(Path(tmp.name) / "store.json")
        win = MainWindow(store)
        self.addCleanup(win.close)
        win.session.sign_in(auth.register(store, "Jane Doe", "jane@example.com", "correct horse"))
        chat = win.shell.chat
        seen = {}

        def fake_stream(messages, **_kwargs):
            seen["messages"] = messages
            yield "ok"

        chat._history.extend(
            {"role": "user" if i % 2 == 0 else "assistant", "content": f"m{i}"} for i in range(30)
        )
        original, llm.stream_chat = llm.stream_chat, fake_stream
        try:
            chat.send("latest question")
            waited = 0
            while chat.busy and waited < 2000:
                QTest.qWait(20)
                waited += 20
        finally:
            llm.stream_chat = original
        messages = seen["messages"]
        self.assertEqual(messages[0]["role"], "system")
        self.assertEqual(len(messages) - 1, 12)
        self.assertEqual(messages[-1], {"role": "user", "content": "latest question"})


if __name__ == "__main__":
    unittest.main()
