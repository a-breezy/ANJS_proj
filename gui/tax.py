"""Sales tax by billing ZIP code.

The state comes from the ZIP's 3-digit prefix (USPS prefix ranges). Each state
has one combined state + typical-local rate, and a few local prefixes override
that where a big city differs (e.g. New York City).

These are APPROXIMATE PROTOTYPE rates for a class project. They are not for
real tax filing: real rates change by street address and product.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from decimal import Decimal

RATES_AS_OF = "2026"

# State -> combined state + average local rate, in percent.
# None means the state has no statewide sales tax (treated as not taxable).
STATE_RATES: dict[str, str | None] = {
    "AL": "9.46", "AK": None, "AZ": "8.38", "AR": "9.46", "CA": "8.82",
    "CO": "7.78", "CT": "6.35", "DE": None, "DC": "6.00", "FL": "7.02",
    "GA": "7.42", "HI": "4.50", "ID": "6.03", "IL": "8.89", "IN": "7.00",
    "IA": "6.94", "KS": "8.69", "KY": "6.00", "LA": "10.11", "ME": "5.50",
    "MD": "6.00", "MA": "6.25", "MI": "6.00", "MN": "7.49", "MS": "7.07",
    "MO": "8.40", "MT": None, "NE": "6.97", "NV": "8.24", "NH": None,
    "NJ": "6.60", "NM": "7.65", "NY": "8.54", "NC": "6.99", "ND": "6.97",
    "OH": "7.24", "OK": "9.04", "OR": None, "PA": "6.34", "RI": "7.00",
    "SC": "7.50", "SD": "6.11", "TN": "9.61", "TX": "8.20", "UT": "7.31",
    "VT": "6.39", "VA": "5.74", "WA": "9.43", "WV": "6.57", "WI": "5.70",
    "WY": "5.36",
}

# (first ZIP3, last ZIP3, state). Prefixes missing here (000-004, 006-009
# territories, 090-099 and 340/962-966 military, 969+ Pacific territories,
# other unassigned) have no rate, so they are not taxable.
ZIP3_STATES: list[tuple[int, int, str]] = [
    (10, 27, "MA"), (28, 29, "RI"), (30, 38, "NH"), (39, 49, "ME"),
    (50, 59, "VT"), (60, 69, "CT"), (70, 89, "NJ"), (100, 149, "NY"),
    (150, 196, "PA"), (197, 199, "DE"), (200, 205, "DC"), (206, 212, "MD"),
    (214, 219, "MD"), (220, 246, "VA"), (247, 268, "WV"), (270, 289, "NC"),
    (290, 299, "SC"), (300, 319, "GA"), (320, 339, "FL"), (341, 349, "FL"),
    (350, 369, "AL"), (370, 385, "TN"), (386, 397, "MS"), (398, 399, "GA"),
    (400, 427, "KY"), (430, 459, "OH"), (460, 479, "IN"), (480, 499, "MI"),
    (500, 528, "IA"), (530, 549, "WI"), (550, 567, "MN"), (569, 569, "DC"),
    (570, 577, "SD"), (580, 588, "ND"), (590, 599, "MT"), (600, 629, "IL"),
    (630, 658, "MO"), (660, 679, "KS"), (680, 693, "NE"), (700, 714, "LA"),
    (716, 729, "AR"), (730, 749, "OK"), (750, 799, "TX"), (800, 816, "CO"),
    (820, 831, "WY"), (832, 838, "ID"), (840, 847, "UT"), (850, 865, "AZ"),
    (870, 884, "NM"), (885, 885, "TX"), (889, 898, "NV"), (900, 961, "CA"),
    (967, 968, "HI"), (970, 979, "OR"), (980, 994, "WA"), (995, 999, "AK"),
]

# ZIP prefix (3 to 5 digits) -> (combined rate in percent, jurisdiction).
# The longest matching prefix wins.
LOCAL_RATES: dict[str, tuple[str, str]] = {
    "100": ("8.875", "New York City, NY"),
    "101": ("8.875", "New York City, NY"),
    "102": ("8.875", "New York City, NY"),
    "103": ("8.875", "New York City, NY"),
    "104": ("8.875", "New York City, NY"),
    "112": ("8.875", "New York City, NY"),
    "113": ("8.875", "New York City, NY"),
    "114": ("8.875", "New York City, NY"),
    "116": ("8.875", "New York City, NY"),
    "606": ("10.25", "Chicago, IL"),
    "900": ("9.50", "Los Angeles, CA"),
    "770": ("8.25", "Houston, TX"),
    "981": ("10.35", "Seattle, WA"),
}

_ZIP = re.compile(r"^(\d{5})(?:-\d{4})?$")


@dataclass(frozen=True)
class TaxQuote:
    rate: Decimal | None  # e.g. Decimal("0.08875"); None = not taxable
    jurisdiction: str
    note: str  # "" when taxable


def _not_taxable(zip_text: str, jurisdiction: str = "") -> TaxQuote:
    return TaxQuote(None, jurisdiction, f"ZIP {zip_text} is not taxable, so no sales tax was charged.")


def _percent(text: str) -> Decimal:
    return Decimal(text) / 100


def state_for_zip(zip_code: str) -> str | None:
    """The 2-letter state for a valid ZIP, or None if its prefix is not in the table."""
    match = _ZIP.match((zip_code or "").strip())
    if not match:
        return None
    prefix = int(match.group(1)[:3])
    return next((state for lo, hi, state in ZIP3_STATES if lo <= prefix <= hi), None)


def tax_for_zip(zip_code: str) -> TaxQuote:
    """The sales tax rate for a ZIP (12345 or 12345-6789)."""
    text = (zip_code or "").strip()
    match = _ZIP.match(text)
    shown = match.group(1) if match else text
    if not match:
        return _not_taxable(shown)
    digits = match.group(1)
    for length in (5, 4, 3):
        local = LOCAL_RATES.get(digits[:length])
        if local:
            return TaxQuote(_percent(local[0]), local[1], "")
    state = state_for_zip(digits)
    if state is None:
        return _not_taxable(shown)
    rate = STATE_RATES.get(state)
    if rate is None:
        return _not_taxable(shown, state)
    return TaxQuote(_percent(rate), state, "")
