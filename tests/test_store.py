"""Store tests: no PySide, camera, or network needed."""
import os
import sys
import tempfile
import unittest
from pathlib import Path

os.environ.setdefault("ANJS_CATALOG", "sample")

from gui import auth
from gui.store import Store

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))


class StoreTestCase(unittest.TestCase):
    def setUp(self):
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        self.path = Path(folder.name) / "store.json"
        self.store = Store(self.path)


class RoleTests(StoreTestCase):
    def rec(self, email, **extra):
        return {"name": "N", "email": email, "salt": "", "hash": "", **extra}

    def test_add_user_honors_role(self):
        self.store.add_user(self.rec("su@example.com", role="SU"))
        self.assertEqual(self.store.get_user("su@example.com")["role"], "SU")

    def test_add_user_defaults_to_rc(self):
        self.store.add_user(self.rec("a@example.com"))
        self.assertEqual(self.store.get_user("a@example.com")["role"], "RC")

    def test_add_user_keeps_supplied_counters(self):
        self.store.add_user(self.rec("a@example.com", purchase_count=5, total_spent=9.5))
        user = self.store.get_user("a@example.com")
        self.assertEqual((user["purchase_count"], user["total_spent"]), (5, 9.5))

    def test_invalid_role_raises(self):
        for bad in ("VS", "admin", ""):
            with self.assertRaises(ValueError):
                self.store.add_user(self.rec("x@example.com", role=bad))
        self.assertIsNone(self.store.get_user("x@example.com"))

    def test_register_always_creates_rc(self):
        user = auth.register(self.store, "Jane", "jane@example.com", "password123")
        self.assertEqual(user.role, "RC")
        self.assertEqual(self.store.get_user("jane@example.com")["role"], "RC")

    def test_set_role(self):
        auth.register(self.store, "Jane", "jane@example.com", "password123")
        self.store.set_role("jane@example.com", "SU")
        self.assertEqual(Store(self.path).get_user("jane@example.com")["role"], "SU")
        with self.assertRaises(ValueError):
            self.store.set_role("jane@example.com", "VS")

    def test_set_role_unknown_email_raises(self):
        with self.assertRaises(ValueError):
            self.store.set_role("nobody@example.com", "SU")

    def test_create_su_script_helper(self):
        import create_su
        create_su.create_su(self.store, "Root", "root@example.com", "password123")
        self.assertEqual(self.store.get_user("root@example.com")["role"], "SU")
        with self.assertRaises(auth.AuthError):
            create_su.create_su(self.store, "Root", "root@example.com", "password123")


class StaleWriterTests(StoreTestCase):
    def test_second_writer_does_not_clobber_first(self):
        auth.register(self.store, "Jane", "jane@example.com", "password123")
        a, b = Store(self.path), Store(self.path)  # b opened before a's change
        a.add_face_template("jane@example.com", [0.5] * 128)
        b.update_user("jane@example.com", lambda u: u.update(shipping_address="1 Main St"))
        user = Store(self.path).get_user("jane@example.com")
        self.assertEqual(len(user["face_templates"]), 1)
        self.assertEqual(user["shipping_address"], "1 Main St")

    def test_template_survives_later_review_submission(self):
        from gui.reviews import ReviewService
        auth.register(self.store, "Jane", "jane@example.com", "password123")
        service = ReviewService(self.store)  # opened before enrollment
        Store(self.path).add_face_template("jane@example.com", [0.5] * 128)  # enroll script
        service.submit_review(1, "Jane", "jane@example.com", 5, "great")
        user = Store(self.path).get_user("jane@example.com")
        self.assertEqual(len(user["face_templates"]), 1)
        self.assertEqual(len(Store(self.path).get_reviews(1)), 1)

    def test_reads_see_other_writers_changes(self):
        other = Store(self.path)
        auth.register(other, "Jane", "jane@example.com", "password123")
        self.assertIsNotNone(self.store.get_user("jane@example.com"))

    def test_failed_update_saves_nothing(self):
        def boom(data):
            data["next_order"] = 999
            raise RuntimeError
        with self.assertRaises(RuntimeError):
            self.store.update(boom)
        self.assertNotEqual(Store(self.path)._data["next_order"], 999)
        self.assertNotEqual(self.store._data["next_order"], 999)


if __name__ == "__main__":
    unittest.main()
