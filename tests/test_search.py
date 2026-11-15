"""Catalogue search tests (in-memory FTS5 index, no network)."""
from __future__ import annotations

import os
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.environ.setdefault("ANJS_CATALOG", "sample")  # tests use the 8 sample books

from gui.data import Book  # noqa: E402
from gui.search import CatalogIndex  # noqa: E402

BOOKS = [
    Book(84, "Frankenstein", "Mary Wollstonecraft Shelley", 9.99, "Sci-fi & fantasy", 0,
         description="A young scientist creates a living creature.", subjects=("Monsters", "Gothic fiction")),
    Book(345, "Dracula", "Bram Stoker", 14.99, "Horror & gothic", 1,
         description="Count Dracula moves from Transylvania to England.", subjects=("Vampires", "Gothic fiction")),
    Book(3420, "A Vindication of the Rights of Woman", "Mary Wollstonecraft", 9.99, "Philosophy & religion", 2,
         description="An early work of feminist philosophy that mentions Frankenstein's author's mother.",
         subjects=("Women's rights",)),
]


class SearchTests(unittest.TestCase):
    def setUp(self) -> None:
        self.index = CatalogIndex(BOOKS)

    def ids(self, query: str) -> list[int]:
        return [b.id for b in self.index.search(query)]

    def test_title_match_ranks_above_description_match(self) -> None:
        self.assertEqual(self.ids("frankenstein"), [84, 3420])

    def test_author_and_prefix(self) -> None:
        self.assertEqual(self.ids("stok"), [345])
        self.assertEqual(sorted(self.ids("wollstonecraft")), [84, 3420])

    def test_subjects_are_searched(self) -> None:
        self.assertEqual(self.ids("vampires"), [345])
        self.assertEqual(sorted(self.ids("gothic")), [84, 345])

    def test_all_words_must_match(self) -> None:
        self.assertEqual(self.ids("gothic vampires"), [345])

    def test_misspelling_is_corrected(self) -> None:
        self.assertEqual(self.ids("frankenstien")[0], 84)
        self.assertEqual(self.ids("drakula"), [345])

    def test_misspelled_word_still_matches_alongside_exact_hits(self) -> None:
        # "wolstonecraft" matches nothing exactly, so it also searches "wollstonecraft"
        self.assertEqual(sorted(self.ids("wolstonecraft")), [84, 3420])
        self.assertEqual(self.ids("dracula stokr"), [345])

    def test_operators_and_punctuation_are_plain_text(self) -> None:
        self.assertEqual(self.ids('"dracula" OR NOT'), [])
        self.assertEqual(self.ids("dracula!"), [345])
        self.assertEqual(self.ids("   "), [])


if __name__ == "__main__":
    unittest.main()
