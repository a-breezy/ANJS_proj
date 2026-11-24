"""Test matching without a webcam or downloading AI models."""
import os
import tempfile
import unittest
from pathlib import Path

os.environ.setdefault("ANJS_CATALOG", "sample")  # tests use the 8 sample books

from gui import auth
from gui.face_login import find_user_by_face, similarity
from gui.store import Store


def sample(index):
    numbers = [0.0] * 128
    numbers[index] = 1.0
    return numbers


class FaceLoginTests(unittest.TestCase):
    def setUp(self):
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        self.store = Store(Path(folder.name) / "store.json")
        auth.register(self.store, "Jane", "jane@example.com", "password123")
        auth.register(self.store, "Sam", "sam@example.com", "password123")
        self.store.add_face_template("jane@example.com", sample(0))

    def test_correct_face(self):
        user = find_user_by_face(self.store, sample(0))
        self.assertEqual(user.email, "jane@example.com")

    def test_auth_face_hook(self):
        user = auth.authenticate_face(self.store, sample(0))
        self.assertEqual(user.email, "jane@example.com")

    def test_role_is_preserved(self):
        for index, role in ((3, "VC"), (4, "SU")):
            email = f"{role.lower()}@example.com"
            auth.register(self.store, role, email, "password123")
            if role != "RC":
                self.store.set_role(email, role)
            self.store.add_face_template(email, sample(index))
            self.assertEqual(find_user_by_face(self.store, sample(index)).role, role)
            # Regression: the auth hook must return the role too.
            self.assertEqual(auth.authenticate_face(self.store, sample(index)).role, role)

    def test_wrong_face(self):
        self.assertIsNone(find_user_by_face(self.store, sample(1)))

    def test_not_enrolled(self):
        self.assertIsNone(find_user_by_face(self.store, sample(2)))

    def test_second_face_sample_works(self):
        self.store.add_face_template("jane@example.com", sample(2))
        self.assertEqual(find_user_by_face(self.store, sample(2)).email,
                         "jane@example.com")

    def test_ambiguous_face_rejected(self):
        self.store.add_face_template("sam@example.com", sample(0))
        self.assertIsNone(find_user_by_face(self.store, sample(0)))

    def test_invalid_input_rejected(self):
        self.assertEqual(similarity(sample(0), [0.1]), -1.0)
        self.assertIsNone(find_user_by_face(self.store, [0.1]))

    def test_no_enrollment(self):
        self.store.remove_face_templates("jane@example.com")
        self.assertIsNone(find_user_by_face(self.store, sample(0)))


if __name__ == "__main__":
    unittest.main()
