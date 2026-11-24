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

from .data import Book, Order

HOST = os.environ.get("ANJS_LLM_HOST", "http://localhost:11434").rstrip("/")
MODEL = os.environ.get("ANJS_LLM_MODEL", "llama3.2:3b")


class LLMError(RuntimeError):
    """A problem talking to the local model, worded for the user."""

def financial_answer(question, role, financial_summary=None):
    question = question.lower().strip().rstrip("?.!")

    if question not in (
        "what was total revenue",
        "what is total revenue",
        "what is the total revenue",
        "what was the total revenue",
        "what is the bookstore's total revenue",
        "what are the total sales",
        "total revenue",
        "total sales",
    ):
        return None

    if role != "SU":
        return (
            "Bookstore financial information is restricted "
            "to super-users."
        )

    if financial_summary is None:
        return "Financial information is currently unavailable."

    return (
        f"The bookstore's total revenue after discounts is "
        f"${financial_summary['total_sales']:,.2f}."
    )

def system_prompt(
    catalog: Iterable[Book],
    purchased: Iterable[Book] = (),
    role: str = "RC",
    orders: Iterable[Order] = (),
    financial_summary: dict | None = None,
) -> str:
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
    bought = (
        sorted({b.title for b in purchased})
        if role in ("RC", "VC")
        else []
    )
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
            "The user is a visitor.",
            "Provide basic book recommendations using the public catalog only.",
            "Do not recommend books outside the public catalog.",
            "Answer questions about available books, authors, categories, and prices.",
            "Do not provide private customer information or bookstore financial reports.",
            "Suggest creating an account for personalized recommendations and purchase history.",
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
    if role != "SU":
        lines += [
            "",
            "Bookstore-wide financial information is restricted to super-users.",
            "Politely refuse requests for bookstore revenue, total sales,",
            "financial reports, or other customers' private information.",
            "Do not estimate or invent restricted financial figures.",
        ]
    if role == "SU" and financial_summary is not None:
        lines += [
            "",
            "Bookstore financial report:",
            json.dumps(financial_summary, separators=(",", ":")),
            "Total sales represents revenue after discounts.",
            "Use the exact recorded financial figures.",
            "Do not invent or recalculate financial figures.",
            "Do not confuse revenue with profit.",
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
