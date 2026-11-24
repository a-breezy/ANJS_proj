"""Cart actions for the Ask chat.

The language model only produces text, so it cannot change the cart by itself.
This module gives the chat two ways to do it, and in both the *app* makes the
change and reports it, never the model:

1. **Explicit requests** such as "add The Quiet Orchard to my cart" are
   recognised in the user's own message and handled without calling the model.
2. **Model requests**: the system prompt (see :mod:`gui.llm`) tells the model to
   finish a reply with a line like ``[[add_to_cart: 84]]`` (a catalog id or a
   title). The chat strips that line from what the customer sees and carries it
   out.

Nothing here depends on Qt, so it is easy to test.
"""
from __future__ import annotations

import re
from collections.abc import Callable, Iterable
from dataclasses import dataclass, field

from . import data
from .data import Book

MAX_ADDS_PER_REPLY = 5

_MARKER = re.compile(r"\[\[\s*add_to_cart\s*:\s*([^\]\n]{1,120}?)\s*\]\]", re.IGNORECASE)
_OPEN_MARKER = re.compile(r"\[\[[^\]]*$")  # a marker still being streamed

# "add X to my cart", "put X in the basket", "please add X to cart"
_ADD = re.compile(
    r"\b(?:add|put|place|throw|drop|stick)\s+(?P<what>.+?)\s+"
    r"(?:to|in|into|on)\s+(?:(?:my|the|your)\s+)?(?:shopping\s+)?(?:cart|basket)\b",
    re.IGNORECASE,
)
_PRONOUNS = {
    "it", "this", "that", "these", "those", "them", "one", "both", "all", "everything",
    "the first", "the second", "the third", "the last", "the first one", "the second one",
    "the third one", "the last one", "that one", "this one", "the book", "that book", "this book",
}
# Phrases a model uses when it claims it changed the cart.
_CART_CLAIM = re.compile(
    r"\b(?:added|adding|i'll add|i will add|let me add|i can add|i've put|putting|placed)\b[^.!?\n]{0,80}\b(?:cart|basket)\b",
    re.IGNORECASE,
)

NOT_ADDED_WARNING = (
    "⚠️ **Nothing was added to your cart.** I can add a book when you name it, "
    "for example: “add *The Quiet Orchard* to my cart”."
)


# --------------------------------------------------------------------------
# Markers in model replies
# --------------------------------------------------------------------------
def strip_markers(text: str, streaming: bool = False) -> str:
    """``text`` without ``[[add_to_cart: …]]`` lines. While streaming, also hide a half-written one."""
    text = _MARKER.sub("", text)
    if streaming:
        text = _OPEN_MARKER.sub("", text)
    return text.rstrip()


def extract_add_requests(text: str) -> list[str]:
    """The ids or titles the model asked to add, in order, without duplicates."""
    seen: list[str] = []
    for match in _MARKER.finditer(text):
        arg = match.group(1).strip().strip("\"'“”")
        if arg and arg.lower() not in (s.lower() for s in seen):
            seen.append(arg)
    return seen[:MAX_ADDS_PER_REPLY]


def claims_cart_change(text: str) -> bool:
    return bool(_CART_CLAIM.search(text))


# --------------------------------------------------------------------------
# Finding the book someone means
# --------------------------------------------------------------------------
_PUNCT = re.compile(r"[^\w\s]", re.UNICODE)
_FILLER = re.compile(r"^(?:(?:a|an|the)\s+)?(?:(?:copy|copies)\s+of\s+)?(?:(?:a|an|the)\s+)?(?:book\s+)?(?:called\s+|titled\s+|named\s+)?", re.IGNORECASE)
_LEADING_ARTICLE = re.compile(r"^(?:the|a|an)\s+")


def _norm(text: str) -> str:
    text = _PUNCT.sub(" ", text.lower())
    return _LEADING_ARTICLE.sub("", " ".join(text.split()))


def _main_title(title: str) -> str:
    """'Frankenstein; Or, The Modern Prometheus' -> 'frankenstein'."""
    return _norm(re.split(r";|:| or, | or ", title, maxsplit=1, flags=re.IGNORECASE)[0])


def _lookup(query: str, catalog: list[Book], search: Callable[[str], list[Book]]) -> tuple[int, list[Book]]:
    """(quality, books): 3 = exact title, 2 = title contained in the words, 1 = search hit, 0 = none."""
    cleaned = _FILLER.sub("", query.strip().strip("\"'“”.!?"))
    q = _norm(cleaned)
    if len(q) < 2:
        return 0, []

    exact = [b for b in catalog if q in (_norm(b.title), _main_title(b.title))]
    if exact:
        return 3, exact[:1]

    contained = [
        b for b in catalog
        if (len(q) >= 4 and q in _norm(b.title))
        or (len(_main_title(b.title)) >= 4 and _main_title(b.title) in q)
    ]
    if contained:
        return 2, contained[:3]

    ids = {b.id for b in catalog}
    try:
        hits = [b for b in search(cleaned) if b.id in ids]
    except Exception:  # noqa: BLE001 - a search hiccup must not break chat
        hits = []
    return (1, hits[:3]) if hits else (0, [])


def find_books(query: str, books: Iterable[Book] | None = None, search: Callable[[str], list[Book]] | None = None) -> list[Book]:
    """Books that could be what ``query`` names: one means a clear match, several mean ambiguous."""
    catalog = list(data.BOOKS if books is None else books)
    return _lookup(query, catalog, data.search if search is None else search)[1]


def resolve_marker_arg(arg: str, books: Iterable[Book] | None = None) -> list[Book]:
    """A model-supplied id ('84') or title; like :func:`find_books`."""
    arg = arg.strip()
    if arg.isdigit():
        book = data.book_by_id(int(arg))
        return [book] if book is not None else []
    return find_books(arg, books)


