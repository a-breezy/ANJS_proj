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


def register(store: Store, name: str, email: str, password: str) -> User:
    name, email = name.strip(), email.strip().lower()
    if not name:
        raise AuthError("Enter your name.")
    local, _, domain = email.partition("@")
    if not local or "." not in domain:
        raise AuthError("Enter a valid email address.")
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
    "role": "RC"
})
    return User(name=name, email=email)


def authenticate_password(store: Store, email: str, password: str) -> User | None:
    record = store.get_user(email)
    if record is None or not password:
        return None
    if not hmac.compare_digest(record["hash"], _hash(password, bytes.fromhex(record["salt"]))):
        return None
    return User(
    name=record["name"],
    email=record["email"],
    role=record.get("role", "RC")
)


def authenticate_face(store: Store, features: list[float]) -> User | None:
    from .face_login import find_user_by_face
    return find_user_by_face(store, features)
