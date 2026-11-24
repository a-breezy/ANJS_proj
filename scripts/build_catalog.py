"""Build catalog/catalog.json from the hand-picked list in catalog/selection.toml.

Run from the project root:

    python scripts/build_catalog.py            # fetch only books not already built
    python scripts/build_catalog.py --refresh  # fetch every book again

For each book in the selection it:

1. reads title, authors and subjects from Project Gutenberg's own catalogue
   file (pg_catalog.csv, downloaded once to .data/);
2. asks Gutendex for the download count and summary. Gutendex is often slow or
   down, so this is best-effort: without it, downloads are 0 and Open Library's
   rating count decides the "bestseller" order instead;
3. asks for the size of the plain-text edition (a HEAD request, nothing is
   downloaded) and sets the price from it;
4. saves the cover to catalog/covers/<id>.jpg;
5. looks the book up on Open Library for a description, star rating and first
   publication year. Gutenberg's summary is used when Open Library has no
   description.

Books already in catalog.json are reused unless --refresh is given, so after
editing selection.toml only the new books are fetched. Both catalog.json and
the covers are committed, so teammates don't need to run this.
"""
from __future__ import annotations

import argparse
import csv
import gzip
import json
import re
import sys
import time
import tomllib
import urllib.error
import urllib.parse
import urllib.request
from collections import Counter
from datetime import date
from pathlib import Path

PROJECT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT))

from gui import openlibrary  # noqa: E402

CATALOG = PROJECT / "catalog"
SELECTION_FILE = CATALOG / "selection.toml"
CATALOG_FILE = CATALOG / "catalog.json"
COVERS = CATALOG / "covers"

GUTENDEX = "https://gutendex.com/books/"
PG_CATALOG_URL = "https://www.gutenberg.org/cache/epub/feeds/pg_catalog.csv.gz"
PG_CATALOG_FILE = PROJECT / ".data" / "pg_catalog.csv.gz"
TEXT_URL = "https://www.gutenberg.org/cache/epub/{id}/pg{id}.txt"
COVER_URL = "https://www.gutenberg.org/cache/epub/{id}/pg{id}.cover.medium.jpg"
USER_AGENT = openlibrary.USER_AGENT
RETRIES = 5
GUTENDEX_RETRIES = 2  # Gutendex is optional; don't stall the import when it is down
OPEN_LIBRARY_PAUSE = 1.0  # seconds between Open Library lookups, to be polite
MAX_PER_AUTHOR = 2
MIN_DESCRIPTION = 150  # shorter Open Library descriptions lose to Gutenberg's summary
POSTHUMOUS_YEARS = 10  # a first-publication year this long after the author died is a bad match

# (largest plain-text size in bytes, price). Roughly 6 bytes per word, so
# under ~35k words is "short" and under ~115k words is "medium".
PRICE_TIERS = ((200_000, 4.99), (700_000, 9.99), (float("inf"), 14.99))
DEFAULT_PRICE = 9.99


# --- network ---------------------------------------------------------------
def _open(url: str, method: str = "GET"):
    request = urllib.request.Request(url, method=method, headers={"User-Agent": USER_AGENT})
    return urllib.request.urlopen(request, timeout=60, context=openlibrary._ssl_context())


def _with_retries(action, what: str, retries: int = RETRIES):
    """Servers here sometimes time out or send an empty reply; try a few times."""
    for attempt in range(retries):
        try:
            return action()
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, ConnectionError) as exc:
            if attempt == retries - 1:
                raise RuntimeError(f"{what} failed after {retries} tries: {exc}") from exc
            time.sleep(2 + 3 * attempt)


def get_json(url: str, retries: int = RETRIES) -> dict:
    def fetch():
        with _open(url) as response:
            return json.load(response)

    return _with_retries(fetch, url, retries)


def text_size(url: str) -> int | None:
    def head():
        with _open(url, method="HEAD") as response:
            length = response.headers.get("Content-Length")
            return int(length) if length else None

    try:
        return _with_retries(head, url)
    except RuntimeError:
        return None


def download(url: str, path: Path) -> None:
    def fetch():
        with _open(url) as response:
            return response.read()

    path.write_bytes(_with_retries(fetch, url))


