"""Look up a book's description and star rating on Open Library.

Open Library (https://openlibrary.org/developers/api) needs no API key. Each
lookup makes two or three requests: a search that returns the work and its
ratings (twice if the first finds no matching author), then the work record
for the description. This is meant to run once while
building the catalogue, not every time a page opens.

This module has no Qt dependency, so the future backend can reuse it.
"""
from __future__ import annotations

import difflib
import json
import re
import ssl
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass

HOST = "https://openlibrary.org"
# Open Library asks API clients to identify themselves.
USER_AGENT = "ANJS-bookstore/0.1 (CSC 322 class project)"
SEARCH_FIELDS = "key,title,author_name,edition_count,ratings_average,ratings_count,first_publish_year"
SAME_NAME = 0.75  # how alike two spellings of a name must be (0-1)


def _ssl_context() -> ssl.SSLContext:
    # python.org builds on macOS don't use the system certificates; certifi's
    # bundle (installed alongside requests/ultralytics) fixes that when present.
    try:
        import certifi
    except ImportError:
        return ssl.create_default_context()
    return ssl.create_default_context(cafile=certifi.where())


class OpenLibraryError(RuntimeError):
    """Open Library could not be reached or sent back something unexpected."""


@dataclass(frozen=True)
class BookInfo:
    work_key: str  # e.g. "/works/OL66554W"
    description: str
    rating: float | None  # average out of 5, or None when nobody has rated it
    rating_count: int
    year: int | None = None  # first publication year


def _get(path: str, params: dict | None = None, timeout: float = 20) -> dict:
    url = f"{HOST}{path}"
    if params:
        url += "?" + urllib.parse.urlencode(params)
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(request, timeout=timeout, context=_ssl_context()) as response:
            return json.load(response)
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
        raise OpenLibraryError(f"Open Library request failed: {exc}") from exc


def _description_text(value) -> str:
    """Work descriptions are either a plain string or {"type": ..., "value": "..."}."""
    if isinstance(value, dict):
        value = value.get("value", "")
    if not isinstance(value, str):
        return ""
    # Descriptions are Markdown copied from Wikipedia and elsewhere, often ending
    # with a "----------" or "---" block of links.
    value = re.split(r"\n\s*-{3,}\s*(\n|$)", value)[0]
    value = re.sub(r"\[\d+\]\([^)]*\)", "", value)  # footnote links: [1](url)
    value = re.sub(r"\\\[[^\]]*\\\]", "", value)  # escaped brackets: \[2\], \[prɪˈstoʊ...\]
    value = re.sub(r";?\s*IPA:\s*(?=\))", "", value)
    value = re.sub(r"\\([\[\]()*_#])", r"\1", value)  # other Markdown escapes
    value = re.sub(r"\[([^\]]+)\]\([^)]*\)", r"\1", value)  # [text](url) -> text
    value = re.sub(r"(?m)^\s*\[\d+\]:\s*\S+.*$", "", value)  # reference definitions: [1]: http://...
    value = re.sub(r"\s*[-–—]?\s*\[wikipedia\]\[\d+\]", "", value, flags=re.IGNORECASE)
    value = re.sub(r"\[([^\]]+)\]\[\d+\]", r"\1", value)  # [text][1] -> text
    value = re.sub(r"\[\d+\]", "", value)  # bare footnotes: [2]
    value = re.sub(r"\*+([^*]+)\*+", r"\1", value)
    value = re.sub(r"^\s*(source|from)\s*:?\s*wikipedia\s*:?\s*", "", value, flags=re.IGNORECASE)
    value = value.strip()
    return value if _looks_english(value) else ""


_ENGLISH = {"the", "and", "of", "to", "a", "in", "is", "that", "his", "her", "with", "for", "by", "was", "as", "an"}


def _looks_english(text: str) -> bool:
    """Some works only have a Spanish, French... description; skip those."""
    words = re.findall(r"[a-z]+", text.lower())
    if len(words) < 8:  # too short to judge
        return True
    return sum(w in _ENGLISH for w in words) / len(words) > 0.12


def _same_author(wanted: str, names: list[str]) -> bool:
    """Loose author match, so 'Dostoyevsky' finds 'Dostoevsky' and 'Fiódor Dostoievski'."""
    wanted_words = [w for w in re.findall(r"\w+", wanted.lower()) if len(w) > 2]
    for name in names:
        for word in re.findall(r"\w+", name.lower()):
            if len(word) > 2 and any(difflib.SequenceMatcher(None, word, w).ratio() > SAME_NAME for w in wanted_words):
                return True
    return False


def _search(query: str, limit: int) -> list[dict]:
    # Sorting by edition count puts the well-known work ahead of single study
    # guides and reprints that happen to share the title.
    params = {"q": query, "sort": "editions", "limit": limit, "fields": SEARCH_FIELDS}
    return _get("/search.json", params).get("docs", [])


def _same_title(wanted: str, found: str) -> bool:
    """'Don Quixote' matches 'Don Quijote de la Mancha'; 'Herland' doesn't match 'The Yellow Wallpaper'."""
    wanted, found = (re.sub(r"^(the|a|an) ", "", t.lower().strip()) for t in (wanted, found))
    return wanted in found or difflib.SequenceMatcher(None, wanted, found[: len(wanted) + 2]).ratio() > SAME_NAME


def lookup(title: str, author: str = "") -> BookInfo | None:
    """Best Open Library match for a title (and author), or None if there is none.

    Searches the title alone (which also matches translated and original-language
    titles) and keeps the most-published work whose author roughly matches. If no
    author matches, searches title and author together, still requiring the
    author or the title to match so an unrelated popular book can't slip in.
    """
    # "Dream of the Red Chamber (Book I)" -> "Dream of the Red Chamber"
    title = re.sub(r"\s*\(.*?\)", "", title).strip()
    author = re.sub(r"\s*\(.*?\)", "", author).strip()
    docs = _search(title, 20)
    if author:
        # Titles aren't compared here: the best record is often under the original
        # title (Le Comte de Monte-Cristo). When this picks the author's other,
        # better-known book instead, pin the right work in selection.toml.
        docs = [d for d in docs if _same_author(author, d.get("author_name", []))] or [
            d for d in _search(f"{title} {author}", 5)
            if _same_author(author, d.get("author_name", [])) or _same_title(title, d.get("title", ""))
        ]
    if not docs:
        return None
    doc = docs[0]
    work = _get(f"{doc['key']}.json")
    count = int(doc.get("ratings_count") or 0)
    rating = round(float(doc["ratings_average"]), 2) if count and doc.get("ratings_average") else None
    return BookInfo(doc["key"], _description_text(work.get("description")), rating, count, doc.get("first_publish_year"))


def work(work_key: str) -> BookInfo:
    """A specific work, for when lookup() picks the wrong one (pinned in selection.toml)."""
    record = _get(f"{work_key}.json")
    ratings = _get(f"{work_key}/ratings.json").get("summary", {})
    count = int(ratings.get("count") or 0)
    rating = round(float(ratings["average"]), 2) if count and ratings.get("average") else None
    year = re.search(r"\d{3,4}", str(record.get("first_publish_date", "")))
    return BookInfo(work_key, _description_text(record.get("description")), rating, count, int(year.group()) if year else None)
