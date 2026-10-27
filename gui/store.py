"""Local JSON store for accounts and orders - a STAND-IN for the real backend.

Everything is kept in one JSON file (``.data/store.json`` at the repo root by
default, or ``$ANJS_DATA_DIR/store.json``). It starts empty: there are no users
until someone signs up. Swapping in the real database later only means
re-implementing the methods of :class:`Store`.
"""
from __future__ import annotations

import json
import os
from datetime import date
from pathlib import Path
from .data import book_by_id

DEFAULT_DIR = Path(__file__).resolve().parents[1] / ".data"
FIRST_ORDER_NUMBER = 1001


def default_path() -> Path:
    return Path(os.environ.get("ANJS_DATA_DIR", DEFAULT_DIR)) / "store.json"


class Store:
    def __init__(self, path: Path | str | None = None) -> None:
        self.path = Path(path) if path else default_path()
        self._data = self._load()

    def _load(self) -> dict:
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
        except FileNotFoundError:
            data = {}
        data.setdefault("users", {})
        data.setdefault("orders", {})
        data.setdefault("next_order", FIRST_ORDER_NUMBER)
        return data

    def _save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.path.with_suffix(".tmp")
        tmp.write_text(json.dumps(self._data, indent=2), encoding="utf-8")
        tmp.replace(self.path)

    # --- users ------------------------------------------------------------
    def get_user(self, email: str) -> dict | None:
        return self._data["users"].get(email.strip().lower())

    def add_user(self, record: dict) -> None:
        email = record["email"].strip().lower()

        if email in self._data["users"]:
            raise KeyError(email)

        self._data["users"][email] = {
            **record,
            "email": email,
            "role": "RC",
            "shipping_address": "",
            "purchase_count": 0,
            "total_spent": 0.0,
        }

        self._save()

    # --- orders -----------------------------------------------------------
    def orders_for(self, email: str) -> list[dict]:
        return list(self._data["orders"].get(email.strip().lower(), []))

    def add_order(self, email: str, book_ids: list[int]) -> dict:
        order_total = 0.0
        for book_id in book_ids:
            book = book_by_id(book_id)
            if book is not None:
                order_total += book.price


        user = self.get_user(email)
        discount_rate = 0.10 if user and user["role"] == "VC" else 0.0
        discount_amount = round(order_total * discount_rate, 2)
        final_total = round(order_total - discount_amount, 2)

        order = {
            "number": self._data["next_order"],
            "placed": date.today().isoformat(),
            "status": "processing",
            "progress": 0.15,
            "book_ids": list(book_ids),
            "total": final_total,
            "discount_amount": discount_amount,
        }
        self._data["next_order"] += 1
        self._data["orders"].setdefault(email.strip().lower(), []).append(order)
        user = self.get_user(email)
        if user is not None:
            user["purchase_count"] = user.get("purchase_count", 0) + 1
            user["total_spent"] = round(user.get("total_spent", 0.0) + final_total, 2)
            if user["role"] == "RC" and (
                user["purchase_count"] > 3 or user["total_spent"] > 200
            ):
                user["role"] = "VC"
        self._save()
        return order
