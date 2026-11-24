"""Checkout pricing, in ONE pure function used by both the confirmation page
and the store, so the screen and the saved order can never disagree.

Also :class:`ReceiptOrder`, an Order that carries the checkout fields.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from decimal import ROUND_HALF_UP, Decimal

from .data import Book, Order
from .tax import tax_for_zip

VIP_DISCOUNT = Decimal("0.10")
_CENT = Decimal("0.01")


def money(value) -> Decimal:
    return Decimal(str(value)).quantize(_CENT, rounding=ROUND_HALF_UP)


@dataclass(frozen=True)
class QuoteLine:
    book_id: int
    title: str
    author: str
    price: Decimal


@dataclass(frozen=True)
class Quote:
    lines: tuple[QuoteLine, ...]
    subtotal: Decimal
    discount: Decimal  # amount taken off (>= 0)
    taxable: Decimal  # subtotal - discount
    tax_rate: Decimal | None  # None = ZIP not taxable
    tax_amount: Decimal
    tax_note: str
    grand_total: Decimal


def quote(books: list[Book], role: str, billing_zip: str) -> Quote:
    """Price ``books`` for a user with ``role``, taxed by the billing ZIP.

    The VIP (VC) discount comes off first and tax applies to what is left."""
    lines = tuple(QuoteLine(b.id, b.title, b.author, money(b.price)) for b in books)
    subtotal = sum((line.price for line in lines), Decimal("0.00"))
    discount = money(subtotal * VIP_DISCOUNT) if role == "VC" else Decimal("0.00")
    taxable = subtotal - discount
    tax = tax_for_zip(billing_zip)
    tax_amount = money(taxable * tax.rate) if tax.rate is not None else Decimal("0.00")
    return Quote(lines, subtotal, discount, taxable, tax.rate, tax_amount, tax.note, taxable + tax_amount)


@dataclass(frozen=True)
class ReceiptOrder(Order):
    """An Order plus what was saved at checkout (all None for older orders)."""

    subtotal: float | None = None
    tax_rate: float | None = None
    tax_amount: float | None = None
    tax_note: str = ""
    grand_total: float | None = None
    shipping_address: dict | None = field(default=None, compare=False)
    billing_address: dict | None = field(default=None, compare=False)
    payment_card: dict | None = field(default=None, compare=False)

    @classmethod
    def from_record(cls, record: dict) -> "ReceiptOrder":
        base = Order.from_record(record)
        return cls(
            base.number, base.placed, base.status, base.progress, base.book_ids,
            base.total, base.discount_amount,
            record.get("subtotal"), record.get("tax_rate"), record.get("tax_amount"),
            record.get("tax_note", ""), record.get("grand_total"),
            record.get("shipping_address"), record.get("billing_address"),
            record.get("payment_card"),
        )

    @property
    def total_text(self) -> str:
        """What the customer paid: grand total if saved, else the merchandise total."""
        return f"${self.grand_total if self.grand_total is not None else self.total:.2f}"
