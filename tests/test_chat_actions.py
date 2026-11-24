"""Cart actions in the Ask chat: parsing, matching and applying (no Qt, no Ollama)."""
from __future__ import annotations

import os
import sys
import unittest
from pathlib import Path

os.environ.setdefault("ANJS_CATALOG", "sample")
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from gui import chat_actions as ca  # noqa: E402
from gui import data  # noqa: E402
from gui.data import Book  # noqa: E402


def _book(i: int, title: str, author: str = "A. Writer") -> Book:
    return Book(i, title, author, 9.99, "Fiction", 0)


class FakeSession:
    def __init__(self) -> None:
        self.cart: list[Book] = []

    def add_to_cart(self, book: Book) -> None:
        self.cart.append(book)

    @property
    def cart_total(self) -> float:
        return round(sum(b.price for b in self.cart), 2)


class MarkerTests(unittest.TestCase):
    def test_markers_are_hidden_from_the_reply(self) -> None:
        raw = "Great pick! [[add_to_cart: 4]]"
        self.assertEqual(ca.strip_markers(raw), "Great pick!")

    def test_half_written_marker_is_hidden_while_streaming(self) -> None:
        self.assertEqual(ca.strip_markers("Sure. [[add_to_c", streaming=True), "Sure.")
        self.assertEqual(ca.strip_markers("Sure. [[", streaming=True), "Sure.")
        self.assertEqual(ca.strip_markers("Sure. [[add_to_cart: 4]]", streaming=True), "Sure.")

    def test_normal_brackets_are_kept(self) -> None:
        self.assertEqual(ca.strip_markers("See [id 4] for details", streaming=True), "See [id 4] for details")

    def test_extract_ids_and_titles_without_duplicates(self) -> None:
        raw = "ok [[add_to_cart: 4]] [[ADD_TO_CART: “Small Systems”]] [[add_to_cart: 4]]"
        self.assertEqual(ca.extract_add_requests(raw), ["4", "Small Systems"])

    def test_extract_is_capped(self) -> None:
        raw = " ".join(f"[[add_to_cart: {i}]]" for i in range(20))
        self.assertEqual(len(ca.extract_add_requests(raw)), ca.MAX_ADDS_PER_REPLY)

    def test_claim_detection(self) -> None:
        self.assertTrue(ca.claims_cart_change("Done! I've added it to your cart."))
        self.assertTrue(ca.claims_cart_change("I'll add Frankenstein to your cart now."))
        self.assertFalse(ca.claims_cart_change("You can open your cart from the Cart tab."))
        self.assertFalse(ca.claims_cart_change("Try The Quiet Orchard, $14.99."))


class FindBookTests(unittest.TestCase):
    BOOKS = [
        _book(1, "Frankenstein; Or, The Modern Prometheus", "Mary Shelley"),
        _book(2, "Pride and Prejudice", "Jane Austen"),
        _book(3, "The Great Gatsby", "F. Scott Fitzgerald"),
        _book(4, "The Great Escape", "P. Brickhill"),
    ]
    NO_SEARCH = staticmethod(lambda q: [])

    def find(self, query: str):
        return ca.find_books(query, self.BOOKS, self.NO_SEARCH)

    def test_exact_title_ignores_case_articles_and_punctuation(self) -> None:
        self.assertEqual([b.id for b in self.find("the great gatsby")], [3])
        self.assertEqual([b.id for b in self.find("Great Gatsby!")], [3])

    def test_main_title_matches_long_gutenberg_titles(self) -> None:
        self.assertEqual([b.id for b in self.find("Frankenstein")], [1])

    def test_title_with_and_inside(self) -> None:
        self.assertEqual([b.id for b in self.find("Pride and Prejudice")], [2])

    def test_ambiguous_returns_several(self) -> None:
        self.assertEqual({b.id for b in self.find("great")}, {3, 4})

    def test_unknown_title_finds_nothing(self) -> None:
        self.assertEqual(self.find("Quantum Gardening"), [])

    def test_filler_words_are_ignored(self) -> None:
        self.assertEqual([b.id for b in self.find("a copy of Frankenstein")], [1])
        self.assertEqual([b.id for b in self.find("the book called Pride and Prejudice")], [2])

    def test_search_fallback_only_returns_catalog_books(self) -> None:
        outsider = _book(99, "Not In Catalog")
        found = ca.find_books("zzz", self.BOOKS, lambda q: [self.BOOKS[1], outsider])
        self.assertEqual([b.id for b in found], [2])

    def test_marker_id_must_exist(self) -> None:
        self.assertEqual([b.id for b in ca.resolve_marker_arg("4")], [4])
        self.assertEqual(ca.resolve_marker_arg("999999"), [])


