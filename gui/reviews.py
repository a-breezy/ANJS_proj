"""Book reviews, weighted star ratings, taboo-word moderation, and SU order lists."""
from __future__ import annotations

import re
from datetime import date

from .data import SAMPLE_BOOKS, Book
from .store import Store

DEFAULT_TABOO_WORDS = ["spam", "scam", "trash", "idiot"]


class ReviewService:
    """Encapsulates all review, rating, taboo moderation, and order-list rules."""

    def __init__(self, store: Store) -> None:
        self.store = store
        self._ensure_schema()

    def _ensure_schema(self) -> None:
        data = self.store._data
        changed = False
        if "reviews" not in data:
            data["reviews"] = {}
            changed = True
        if "taboo_words" not in data:
            data["taboo_words"] = list(DEFAULT_TABOO_WORDS)
            changed = True
        if changed:
            self.store._save()

    # --- Purchase Verification --------------------------------------------
    def has_purchased(self, email: str | None, book_id: int) -> bool:
        """Return True if the signed-in user has ordered this book."""
        if not email or email.strip().lower() == "guest":
            return False
        for order in self.store.orders_for(email):
            if book_id in order.get("book_ids", []):
                return True
        return False

    # --- Taboo Words (SU-maintained) --------------------------------------
    def taboo_words(self) -> list[str]:
        return list(self.store._data.get("taboo_words", []))

    def add_taboo_word(self, word: str) -> bool:
        cleaned = word.strip().lower()
        words = self.store._data.setdefault("taboo_words", [])
        if not cleaned or cleaned in words:
            return False
        words.append(cleaned)
        self.store._save()
        return True

    def remove_taboo_word(self, word: str) -> bool:
        cleaned = word.strip().lower()
        words = self.store._data.get("taboo_words", [])
        if cleaned not in words:
            return False
        words.remove(cleaned)
        self.store._save()
        return True

    def filter_taboo(self, text: str) -> tuple[str, int]:
        """Replace taboo words with '*' and return (censored_text, taboo_count)."""
        words = self.taboo_words()
        if not words:
            return text, 0

        sorted_words = sorted(words, key=len, reverse=True)
        pattern = re.compile(
            r"\b(" + "|".join(re.escape(w) for w in sorted_words) + r")\b",
            flags=re.IGNORECASE,
        )
        count = 0

        def _replace(match: re.Match) -> str:
            nonlocal count
            count += 1
            return "*" * len(match.group(0))

        return pattern.sub(_replace, text), count

    # --- Reviews & Weighted Ratings ---------------------------------------
    def reviews_for(self, book_id: int) -> list[dict]:
        """Return reviews for a book with verified buyers sorted to the top."""
        raw = list(self.store._data.get("reviews", {}).get(str(book_id), []))
        return sorted(raw, key=lambda r: (not r.get("verified_buyer", False)))

    def rating_summary(self, book_id: int) -> tuple[float, int]:
        """Return (weighted_average_stars, review_count).

        Verified buyers receive weight 2.0; non-buyers receive weight 1.0.
        """
        reviews = self.store._data.get("reviews", {}).get(str(book_id), [])
        if not reviews:
            return 0.0, 0

        weighted_sum = 0.0
        total_weight = 0.0
        for r in reviews:
            weight = 2.0 if r.get("verified_buyer", False) else 1.0
            weighted_sum += float(r["stars"]) * weight
            total_weight += weight

        return round(weighted_sum / total_weight, 2), len(reviews)

    def submit_review(
        self,
        book_id: int,
        author_name: str,
        author_email: str | None,
        stars: int,
        comment: str,
    ) -> dict:
        """Post a review, mask 1-2 taboo words, or block >=3 and penalize user."""
        stars = max(1, min(5, int(stars)))
        cleaned_comment, taboo_count = self.filter_taboo(comment.strip())

        if taboo_count >= 3:
            demoted = False
            suspended = False
            msg = f"Comment blocked: contained {taboo_count} taboo words."

            user = self.store.get_user(author_email) if author_email else None
            if user is not None and user.get("role") != "SU":
                warnings = user.get("warnings", 0) + 1
                user["warnings"] = warnings

                if warnings >= 2:
                    if user.get("role") == "VC":
                        user["role"] = "RC"
                        user["warnings"] = 0
                        demoted = True
                        msg += (
                            " You reached 2 warnings and were demoted from VIP (VC) "
                            "to Registered Customer (RC)."
                        )
                    else:
                        user["suspended"] = True
                        suspended = True
                        msg += " You reached 2 warnings and your account has been suspended."
                else:
                    msg += f" Warning issued ({warnings}/2)."

                self.store._save()

            return {
                "accepted": False,
                "masked_count": taboo_count,
                "message": msg,
                "demoted": demoted,
                "suspended": suspended,
            }

        verified = self.has_purchased(author_email, book_id)
        entry = {
            "author_name": author_name.strip() or "Visitor",
            "author_email": (author_email or "").strip().lower(),
            "stars": stars,
            "comment": cleaned_comment,
            "verified_buyer": verified,
            "weight": 2.0 if verified else 1.0,
            "placed": date.today().isoformat(),
        }
        self.store._data.setdefault("reviews", {}).setdefault(str(book_id), []).append(entry)
        self.store._save()

        msg = "Review posted!"
        if taboo_count > 0:
            msg = f"Review posted ({taboo_count} taboo word(s) masked with '*')."

        return {
            "accepted": True,
            "masked_count": taboo_count,
            "message": msg,
            "demoted": False,
            "suspended": False,
        }

    # --- SU Order Lists & Account Reactivation ----------------------------
    def no_order_books(self) -> list[tuple[Book, float, int]]:
        """Books with > 3 reviews and weighted average rating < 2.0 (SU only)."""
        return [
            (book, avg, count)
            for book in SAMPLE_BOOKS
            for avg, count in [self.rating_summary(book.id)]
            if count > 3 and avg < 2.0
        ]

    def to_order_books(self) -> list[tuple[Book, float, int]]:
        """Books with > 3 reviews and weighted average rating > 4.0 (SU only)."""
        return [
            (book, avg, count)
            for book in SAMPLE_BOOKS
            for avg, count in [self.rating_summary(book.id)]
            if count > 3 and avg > 4.0
        ]

    def suspended_users(self) -> list[dict]:
        return [
            dict(u)
            for u in self.store._data.get("users", {}).values()
            if u.get("suspended", False)
        ]

    def unsuspend_user(self, email: str) -> None:
        user = self.store.get_user(email)
        if user is not None:
            user["suspended"] = False
            user["warnings"] = 0
            self.store._save()