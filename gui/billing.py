"""Address and payment-card helpers shared by the Account page and checkout.

Only a card *summary* is ever stored: brand, last 4 digits, expiry month/year
and the cardholder name. The full card number and the CVV are checked here
and then dropped; they are never written to ``store.json`` (which is plain
text). There is no payment processor yet; a real one would hand back a token
to store instead.
"""
from __future__ import annotations

import re
from datetime import date

ADDRESS_FIELDS = ("name", "line1", "line2", "city", "state", "zip")
REQUIRED_ADDRESS_FIELDS = ("name", "line1", "city", "state", "zip")
_ZIP = re.compile(r"^\d{5}(-\d{4})?$")
_FIELD_NAMES = {"name": "Full name", "line1": "Street address", "city": "City", "state": "State", "zip": "ZIP code"}


class BillingError(ValueError):
    """Invalid address or card, with a message that can be shown to the user."""


def clean_address(raw: dict) -> dict:
    """Return a normalised address dict or raise BillingError.

    Keys: name, line1, line2 (optional), city, state (2-letter, upper case),
    zip (12345 or 12345-6789)."""
    address = {key: str(raw.get(key, "") or "").strip() for key in ADDRESS_FIELDS}
    for key in REQUIRED_ADDRESS_FIELDS:
        if not address[key]:
            raise BillingError(f"Enter the {_FIELD_NAMES[key].lower()}.")
    address["state"] = address["state"].upper()
    if not re.fullmatch(r"[A-Z]{2}", address["state"]):
        raise BillingError("Use the 2-letter state code, e.g. NY.")
    if not _ZIP.match(address["zip"]):
        raise BillingError("Enter a 5-digit ZIP code, e.g. 10031.")
    return address


def zip5(address: dict | None) -> str:
    """The 5-digit ZIP of an address ('' if none)."""
    return str((address or {}).get("zip", ""))[:5]


def format_address(address: dict | None) -> str:
    """Multi-line display form of an address ('' if none)."""
    if not address:
        return ""
    street = ", ".join(p for p in (address.get("line1"), address.get("line2")) if p)
    return f"{address.get('name', '')}\n{street}\n{address.get('city', '')}, {address.get('state', '')} {address.get('zip', '')}"


def luhn_ok(number: str) -> bool:
    digits = [int(d) for d in number]
    checksum = 0
    for i, d in enumerate(reversed(digits)):
        if i % 2:
            d *= 2
            if d > 9:
                d -= 9
        checksum += d
    return checksum % 10 == 0


def card_brand(number: str) -> str:
    if number.startswith("4"):
        return "Visa"
    if re.match(r"^(5[1-5]|2[2-7])", number):
        return "Mastercard"
    if re.match(r"^3[47]", number):
        return "American Express"
    if re.match(r"^6(011|5)", number):
        return "Discover"
    return "Card"


def clean_card(cardholder: str, number: str, exp_month, exp_year, cvv: str, today: date | None = None) -> dict:
    """Validate a card and return the SAFE summary to store or show.

    Returns {"cardholder", "brand", "last4", "exp_month", "exp_year"}.
    The number and CVV are not in the result. Raises BillingError."""
    today = today or date.today()
    cardholder = (cardholder or "").strip()
    number = re.sub(r"[\s-]", "", number or "")
    cvv = (cvv or "").strip()
    if not cardholder:
        raise BillingError("Enter the name on the card.")
    if not number.isdigit() or not 13 <= len(number) <= 19 or not luhn_ok(number):
        raise BillingError("That card number doesn't look right.")
    try:
        month, year = int(exp_month), int(exp_year)
    except (TypeError, ValueError):
        raise BillingError("Enter the expiry month and year.") from None
    if year < 100:
        year += 2000
    if not 1 <= month <= 12:
        raise BillingError("Expiry month must be 1-12.")
    if (year, month) < (today.year, today.month):
        raise BillingError("That card has expired.")
    brand = card_brand(number)
    if not re.fullmatch(r"\d{4}" if brand == "American Express" else r"\d{3}", cvv):
        raise BillingError("Enter the security code (CVV) from the card.")
    return {"cardholder": cardholder, "brand": brand, "last4": number[-4:], "exp_month": month, "exp_year": year}


def card_label(card: dict | None) -> str:
    """e.g. 'Visa •••• 4242 (exp 04/2028)'; '' if no card."""
    if not card:
        return ""
    return f"{card['brand']} •••• {card['last4']} (exp {card['exp_month']:02d}/{card['exp_year']})"
