"""AI preference normalisation, prompt wiring and the temperature sent to Ollama."""
import io
import json
import os
import unittest
from unittest import mock

os.environ.setdefault("ANJS_CATALOG", "sample")

from gui import data, llm


class NormalizeTests(unittest.TestCase):
    def test_defaults(self):
        self.assertEqual(llm.normalize_prefs(None), llm.DEFAULT_PREFS)
        self.assertEqual(llm.normalize_prefs({"tone": "bogus"}), llm.DEFAULT_PREFS)
        self.assertIsNot(llm.normalize_prefs({})["categories"], llm.DEFAULT_PREFS["categories"])

    def test_clamping_and_cap(self):
        self.assertEqual(llm.normalize_prefs({"suggestions": 99})["suggestions"], 5)
        self.assertEqual(llm.normalize_prefs({"suggestions": 0})["suggestions"], 1)
        self.assertEqual(llm.normalize_prefs({"suggestions": "x"})["suggestions"], 3)
        self.assertEqual(len(llm.normalize_prefs({"notes": "a" * 500})["notes"]), 200)
        cats = llm.normalize_prefs({"categories": ["Fiction", "Nope", "All"]})["categories"]
        self.assertEqual(cats, ["Fiction"])

    def test_temperature(self):
        self.assertEqual(llm.temperature({"creativity": "focused"}), 0.3)
        self.assertEqual(llm.temperature(None), 0.7)
        self.assertEqual(llm.temperature({"creativity": "creative"}), 1.0)


class PromptTests(unittest.TestCase):
    def test_prefs_in_prompt(self):
        prompt = llm.system_prompt(data.BOOKS, prefs={
            "length": "detailed", "tone": "enthusiastic", "suggestions": 2,
            "categories": ["Fiction"], "notes": "no horror"})
        self.assertIn("fuller replies", prompt)
        self.assertIn("enthusiastic", prompt)
        self.assertIn("up to 2 books", prompt)
        self.assertIn("Fiction", prompt)
        self.assertIn("no horror", prompt)
        self.assertIn("never override", prompt)

    def test_history_off_omits_purchases(self):
        book = data.BOOKS[0]
        on = llm.system_prompt(data.BOOKS, [book], prefs={"use_history": True})
        off = llm.system_prompt(data.BOOKS, [book], prefs={"use_history": False})
        self.assertIn("already bought", on)
        self.assertNotIn("already bought", off)

    def test_no_prefs_keeps_old_behaviour(self):
        self.assertIn("Keep replies short", llm.system_prompt(data.BOOKS))


class StreamTests(unittest.TestCase):
    def _sent(self, prefs):
        captured = {}

        def fake_urlopen(request, timeout=None):
            captured["body"] = json.loads(request.data)
            return io.BytesIO(b'{"message": {"content": "hi"}, "done": true}\n')

        with mock.patch("urllib.request.urlopen", fake_urlopen):
            self.assertEqual(list(llm.stream_chat([], prefs=prefs)), ["hi"])
        return captured["body"]

    def test_temperature_sent(self):
        self.assertEqual(self._sent({"creativity": "creative"})["options"]["temperature"], 1.0)
        self.assertEqual(self._sent(None)["options"]["temperature"], 0.7)


if __name__ == "__main__":
    unittest.main()