# --- Gutenberg ---------------------------------------------------------------
def pg_catalog_records(ids: list[int], refresh: bool = False) -> dict[int, dict]:
    """Rows of Project Gutenberg's catalogue file for the given ids."""
    if refresh or not PG_CATALOG_FILE.is_file():
        print("Downloading Project Gutenberg's catalogue file (~6 MB)...")
        PG_CATALOG_FILE.parent.mkdir(parents=True, exist_ok=True)
        download(PG_CATALOG_URL, PG_CATALOG_FILE)
    wanted = set(ids)
    with gzip.open(PG_CATALOG_FILE, "rt", encoding="utf-8", newline="") as fh:
        return {int(row["Text#"]): row for row in csv.DictReader(fh) if row["Text#"].isdigit() and int(row["Text#"]) in wanted}


def gutendex_records(ids: list[int]) -> dict[int, dict]:
    """Gutendex records (for download counts and summaries), or {} if it is down."""
    records: dict[int, dict] = {}
    try:
        for start in range(0, len(ids), 32):
            url = GUTENDEX + "?" + urllib.parse.urlencode({"ids": ",".join(map(str, ids[start:start + 32]))})
            while url:
                page = get_json(url, GUTENDEX_RETRIES)
                records.update({r["id"]: r for r in page["results"]})
                url = page.get("next")
    except RuntimeError as exc:
        print(f"Gutendex unavailable, continuing without download counts and summaries ({exc}).")
    return records


def person_name(name: str) -> str:
    """'Austen, Jane, 1775-1817' -> 'Jane Austen'.

    Drops dates ('6th cent. BCE', '751? BCE-651? BCE'), expansions like
    '(Daniel Stephen)' and titles like 'Emperor of Rome' or 'Countess of'.
    """
    name = re.sub(r"\s*\(.*?\)", "", name)
    parts = [part.strip() for part in name.split(",")]
    keep = [parts[0]] + [
        part for part in parts[1:]
        if part and not re.search(r"\d|\bcent\b|\bcentury\b|\bactive\b", part) and not re.search(r"\bof\b", part)
    ]
    return f"{keep[1]} {keep[0]}" if len(keep) >= 2 else keep[0]


def authors_of(row: dict) -> str:
    """Authors from a catalogue row, skipping translators, editors and illustrators."""
    names = [a for a in row["Authors"].split("; ") if a.strip() and "[" not in a]
    return " & ".join(person_name(a) for a in names[:2]) or "Unknown"


def clean_title(title: str) -> str:
    """'Frankenstein; or, The modern Prometheus' -> 'Frankenstein'."""
    return " ".join(title.split(";")[0].split())


def clean_subjects(row: dict) -> list[str]:
    """Catalogue subjects ('England -- Fiction') and 'Category:' shelves, de-duplicated."""
    subjects: list[str] = []
    for subject in row.get("Subjects", "").split("; "):
        for part in subject.split(" -- "):
            part = part.strip().rstrip(".")
            if part and part.lower() != "fiction" and part not in subjects:
                subjects.append(part)
    for shelf in row.get("Bookshelves", "").split("; "):
        if shelf.startswith("Category: "):
            shelf = shelf.removeprefix("Category: ")
            if shelf not in subjects:
                subjects.append(shelf)
    return subjects


def price_for(size: int | None) -> float:
    if size is None:
        return DEFAULT_PRICE
    return next(price for limit, price in PRICE_TIERS if size <= limit)


def gutenberg_summary(record: dict) -> str:
    summaries = (record or {}).get("summaries") or [""]
    return re.sub(r"\s*\(This is an automatically generated summary\.\)\s*$", "", summaries[0]).strip()


# --- building ----------------------------------------------------------------
def load_selection(path: Path = SELECTION_FILE) -> list[dict]:
    entries = tomllib.loads(path.read_text(encoding="utf-8"))["book"]
    ids = Counter(e["id"] for e in entries)
    duplicates = [i for i, n in ids.items() if n > 1]
    if duplicates:
        raise SystemExit(f"selection.toml lists these ids more than once: {duplicates}")
    for entry in entries:
        if not entry.get("category"):
            raise SystemExit(f"selection.toml: book {entry['id']} has no category")
    return entries


