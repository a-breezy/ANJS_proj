"""GUI face login tests (no camera or model files required)."""
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication, QDialog

from gui import auth
from gui.app import MainWindow
from gui.store import Store

app = QApplication.instance() or QApplication([])


def fake_features():
    return [1.0] + [0.0] * 127


class FaceGuiTests(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.addCleanup(self.folder.cleanup)
        self.store = Store(Path(self.folder.name) / "store.json")
        self.win = MainWindow(self.store)
        self.win.show()
        self.win.show_login()

    def tearDown(self):
        self.win.close()

    def test_no_enrolled_face(self):
        self.win.login.scan_btn.click()
        self.assertIsNone(self.win.session.user)
        self.assertIn("No face enrolled", self.win.login.caption.text())

    def test_face_login_opens_account(self):
        user = auth.register(self.store, "Jane", "jane@example.com", "password123")
        self.store.add_face_template(user.email, fake_features())

        class SuccessfulScan:
            DialogCode = QDialog.DialogCode

            def __init__(self, store, parent=None):
                self.user = user

            def exec(self):
                return QDialog.DialogCode.Accepted

        with patch("gui.pages.login.FaceScanDialog", SuccessfulScan):
            self.win.login.scan_btn.click()

        self.assertEqual(self.win.session.user.email, "jane@example.com")
        self.assertIs(self.win.stack.currentWidget(), self.win.shell)

    def test_canceled_scan_does_not_sign_in(self):
        user = auth.register(self.store, "Jane", "jane@example.com", "password123")
        self.store.add_face_template(user.email, fake_features())

        class CanceledScan:
            DialogCode = QDialog.DialogCode
            user = None

            def __init__(self, store, parent=None):
                pass

            def exec(self):
                return QDialog.DialogCode.Rejected

        with patch("gui.pages.login.FaceScanDialog", CanceledScan):
            self.win.login.scan_btn.click()

        self.assertIsNone(self.win.session.user)
        self.assertTrue(self.win.login.scan_btn.isEnabled())

    def test_password_still_works(self):
        auth.register(self.store, "Jane", "jane@example.com", "password123")
        self.win.login.seg_password.click()
        self.win.login.email.setText("jane@example.com")
        self.win.login.password.setText("password123")
        self.win.login._submit_password()
        self.assertEqual(self.win.session.user.email, "jane@example.com")


if __name__ == "__main__":
    unittest.main()
