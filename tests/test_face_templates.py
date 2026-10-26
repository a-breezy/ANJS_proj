"""Tests for face enrollment storage. No webcam is needed."""
import tempfile
import unittest
from pathlib import Path

from gui import auth
from gui.store import Store


class FaceTemplateTests(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.addCleanup(self.folder.cleanup)
        self.path = Path(self.folder.name) / "store.json"
        self.store = Store(self.path)
        auth.register(self.store, "Jane", "jane@example.com", "testpassword")

    def test_enrollment_is_saved(self):
        self.store.add_face_template("jane@example.com", [0.1] * 128)
        new_store = Store(self.path)
        self.assertEqual(len(new_store.get_user("jane@example.com")["face_templates"]), 1)

    def test_multiple_scans(self):
        self.store.add_face_template("jane@example.com", [0.1] * 128)
        self.store.add_face_template("jane@example.com", [0.2] * 128)
        self.assertEqual(len(self.store.get_user("jane@example.com")["face_templates"]), 2)

    def test_unknown_account_rejected(self):
        with self.assertRaises(ValueError):
            self.store.add_face_template("nobody@example.com", [0.1] * 128)

    def test_invalid_features_rejected(self):
        with self.assertRaises(ValueError):
            self.store.add_face_template("jane@example.com", [0.1] * 10)

    def test_can_delete_scans(self):
        self.store.add_face_template("jane@example.com", [0.1] * 128)
        self.store.remove_face_templates("jane@example.com")
        self.assertNotIn("face_templates", Store(self.path).get_user("jane@example.com"))


if __name__ == "__main__":
    unittest.main()
