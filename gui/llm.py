"""Client for a locally hosted LLM served by Ollama (https://ollama.com).

No extra Python packages are needed: this talks to Ollama's HTTP API with the
standard library. Configure it with environment variables:

* ``ANJS_LLM_HOST``  - default ``http://localhost:11434``
* ``ANJS_LLM_MODEL`` - default ``llama3.2:3b`` (``ollama pull llama3.2:3b``)

This module has no Qt dependency, so the future backend can reuse it.
"""
from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from collections.abc import Iterable, Iterator

from .data import Book

HOST = os.environ.get("ANJS_LLM_HOST", "http://localhost:11434").rstrip("/")
MODEL = os.environ.get("ANJS_LLM_MODEL", "llama3.2:3b")


class LLMError(RuntimeError):
    """A problem talking to the local model, worded for the user."""


def system_prompt(catalog: Iterable[Book], purchased: Iterable[Book] = ()) -> str:
    lines = [
        "You are the friendly bookseller for a small online bookstore.",
        "Help the customer decide what to read next. Ask a short follow-up question when their",
        "taste is unclear. Prefer books from the catalog below and give the price when you",
        "recommend one. If you suggest a book that is not in the catalog, say it is not in stock.",
        "Keep replies short: a few sentences or a short list.",
        "",
        "Catalog:",
    ]
    lines += [f"- {b.title} by {b.author} ({b.category}, {b.price_text})" for b in catalog]
    bought = sorted({b.title for b in purchased})
    if bought:
        lines += ["", "The customer has already bought: " + "; ".join(bought) + "."]
    return "\n".join(lines)


def stream_chat(messages: list[dict], model: str = MODEL, host: str = HOST, timeout: float = 120) -> Iterator[str]:
    """Send a chat to Ollama and yield the reply in pieces as they arrive."""
    body = json.dumps({"model": model, "messages": messages, "stream": True}).encode()
    request = urllib.request.Request(f"{host}/api/chat", data=body, headers={"Content-Type": "application/json"})
    try:
        response = urllib.request.urlopen(request, timeout=timeout)
    except urllib.error.HTTPError as exc:
        if exc.code == 404:
            raise LLMError(f"The model “{model}” isn't installed. Run: ollama pull {model}") from exc
        raise LLMError(f"The local model returned an error ({exc.code}).") from exc
    except (urllib.error.URLError, TimeoutError) as exc:
        raise LLMError(f"Can't reach the local model at {host}. Start it with: ollama serve") from exc
    with response:
        for line in response:
            if not line.strip():
                continue
            payload = json.loads(line)
            if "error" in payload:
                raise LLMError(str(payload["error"]))
            piece = payload.get("message", {}).get("content", "")
            if piece:
                yield piece
            if payload.get("done"):
                return
