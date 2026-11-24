"""The placeholder app name must not come back."""
import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


class RenameTests(unittest.TestCase):
    def test_no_placeholder_name(self):
        for path in (ROOT / "gui").rglob("*.py"):
            self.assertNotIn("[App name]", path.read_text(encoding="utf-8"), path)


if __name__ == "__main__":
    unittest.main()
