"""Session tests (needs PySide6 QtCore only, no display)."""
import os
import tempfile
import unittest
from pathlib import Path

os.environ.setdefault("ANJS_CATALOG", "sample")

from gui import data
from gui.session import Session
from gui.store import Store


class CheckoutTests(unittest.TestCase):
    def test_no_guest_checkout(self):
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        store = Store(Path(folder.name) / "store.json")
        session = Session(store)
        session.add_to_cart(data.BOOKS[0])
        self.assertIsNone(session.checkout())
        self.assertNotIn("guest", store._data["orders"])
        self.assertEqual(len(session.cart), 1)

        session.sign_in(data.User(name="Visitor", email="", role="VS"))
        self.assertIsNone(session.checkout())
        self.assertNotIn("guest", store._data["orders"])


if __name__ == "__main__":
    unittest.main()
