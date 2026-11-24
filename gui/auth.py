"""Authentication hooks backed by the local :mod:`gui.store`.

The GUI calls these functions and nothing else, so wiring up the real backend
later only means replacing the bodies below.

* ``register`` creates an account. Passwords are salted and hashed with
  PBKDF2, but the store is a local JSON file, so this is still a prototype,
  not production security.
* ``authenticate_password`` only accepts an email/password pair that was
  registered first. There are no accounts until someone signs up.
* ``authenticate_face`` matches a face feature vector to an enrolled account.
  The actual webcam is handled by the FaceScanDialog worker.
"""
from __future__ import annotations

import hashlib
import hmac
import os

from .data import User
from .store import Store

MIN_PASSWORD = 8
_ITERATIONS = 200_000


class AuthError(ValueError):
    """Raised by ``register`` with a message that can be shown to the user."""


def _hash(password: str, salt: bytes) -> str:
    return hashlib.pbkdf2_hmac("sha256", password.encode(), salt, _ITERATIONS).hex()


def _check_email(email: str) -> None:
    local, _, domain = email.partition("@")
    if not local or "." not in domain:
        raise AuthError("Enter a valid email address.")


def _verified_record(store: Store, email: str, password: str) -> dict:
    record = store.get_user(email)
    if record is None or not password or not hmac.compare_digest(
        record["hash"], _hash(password, bytes.fromhex(record["salt"]))
    ):
        raise AuthError("That password isn't right.")
    return record


def register(store: Store, name: str, email: str, password: str) -> User:
    name, email = name.strip(), email.strip().lower()
    if not name:
        raise AuthError("Enter your name.")
    _check_email(email)
    if len(password) < MIN_PASSWORD:
        raise AuthError(f"Use at least {MIN_PASSWORD} characters for your password.")
    if store.get_user(email):
        raise AuthError("An account with that email already exists. Sign in instead.")
    salt = os.urandom(16)
    store.add_user({
        "name": name,
        "email": email,
        "salt": salt.hex(),
        "hash": _hash(password, salt),
        "role": "RC",
    })
    return User(name=name, email=email)


def change_email(store: Store, email: str, password: str, new_email: str) -> User:
    """Move the account to ``new_email`` (needs the current password); orders and reviews follow."""
    record = _verified_record(store, email, password)
    new_email = new_email.strip().lower()
    _check_email(new_email)
    if new_email != record["email"] and store.get_user(new_email):
        raise AuthError("That email is already used by another account.")
    try:
        store.change_email(record["email"], new_email)
    except ValueError as exc:
        raise AuthError("That email is already used by another account.") from exc
    return User(name=record["name"], email=new_email, role=record.get("role", "RC"))


def change_password(store: Store, email: str, current: str, new: str) -> None:
    """Set a new password after checking the current one (new salt every time)."""
    record = _verified_record(store, email, current)
    if len(new) < MIN_PASSWORD:
        raise AuthError(f"Use at least {MIN_PASSWORD} characters for your new password.")
    salt = os.urandom(16)

    def apply(rec: dict) -> None:
        rec["salt"] = salt.hex()
        rec["hash"] = _hash(new, salt)

    store.update_user(record["email"], apply)


def authenticate_password(store: Store, email: str, password: str) -> User | None:
    record = store.get_user(email)
    if record is None or not password:
        return None
    if not hmac.compare_digest(record["hash"], _hash(password, bytes.fromhex(record["salt"]))):
        return None
    # Only reveal suspension to someone who proved they know the password.
    if record.get("suspended", False):
        raise AuthError("Account suspended. Contact a Super-User (SU) to reactivate.")
    return User(
        name=record["name"],
        email=record["email"],
        role=record.get("role", "RC"),
    )


def authenticate_face(store: Store, features: list[float]) -> User | None:
    from .face_login import find_user_by_face
    user = find_user_by_face(store, features)
    if user is not None:
        record = store.get_user(user.email)
        if record and record.get("suspended", False):
            raise AuthError("Account suspended. Contact a Super-User (SU) to reactivate.")
    return user
