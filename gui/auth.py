"""Authentication hooks - DEMO STUBS, not real security.

The GUI calls these two functions and nothing else, so wiring up the real
backend later only means replacing the bodies below.

* ``authenticate_password`` accepts any well-formed email with a non-empty
  password. It never checks a real credential.
* ``authenticate_face`` always "recognises" a demo user. Hooking up a real
  camera feed (e.g. ``QtMultimedia.QCamera``) and a face-recognition service
  belongs here.
"""
from __future__ import annotations

from .data import User


def authenticate_password(email: str, password: str) -> User | None:
    email = email.strip()
    if "@" not in email or not password:
        return None
    local = email.split("@", 1)[0]
    return User(name=local.replace(".", " ").title() or "Reader", email=email)


def authenticate_face() -> User | None:
    return User(name="Reader", email="reader@example.com")
