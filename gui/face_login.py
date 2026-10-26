"""Compare a face scan with the scans saved for bookstore accounts."""
import math

from .data import User
from .store import Store

# Starting value for our class prototype. We need to test this with other people.
MIN_SCORE = 0.60
MIN_GAP = 0.10


def similarity(a: list[float], b: list[float]) -> float:
    """Return cosine similarity. A higher score means more similar faces."""
    if len(a) != 128 or len(b) != 128:
        return -1.0
    if not all(math.isfinite(x) for x in a + b):
        return -1.0

    dot = sum(x * y for x, y in zip(a, b))
    size_a = math.sqrt(sum(x * x for x in a))
    size_b = math.sqrt(sum(x * x for x in b))
    if size_a == 0 or size_b == 0:
        return -1.0
    return dot / (size_a * size_b)


def find_user_by_face(store: Store, features: list[float]) -> User | None:
    """Find an enrolled account, or return None if the scan is not clear enough."""
    matches = []
    for account in store.enrolled_face_accounts():
        scores = [similarity(features, sample)
                  for sample in account["face_templates"]]
        if scores:
            matches.append((max(scores), account))

    if not matches:
        return None

    matches.sort(key=lambda entry: entry[0], reverse=True)
    best_score, best_account = matches[0]
    if best_score < MIN_SCORE:
        return None

    # If two accounts look almost equally likely, don't choose one at random.
    if len(matches) > 1 and best_score - matches[1][0] < MIN_GAP:
        return None

    return User(name=best_account["name"], email=best_account["email"])
