"""Local JSON store for accounts and orders - a STAND-IN for the real backend.

Everything is kept in one JSON file (``.data/store.json`` at the repo root by
default, or ``$ANJS_DATA_DIR/store.json``). It starts empty: there are no users
until someone signs up. Swapping in the real database later only means
re-implementing the methods of :class:`Store`.
"""
from __future__ import annotations

import copy
import math
import json
import os
from typing import Callable
from datetime import date
from pathlib import Path
from .data import book_by_id

DEFAULT_DIR = Path(__file__).resolve().parents[1] / ".data"
FIRST_ORDER_NUMBER = 1001
VALID_ROLES = {"RC", "VC", "SU"}  # "VS" (visitor) is never stored


def default_path() -> Path:
    return Path(os.environ.get("ANJS_DATA_DIR", DEFAULT_DIR)) / "store.json"


class Store:
    """JSON-file store. Every public method re-reads the file if another
    Store object (or script) changed it, and every write goes through
    :meth:`update`, so two Store objects never overwrite each other's data."""

    def __init__(self, path: Path | str | None = None) -> None:
        self.path = Path(path) if path else default_path()
        self._data = self._load()
        self._stamp = self._file_stamp()

    def _file_stamp(self) -> tuple[int, int] | None:
        try:
            st = self.path.stat()
        except FileNotFoundError:
            return None
        return (st.st_mtime_ns, st.st_size)

    def _load(self) -> dict:
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
        except FileNotFoundError:
            data = {}
        data.setdefault("users", {})
        data.setdefault("orders", {})
        data.setdefault("next_order", FIRST_ORDER_NUMBER)
        data.setdefault("reviews", {})
        return data

    def _reload_if_changed(self) -> None:
        stamp = self._file_stamp()
        if stamp != self._stamp:
            self._data = self._load()
            self._stamp = stamp

    def _save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.path.with_suffix(".tmp")
        tmp.write_text(json.dumps(self._data, indent=2), encoding="utf-8")
        tmp.replace(self.path)  # atomic on POSIX and Windows
        self._stamp = self._file_stamp()

    def update(self, fn: Callable[[dict], object]):
        """Reload, apply ``fn(data)``, save, and return ``fn``'s result.

        If ``fn`` raises, nothing is saved."""
        self._reload_if_changed()
        try:
            result = fn(self._data)
        except BaseException:
            self._data = self._load()  # drop any half-applied changes
            raise
        self._save()
        return result

    # --- users ------------------------------------------------------------
    def get_user(self, email: str) -> dict | None:
        """A copy of the account record (use update_user to change it)."""
        self._reload_if_changed()
        record = self._data["users"].get(email.strip().lower())
        return copy.deepcopy(record) if record is not None else None

    def list_users(self) -> list[dict]:
        self._reload_if_changed()
        return copy.deepcopy(list(self._data["users"].values()))

    def update_user(self, email: str, fn: Callable[[dict], object]):
        """Apply ``fn(record)`` to an existing account and save. Returns
        ``fn``'s result; raises ValueError if the account does not exist."""
        key = email.strip().lower()

        def apply(data: dict):
            record = data["users"].get(key)
            if record is None:
                raise ValueError("Account not found.")
            return fn(record)

        return self.update(apply)

    def add_user(self, record: dict) -> None:
        email = record["email"].strip().lower()
        role = record.get("role", "RC")
        if role not in VALID_ROLES:
            raise ValueError(f"Invalid role: {role!r}")

        def add(data: dict) -> None:
            if email in data["users"]:
                raise KeyError(email)
            data["users"][email] = {
                "shipping_address": "",
                "purchase_count": 0,
                "total_spent": 0.0,
                **record,
                "email": email,
                "role": role,
            }

        self.update(add)

    def set_role(self, email: str, role: str) -> None:
        """Change an existing account's role (RC, VC or SU) and save."""
        if role not in VALID_ROLES:
            raise ValueError(f"Invalid role: {role!r}")
        self.update_user(email, lambda record: record.__setitem__("role", role))

    def add_face_template(self, email: str, features: list[float]) -> None:
        """Save one face scan for an existing account."""
        if len(features) != 128 or not all(math.isfinite(x) for x in features):
            raise ValueError("Invalid face features.")

        def add(record: dict) -> None:
            templates = record.setdefault("face_templates", [])
            if len(templates) >= 4:
                raise ValueError("This account already has 4 face scans.")
            templates.append([float(x) for x in features])

        self.update_user(email, add)

    def remove_face_templates(self, email: str) -> None:
        """Remove saved face scans from an account."""
        self.update_user(email, lambda record: record.pop("face_templates", None))

    def enrolled_face_accounts(self) -> list[dict]:
        """Find accounts that have face scans saved."""
        return [
            {
                "name": record["name"],
                "email": record["email"],
                "role": record.get("role", "RC"),
                "face_templates": record["face_templates"],
            }
            for record in self.list_users()
            if record.get("face_templates")
        ]

    # --- reviews and taboo words -------------------------------------------
    def get_reviews(self, book_id: int) -> list[dict]:
        self._reload_if_changed()
        return copy.deepcopy(self._data["reviews"].get(str(book_id), []))

    def review_book_ids(self) -> list[int]:
        """Ids of every book that has at least one review."""
        self._reload_if_changed()
        return [int(k) for k, v in self._data["reviews"].items() if v]

    def add_review(self, book_id: int, entry: dict) -> None:
        self.update(
            lambda data: data["reviews"].setdefault(str(book_id), []).append(entry)
        )

    def get_taboo_words(self) -> list[str] | None:
        """The taboo list, or None if it has never been initialised."""
        self._reload_if_changed()
        words = self._data.get("taboo_words")
        return None if words is None else list(words)

    def set_taboo_words(self, words: list[str]) -> None:
        self.update(lambda data: data.__setitem__("taboo_words", list(words)))

    # --- orders -----------------------------------------------------------
    def orders_for(self, email: str) -> list[dict]:
        self._reload_if_changed()
        return copy.deepcopy(self._data["orders"].get(email.strip().lower(), []))

    def financial_summary(self) -> dict:
        self._reload_if_changed()
        orders = [
            order
            for customer_orders in self._data["orders"].values()
            for order in customer_orders
        ]

        return {
            "total_orders": len(orders),
            "total_sales": round(
                sum(o.get("total", 0.0) for o in orders), 2
            ),
            "total_discounts": round(
                sum(o.get("discount_amount", 0.0) for o in orders), 2
            ),
            "books_sold": sum(
                len(o.get("book_ids", [])) for o in orders
            ),
        }

    def add_order(self, email: str, book_ids: list[int]) -> dict:
        order_total = 0.0
        for book_id in book_ids:
            book = book_by_id(book_id)
            if book is not None:
                order_total += book.price

        key = email.strip().lower()

        def place(data: dict) -> dict:
            user = data["users"].get(key)
            discount_rate = 0.10 if user and user["role"] == "VC" else 0.0
            discount_amount = round(order_total * discount_rate, 2)
            final_total = round(order_total - discount_amount, 2)

            order = {
                "number": data["next_order"],
                "placed": date.today().isoformat(),
                "status": "processing",
                "progress": 0.15,
                "book_ids": list(book_ids),
                "total": final_total,
                "discount_amount": discount_amount,
            }
            data["next_order"] += 1
            data["orders"].setdefault(key, []).append(order)
            if user is not None:
                user["purchase_count"] = user.get("purchase_count", 0) + 1
                user["total_spent"] = round(user.get("total_spent", 0.0) + final_total, 2)
                # A demoted VC must earn VIP status again: only count activity
                # since the demotion (baseline is 0 for never-demoted users).
                baseline = user.get("promotion_baseline", {})
                purchases_since = user["purchase_count"] - baseline.get("purchases", 0)
                spent_since = user["total_spent"] - baseline.get("spent", 0.0)
                if user["role"] == "RC" and (purchases_since > 3 or spent_since > 200):
                    user["role"] = "VC"
            return dict(order)

        return self.update(place)
