"""Open Library client tests. The network is replaced with canned responses."""
from __future__ import annotations

import os
import sys
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.environ.setdefault("ANJS_CATALOG", "sample")  # tests use the 8 sample books

from gui import openlibrary  # noqa: E402
from gui.data import Book  # noqa: E402

SEARCH = {"docs": [
    {"key": "/works/OL450063W", "author_name": ["Mary Wollstonecraft Shelley"], "ratings_average": 3.9688, "ratings_count": 229},
]}
WORK = {"description": {"type": "/type/text", "value": "*Frankenstein* is an 1818 novel.\r\n\r\n----------\r\nAlso contained in: ..."}}


def fake_get(responses):
    return mock.patch.object(openlibrary, "_get", side_effect=lambda path, params=None: responses[path])


class OpenLibraryTests(unittest.TestCase):
    def test_lookup_returns_description_and_rating(self) -> None:
        with fake_get({"/search.json": SEARCH, "/works/OL450063W.json": WORK}):
            info = openlibrary.lookup("Frankenstein", "Mary Shelley")
        self.assertEqual(info.work_key, "/works/OL450063W")
        self.assertEqual(info.description, "Frankenstein is an 1818 novel.")
        self.assertEqual(info.rating, 3.97)
        self.assertEqual(info.rating_count, 229)

    def test_no_match_returns_none(self) -> None:
        with fake_get({"/search.json": {"docs": []}}):
            self.assertIsNone(openlibrary.lookup("Not a real book"))

    def test_unrated_book_has_no_rating(self) -> None:
        search = {"docs": [{"key": "/works/OL1W", "author_name": ["Someone"], "ratings_count": 0}]}
        with fake_get({"/search.json": search, "/works/OL1W.json": {"description": "Plain text."}}):
            info = openlibrary.lookup("Obscure")
        self.assertIsNone(info.rating)
        self.assertEqual(info.description, "Plain text.")

    def test_skips_works_by_other_authors(self) -> None:
        search = {"docs": [
            {"key": "/works/OL9W", "author_name": ["SparkNotes"], "ratings_average": 5.0, "ratings_count": 1},
            {"key": "/works/OL166894W", "author_name": ["Fiódor Dostoievski"], "ratings_average": 4.3, "ratings_count": 163},
        ]}
        with fake_get({"/search.json": search, "/works/OL166894W.json": {"description": "A novel."}}):
            info = openlibrary.lookup("Crime and Punishment", "Fyodor Dostoyevsky")
        self.assertEqual(info.work_key, "/works/OL166894W")
        self.assertEqual(info.rating_count, 163)

    def test_fallback_needs_matching_author_or_title(self) -> None:
        hamlet = {"docs": [{"key": "/works/OL9170454W", "title": "Hamlet", "author_name": ["William Shakespeare"]}]}
        with fake_get({"/search.json": hamlet}):
            self.assertIsNone(openlibrary.lookup("The Odyssey", "Homer"))

    def test_description_cleanup(self) -> None:
        clean = openlibrary._description_text
        self.assertEqual(clean("From [wikipedia](https://en.wikipedia.org/wiki/X):\r\nThe novel is a story of the town."),
                         "The novel is a story of the town.")
        self.assertEqual(clean("Don Quijote de la Mancha es una novela escrita por el español Miguel de Cervantes."), "")
        wiki = ("Crime and Punishment (Russian: X; IPA: \\[prʲɪstʊˈplʲenʲɪje\\]) is a novel by the author of "
                "the work.[1](https://x.org/a) It is great.\\[2\\]\r\n\r\n---\r\n\r\nSee also:\r\n\r\n- X: 1/2")
        self.assertEqual(clean(wiki), "Crime and Punishment (Russian: X) is a novel by the author of the work. It is great.")
        self.assertEqual(clean("It is a comedy of manners.[2] - [Wikipedia][1]\r\n\r\n  [1]: http://en.wikipedia.org/wiki/X"),
                         "It is a comedy of manners.")

    def test_rating_text(self) -> None:
        book = Book(1, "T", "A", 1.0, "Fiction", 0)
        self.assertEqual(book.rating_text, "No ratings yet")
        self.assertEqual(Book(1, "T", "A", 1.0, "Fiction", 0, rating=4.2, rating_count=1417).rating_text, "4.2 · 1,417 ratings")


if __name__ == "__main__":
    unittest.main()
