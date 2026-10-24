"""Local JSON store for accounts and orders - a STAND-IN for the real backend.

Everything is kept in one JSON file (``.data/store.json`` at the repo root by
default, or ``$ANJS_DATA_DIR/store.json``). It starts empty: there are no users
until someone signs up. Swapping in the real database later only means
re-implementing the methods of :class:`Store`.
"""
from __future__ import annotations

import math
import json
import os
from datetime import date
from pathlib import Path

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
        self._data["users"][email] = {**record, "email": email}
        self._save()

    def add_face_template(self, email: str, features: list[float]) -> None:
        """Save one face scan for an existing account."""
        record = self.get_user(email)

        if record is None:
            raise ValueError("Account not found.")

        if len(features) != 128 or not all(math.isfinite(x) for x in features):
            raise ValueError("Invalid face features.")

        templates = record.setdefault("face_templates", [])

        if len(templates) >= 4:
            raise ValueError("This account already has 4 face scans.")

        templates.append([float(x) for x in features])
        self._save()

    def remove_face_templates(self, email: str) -> None:
        """Remove saved face scans from an account."""
        record = self.get_user(email)

        if record is None:
            raise ValueError("Account not found.")

        record.pop("face_templates", None)
        self._save()

    """Finds accounts that have enrolled faces"""
    def enrolled_face_accounts(self) -> list[dict]: 
        """Find accounts that have face scans saved."""
        return [
            {
                "name": record["name"],
                "email": record["email"],
                "face_templates": record["face_templates"],
            }
            for record in self._data["users"].values()
            if record.get("face_templates")
        ]

    # --- orders -----------------------------------------------------------
    def orders_for(self, email: str) -> list[dict]:
        return list(self._data["orders"].get(email.strip().lower(), []))

    def add_order(self, email: str, book_ids: list[int]) -> dict:
        order = {
            "number": self._data["next_order"],
            "placed": date.today().isoformat(),
            "status": "processing",
            "progress": 0.15,
            "book_ids": list(book_ids),
        }
        self._data["next_order"] += 1
        self._data["orders"].setdefault(email.strip().lower(), []).append(order)
        self._save()
        return order
