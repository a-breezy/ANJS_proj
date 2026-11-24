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


if __name__ == "__main__":
    unittest.main()
