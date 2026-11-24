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

from . import data
from .data import Book, Order

HOST = os.environ.get("ANJS_LLM_HOST", "http://localhost:11434").rstrip("/")
MODEL = os.environ.get("ANJS_LLM_MODEL", "llama3.2:3b")
MAX_PROMPT_BOOKS = 40  # catalog lines per prompt, so it doesn't grow with the catalog
MAX_HISTORY_MESSAGES = 12  # chat messages sent along with the system prompt


class LLMError(RuntimeError):
    """A problem talking to the local model, worded for the user."""


def _prompt_books(catalog: Iterable[Book], purchased: list[Book], query: str) -> list[Book]:
    """Up to MAX_PROMPT_BOOKS: matches for the query, then purchases, then bestsellers."""
    books = list(catalog)
    by_id = {b.id: b for b in books}
    chosen: dict[int, Book] = {}

    def take(candidates: Iterable[Book]) -> None:
        for book in candidates:
            if len(chosen) >= MAX_PROMPT_BOOKS:
                return
            if book.id in by_id:
                chosen.setdefault(book.id, by_id[book.id])

    if query.strip():
        try:
            take(data.search(query))
        except Exception:  # noqa: BLE001 - a search hiccup must not break chat
            pass
    take(purchased)
    take(sorted(books, key=lambda b: b.downloads, reverse=True))
    return list(chosen.values())


def system_prompt(
    catalog: Iterable[Book],
    purchased: Iterable[Book] = (),
    role: str = "RC",
    orders: Iterable[Order] = (),
    financial_summary: dict | None = None,
    query: str = "",
) -> str:
    """Build the system prompt. ``query`` (the latest user message) picks which catalog books to list."""
    purchased = list(purchased)
    lines = [
        "You are the friendly bookseller for a small online bookstore.",
        "Help the customer decide what to read next. Ask a short follow-up question when their",
        "taste is unclear. Prefer books from the catalog below and give the price when you",
        "recommend one. If you suggest a book that is not in the catalog, say it is not in stock.",
        "Keep replies short: a few sentences or a short list.",
        "",
        "Catalog:",
    ]
    lines += [f"- {b.title} by {b.author} ({b.category}, {b.price_text})" for b in _prompt_books(catalog, purchased, query)]
    bought = sorted({b.title for b in purchased})
    if bought:
        lines += ["", "The customer has already bought: " + "; ".join(bought) + "."]

    if role == "RC":
        lines += [
            "",
            "The customer is a registered customer.",
            "Help with reading recommendations and purchase history.",
            "Only discuss billing information provided in the conversation.",
        ]
    elif role == "VC":
        lines += [
            "",
            "The customer is a VIP customer.",
            "Provide personalized reading recommendations and purchase history.",
            "Explain VIP benefits when relevant.",
            "Explain the VIP customer's 10% purchase discount.",
"Recommend books based on previous purchases.",
"Help the customer understand their accumulated savings.",
"Suggest new books that complement their reading history.",
            "Only discuss billing information provided in the conversation.",
        ]
    elif role == "SU":
        lines += [
            "",
            "The user is a super-user.",
            "Help analyze available bookstore financial reports.",
            "Provide insights and suggestions for business growth.",
            "Do not invent financial figures.",
        ]
    elif role == "VS":
        lines += [
            "",
            "Visitors cannot use the AI assistant.",
        ]

    if role in ("RC", "VC"):
        order_list = list(orders)
        total_spent = sum(order.total for order in order_list)
        total_saved = sum(order.discount_amount for order in order_list)

        lines += [
            "",
            "Customer billing information:",
            f"Total orders: {len(order_list)}",
            f"Original total before discounts: ${total_spent + total_saved:.2f}",
            f"Total spent after discounts: ${total_spent:.2f}",
            "The total spent already includes all applied discounts.",
            "Do not subtract discounts from the total spent again.",
            f"Total discounts: ${total_saved:.2f}",
            "Only use the customer's provided billing data.",
            "Do not invent billing information.",
            "Use the exact billing totals provided above.",
            "Do not recalculate or invent additional savings.",
            "VIP discounts are calculated from the original price before discounts.",
            "Never assume future purchases or future savings.",
            "Use only catalog prices when recommending available books.",
        ]

        for order in order_list:
            lines.append(
                f"Order #{order.number}: "
                f"Date: {order.placed}, "
                f"Total: ${order.total:.2f}, "
                f"Discount: ${order.discount_amount:.2f}, "
                f"Status: {order.status}"
            )
    if role == "SU" and financial_summary is not None:
        lines += [
            "",
            "Bookstore financial report:",
            f"Total orders: {financial_summary['total_orders']}",
            f"Total sales: ${financial_summary['total_sales']:.2f}",
            f"Total discounts: ${financial_summary['total_discounts']:.2f}",
            f"Books sold: {financial_summary['books_sold']}",
            "Use these recorded order figures for financial analysis.",
            "Do not confuse sales with profit.",
            "Suggest business growth strategies based on available data.",
        ]
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
