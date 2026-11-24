"""Sales tax lookup by ZIP."""
from __future__ import annotations

import sys
import unittest
from decimal import Decimal
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from gui.tax import RATES_AS_OF, STATE_RATES, ZIP3_STATES, tax_for_zip  # noqa: E402


class TaxForZipTests(unittest.TestCase):
    def test_nyc(self):
        for zip_code in ("10031", "10001", "11201", "11375", "11432", "11691"):
            self.assertEqual(tax_for_zip(zip_code).rate, Decimal("0.08875"), zip_code)
        self.assertEqual(tax_for_zip("10031").note, "")

    def test_local_overrides(self):
        self.assertEqual(tax_for_zip("60614").rate, Decimal("0.1025"))
        self.assertEqual(tax_for_zip("90012").rate, Decimal("0.095"))

    def test_state_rate(self):
        quote = tax_for_zip("30301")
        self.assertEqual((quote.rate, quote.jurisdiction), (Decimal("0.0742"), "GA"))

    def test_no_sales_tax_states(self):
        for zip_code in ("97201", "59601", "03301", "19901", "99501"):
            quote = tax_for_zip(zip_code)
            self.assertIsNone(quote.rate, zip_code)
            self.assertEqual(quote.note, f"ZIP {zip_code} is not taxable, so no sales tax was charged.")

    def test_unknown_prefix_or_invalid(self):
        for zip_code in ("00000", "96999", "09012", "34012", "96401", "1234", "abcde", ""):
            quote = tax_for_zip(zip_code)
            self.assertIsNone(quote.rate, zip_code)
            self.assertIn("is not taxable", quote.note)

    def test_zip_plus_four(self):
        quote = tax_for_zip("10031-1234")
        self.assertEqual(quote.rate, Decimal("0.08875"))
        self.assertIsNone(tax_for_zip("97201-0001").rate)
        self.assertIn("ZIP 97201 is not", tax_for_zip("97201-0001").note)

    def test_table_is_consistent(self):
        self.assertTrue(RATES_AS_OF)
        for _lo, _hi, state in ZIP3_STATES:
            self.assertIn(state, STATE_RATES)
        ranges = sorted((lo, hi) for lo, hi, _ in ZIP3_STATES)
        for (_, prev_hi), (next_lo, _) in zip(ranges, ranges[1:]):
            self.assertLess(prev_hi, next_lo)


if __name__ == "__main__":
    unittest.main()