class ExplicitRequestTests(unittest.TestCase):
    def ask(self, message: str):
        return ca.explicit_add_request(message, FindBookTests.BOOKS)

    def test_simple_request(self) -> None:
        result = self.ask("Add Frankenstein to my cart")
        self.assertEqual([r.books[0].id for r in result], [1])

    def test_variants_of_wording(self) -> None:
        for text in (
            "please add the great gatsby to cart",
            "Put 'The Great Gatsby' in my shopping cart",
            "can you add The Great Gatsby into the basket?",
        ):
            result = self.ask(text)
            self.assertIsNotNone(result, text)
            self.assertEqual([b.id for b in result[0].books], [3], text)

    def test_two_titles(self) -> None:
        result = self.ask("add Frankenstein and Pride and Prejudice to my cart")
        self.assertEqual([r.books[0].id for r in result], [1, 2])

    def test_vague_requests_are_left_to_the_model(self) -> None:
        for text in ("add it to my cart", "add that one to my cart", "put them in my cart", "add the first one to my cart"):
            self.assertIsNone(self.ask(text), text)

    def test_not_a_cart_request(self) -> None:
        for text in ("What should I read next?", "Is my cart empty?", "I added a bookmark to my favourites"):
            self.assertIsNone(self.ask(text), text)

    def test_unknown_title_is_reported_not_added(self) -> None:
        result = self.ask("add Quantum Gardening to my cart")
        self.assertEqual(result[0].books, [])


class ApplyTests(unittest.TestCase):
    def test_run_requests_adds_and_reports(self) -> None:
        session = FakeSession()
        text, added = ca.run_requests(session, ca.explicit_add_request("add Frankenstein to my cart", FindBookTests.BOOKS))
        self.assertEqual(added, 1)
        self.assertEqual([b.id for b in session.cart], [1])
        self.assertIn("Added **Frankenstein", text)
        self.assertIn("Your cart has 1 book", text)

    def test_already_in_cart_is_not_added_twice(self) -> None:
        session = FakeSession()
        session.cart.append(FindBookTests.BOOKS[0])
        text, added = ca.run_requests(session, ca.explicit_add_request("add Frankenstein to my cart", FindBookTests.BOOKS))
        self.assertEqual(added, 0)
        self.assertEqual(len(session.cart), 1)
        self.assertIn("already in your cart", text)

    def test_not_found_adds_nothing_and_says_so(self) -> None:
        session = FakeSession()
        text, added = ca.run_requests(session, ca.explicit_add_request("add Quantum Gardening to my cart", FindBookTests.BOOKS))
        self.assertEqual((added, session.cart), (0, []))
        self.assertIn("couldn't find", text)

    def test_ambiguous_asks_which_one(self) -> None:
        session = FakeSession()
        text, added = ca.run_requests(session, ca.explicit_add_request("add great to my cart", FindBookTests.BOOKS))
        self.assertEqual((added, session.cart), (0, []))
        self.assertIn("more than one book", text)

    def test_model_markers_use_catalog_ids(self) -> None:
        session = FakeSession()
        first = data.BOOKS[0]
        lines, added = ca.run_model_markers(session, [str(first.id), "999999"])
        self.assertEqual(added, 1)
        self.assertEqual([b.id for b in session.cart], [first.id])
        self.assertTrue(any("Added" in line for line in lines))
        self.assertTrue(any("couldn't find" in line for line in lines))


if __name__ == "__main__":
    unittest.main()
