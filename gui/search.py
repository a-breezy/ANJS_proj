"""Catalogue search: SQLite FTS5 over titles, authors, subjects and descriptions.

The index lives in memory and is built from the loaded catalogue the first
time someone searches (about 100 books, so this takes milliseconds).

* Results are ranked with BM25. A hit in the title counts most, then the
  author, then subjects, then the description.
* Every word is matched as a prefix, so "frank" finds "Frankenstein".
* A word that isn't in any title, author or subject also matches the closest
  word that is, so "frankenstien" finds Frankenstein and "dostoevsky" finds
  Dostoyevsky.

Book text is not indexed yet; see todo.md.
"""
from __future__ import annotations

import difflib
import re
import sqlite3
from collections.abc import Iterable

from .data import Book

# bm25() weights, in column order: title, author, subjects, description
WEIGHTS = (10.0, 6.0, 3.0, 1.0)
SPELLING_CUTOFF = 0.75
_WORD = re.compile(r"\w+", re.UNICODE)


def _words(text: str) -> list[str]:
    return [w.lower() for w in _WORD.findall(text)]


class CatalogIndex:
    def __init__(self, books: Iterable[Book]) -> None:
        self._books = {b.id: b for b in books}
        self._db = sqlite3.connect(":memory:")
        self._db.execute(
            "CREATE VIRTUAL TABLE books USING fts5("
            "title, author, subjects, description, tokenize='unicode61 remove_diacritics 2')"
        )
        self._db.executemany(
            "INSERT INTO books (rowid, title, author, subjects, description) VALUES (?, ?, ?, ?, ?)",
            [(b.id, b.title, b.author, " ; ".join(b.subjects), b.description) for b in self._books.values()],
        )
        self._vocabulary = sorted({
            word
            for b in self._books.values()
            for word in _words(" ".join((b.title, b.author, *b.subjects)))
            if len(word) > 2
        })

    def search(self, query: str, limit: int = 50) -> list[Book]:
        words = _words(query)
        if not words:
            return []
        return self._match(words, limit)

    def _term(self, word: str) -> str:
        # Quote words so FTS5 operators typed by the user are treated as text.
        # A word that starts no title, author or subject word also matches its
        # closest spelling: "dostoevsky" finds Dostoyevsky.
        term = f'"{word}"*'
        if not any(v.startswith(word) for v in self._vocabulary):
            closest = self._closest(word)
            if closest != word:
                term = f'({term} OR "{closest}"*)'
        return term

    def _match(self, words: list[str], limit: int) -> list[Book]:
        expression = " AND ".join(self._term(w) for w in words)
        rows = self._db.execute(
            f"SELECT rowid FROM books WHERE books MATCH ? ORDER BY bm25(books, {', '.join(map(str, WEIGHTS))}) LIMIT ?",
            (expression, limit),
        ).fetchall()
        return [self._books[rowid] for (rowid,) in rows]

    def _closest(self, word: str) -> str:
        match = difflib.get_close_matches(word, self._vocabulary, n=1, cutoff=SPELLING_CUTOFF)
        return match[0] if match else word


_index: CatalogIndex | None = None


def catalog_index() -> CatalogIndex:
    global _index
    if _index is None:
        from .data import BOOKS

        _index = CatalogIndex(BOOKS)
    return _index
