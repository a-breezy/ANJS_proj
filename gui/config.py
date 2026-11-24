"""Load local settings from the project's ``.env`` file.

Each ``KEY=value`` line becomes an environment variable unless that variable
is already set, so a value exported in the shell still wins. Blank lines and
lines starting with ``#`` are skipped. Copy ``.env.example`` to ``.env`` to
get started.
"""
from __future__ import annotations

import os
from pathlib import Path

PROJECT = Path(__file__).resolve().parents[1]
ENV_FILE = PROJECT / ".env"


def load_env(path: Path = ENV_FILE) -> None:
    if not path.is_file():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip("\"'"))


def project_path(value: str) -> Path:
    """Resolve a path from ``.env``; relative paths start at the project root."""
    path = Path(value).expanduser()
    return path if path.is_absolute() else PROJECT / path


load_env()