def build_entry(entry: dict, row: dict, record: dict | None) -> dict:
    book_id = int(row["Text#"])
    title = entry.get("title") or clean_title(row["Title"])
    author = entry.get("author") or authors_of(row)

    size = text_size(TEXT_URL.format(id=book_id))

    cover_image = f"{book_id}.jpg"
    if not (COVERS / cover_image).is_file():
        try:
            download(COVER_URL.format(id=book_id), COVERS / cover_image)
        except RuntimeError as exc:
            print(f"    cover skipped: {exc}")
            cover_image = ""

    info = None
    try:
        if entry.get("openlibrary"):
            info = openlibrary.work(entry["openlibrary"])
        else:
            info = openlibrary.lookup(title, author)
    except openlibrary.OpenLibraryError as exc:
        print(f"    Open Library skipped: {exc}")
    time.sleep(OPEN_LIBRARY_PAUSE)

    summary = gutenberg_summary(record)
    use_open_library = info is not None and len(info.description) >= MIN_DESCRIPTION or (info and info.description and not summary)
    description = info.description if use_open_library else summary
    if entry.get("description"):
        description, use_open_library = entry["description"], False
    year = info.year if info else None
    deaths = [a["death_year"] for a in (record or {}).get("authors", []) if a.get("death_year") is not None]
    if year and deaths and year > max(deaths) + POSTHUMOUS_YEARS:
        year = None  # Open Library matched a later edition or adaptation
    year = entry.get("year", year)
    return {
        "id": book_id,
        "title": title,
        "author": author,
        "category": entry["category"],
        "price": price_for(size),
        "text_bytes": size,
        "description": description,
        "description_source": "selection" if entry.get("description") else "openlibrary" if use_open_library else ("gutenberg" if description else None),
        "rating": info.rating if info else None,
        "rating_count": info.rating_count if info else 0,
        "year": year,
        "subjects": clean_subjects(row),
        "downloads": (record or {}).get("download_count", 0),
        "cover_image": cover_image,
        "gutenberg_url": f"https://www.gutenberg.org/ebooks/{book_id}",
        "openlibrary_key": info.work_key if info else None,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--refresh", action="store_true", help="fetch every book again (and a fresh catalogue file)")
    args = parser.parse_args(argv)

    selection = load_selection()
    previous: dict[int, dict] = {}
    if CATALOG_FILE.is_file() and not args.refresh:
        previous = {b["id"]: b for b in json.loads(CATALOG_FILE.read_text(encoding="utf-8"))["books"]}
    COVERS.mkdir(parents=True, exist_ok=True)

    todo = [e["id"] for e in selection if e["id"] not in previous]
    print(f"{len(selection)} books selected, {len(todo)} to fetch.")
    rows = pg_catalog_records(todo, refresh=args.refresh) if todo else {}
    records = gutendex_records(todo) if todo else {}

    books, missing = [], []
    for n, entry in enumerate(selection, 1):
        if entry["id"] in previous:
            book = {**previous[entry["id"]], "category": entry["category"]}
            for key in ("title", "author", "year", "description"):
                if entry.get(key):
                    book[key] = entry[key]
            if entry.get("description"):
                book["description_source"] = "selection"
            books.append(book)
            continue
        row = rows.get(entry["id"])
        if row is None:
            missing.append(entry["id"])
            print(f"[{n:3}] {entry['id']}: not in Project Gutenberg's catalogue, skipped")
            continue
        book = build_entry(entry, row, records.get(entry["id"]))
        books.append(book)
        stars = f"{book['rating']:.1f}*" if book["rating"] else "unrated"
        print(f"[{n:3}] {book['title']} - {book['author']} (${book['price']}, {stars}, {book['description_source']})")

    for author, count in Counter(b["author"] for b in books).items():
        if count > MAX_PER_AUTHOR:
            print(f"Note: {author} has {count} books (the guideline is {MAX_PER_AUTHOR}).")

    categories = list(dict.fromkeys(e["category"] for e in selection))
    CATALOG_FILE.write_text(
        json.dumps({"generated": date.today().isoformat(), "categories": categories, "books": books}, indent=1, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(f"Wrote {len(books)} books to {CATALOG_FILE.relative_to(PROJECT)}.")
    if missing:
        print(f"Not found in Project Gutenberg's catalogue: {missing}")
    return 1 if missing else 0


if __name__ == "__main__":
    raise SystemExit(main())