# --------------------------------------------------------------------------
# Explicit requests typed by the user
# --------------------------------------------------------------------------
@dataclass
class AddRequest:
    """One thing the user asked to add: what they typed and the books it could mean."""

    text: str
    books: list[Book] = field(default_factory=list)


def explicit_add_request(message: str, books: Iterable[Book] | None = None) -> list[AddRequest] | None:
    """Parse "add <title(s)> to my cart"; ``None`` if the message isn't that, or is vague ("add it")."""
    match = _ADD.search(message)
    if match is None:
        return None
    what = match.group("what").strip().strip("\"'“”,. ")
    if not what or what.lower() in _PRONOUNS:
        return None
    catalog = list(data.BOOKS if books is None else books)

    whole = find_books(what, catalog)
    if len(whole) == 1:
        return [AddRequest(what, whole)]

    segments = _split_titles(what, catalog)
    if segments is not None:
        seen: set[int] = set()
        requests: list[AddRequest] = []
        for text, found in segments:
            if len(found) == 1 and found[0].id in seen:
                continue
            seen.update(b.id for b in found if len(found) == 1)
            requests.append(AddRequest(text, found))
        return requests[:MAX_ADDS_PER_REPLY]
    return [AddRequest(what, whole)]


_WEIGHT = {0: 0, 1: 1, 2: 1, 3: 10}  # an exact title is worth far more than a partial hit


def _split_titles(what: str, catalog: list[Book]) -> list[tuple[str, list[Book]]] | None:
    """Split "A, B and C" into titles, even when a title contains "and" ("Pride and Prejudice").

    Tries every way of cutting at the commas, "&" and "and" words and keeps the one whose
    pieces are the best title matches (an exact title beats a partial one).
    """
    pieces = re.split(r"(\s*(?:,|&|\band\b)\s*)", what)
    n = len(pieces) // 2 + 1
    if n < 2 or n > 8:
        return None
    search = data.search

    cache: dict[tuple[int, int], tuple[int, list[Book]]] = {}

    def score(i: int, j: int) -> tuple[int, list[Book], str]:
        text = "".join(pieces[2 * i : 2 * j + 1]).strip().strip("\"'“”,. ")
        if (i, j) not in cache:
            cache[(i, j)] = _lookup(text, catalog, search)
        quality, found = cache[(i, j)]
        return (_WEIGHT[quality] if len(found) == 1 else 0), found, text

    best: list[tuple[int, int] | None] = [None] * (n + 1)  # (total score, start of last piece)
    best[0] = (0, 0)
    for end in range(1, n + 1):
        for start in range(end):
            if best[start] is None:
                continue
            quality, _found, _text = score(start, end - 1)
            if quality == 0:
                continue
            total = best[start][0] + quality
            if best[end] is None or total > best[end][0]:
                best[end] = (total, start)
    if best[n] is None:
        return None
    out: list[tuple[str, list[Book]]] = []
    end = n
    while end > 0:
        start = best[end][1]
        _quality, found, text = score(start, end - 1)
        out.append((text, found))
        end = start
    return out[::-1]


# --------------------------------------------------------------------------
# Doing it
# --------------------------------------------------------------------------
def _in_cart(session, book: Book) -> bool:
    return any(item.id == book.id for item in session.cart)


def apply_books(session, books: Iterable[Book]) -> tuple[list[str], int]:
    """Add each book that isn't already in the cart. Returns (message lines, number added)."""
    lines: list[str] = []
    added = 0
    for book in books:
        if _in_cart(session, book):
            lines.append(f"**{book.title}** is already in your cart.")
        else:
            session.add_to_cart(book)
            added += 1
            lines.append(f"✓ Added **{book.title}** ({book.price_text}) to your cart.")
    return lines, added


def cart_summary(session) -> str:
    count = len(session.cart)
    noun = "book" if count == 1 else "books"
    return f"Your cart has {count} {noun}, total ${session.cart_total:.2f}. Open the Cart tab to check out."


def _not_found_line(request: AddRequest) -> str:
    if not request.books:
        return f"I couldn't find a book called “{request.text}” in the store, so I didn't add anything for it."
    options = "; ".join(f"*{b.title}* by {b.author}" for b in request.books)
    return f"“{request.text}” could mean more than one book: {options}. Tell me which one and I'll add it."


def run_requests(session, requests: list[AddRequest]) -> tuple[str, int]:
    """Carry out explicit requests. Returns (reply text for the chat, number of books added)."""
    lines: list[str] = []
    to_add: list[Book] = []
    for request in requests:
        if len(request.books) == 1:
            if request.books[0].id not in {b.id for b in to_add}:
                to_add.append(request.books[0])
        else:
            lines.append(_not_found_line(request))
    added_lines, added = apply_books(session, to_add)
    lines = added_lines + lines
    if session.cart and (added or added_lines):
        lines.append(cart_summary(session))
    return "\n\n".join(lines), added


def run_model_markers(session, args: list[str]) -> tuple[list[str], int]:
    """Carry out ``[[add_to_cart: …]]`` lines from the model. Returns (message lines, number added)."""
    lines: list[str] = []
    to_add: list[Book] = []
    for arg in args:
        found = resolve_marker_arg(arg)
        if len(found) == 1:
            if found[0].id not in {b.id for b in to_add}:
                to_add.append(found[0])
        else:
            lines.append(_not_found_line(AddRequest(arg, found)))
    added_lines, added = apply_books(session, to_add)
    out = added_lines + lines
    if added_lines:
        out.append(cart_summary(session))
    return out, added
