"""SM-2 spaced repetition algorithm (SuperMemo 2, Wozniak 1987).

Quality grades (q):
    0 — completely forgot (😕)
    1 — wrong, but after answer remembered (😕+)
    2 — correct after hesitation (🤔)
    3 — correct with difficulty (🙂)
    4 — correct, minor hesitation (😊)
    5 — perfect recall (😊+)

For the 4-button UI we map:
    button 0 → q=0  (😕  — совсем не помню)
    button 1 → q=2  (🤔  — с трудом)
    button 2 → q=4  (🙂  — помню)
    button 3 → q=5  (😊  — легко)
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Tuple


# ---------------------------------------------------------------------------
# Core algorithm
# ---------------------------------------------------------------------------

def calculate_next_interval(
    q: int,
    repetitions: int,
    interval: int,
    easiness_factor: float,
) -> Tuple[int, int, float]:
    """Return (new_interval_days, new_repetitions, new_easiness_factor).

    Args:
        q: quality of recall, 0-5.
        repetitions: how many times the item has been reviewed successfully in a row.
        interval: current interval in days.
        easiness_factor: current EF (starts at 2.5, minimum 1.3).
    """
    if q < 0 or q > 5:
        raise ValueError(f"Quality q must be 0-5, got {q}")

    # Update easiness factor (EF)
    new_ef = easiness_factor + (0.1 - (5 - q) * (0.08 + (5 - q) * 0.02))
    new_ef = max(1.3, new_ef)

    if q < 3:
        # Failed recall — reset streak
        new_repetitions = 0
        new_interval = 1
    else:
        # Successful recall — advance
        new_repetitions = repetitions + 1
        if repetitions == 0:
            new_interval = 1
        elif repetitions == 1:
            new_interval = 6
        else:
            new_interval = round(interval * new_ef)

    return new_interval, new_repetitions, new_ef


# ---------------------------------------------------------------------------
# Mastery helpers
# ---------------------------------------------------------------------------

MASTERY_LEVELS = [
    (0,   "новый"),       # never reviewed
    (33,  "знакомый"),    # 1-33%
    (66,  "уверенный"),   # 34-66%
    (100, "освоен"),      # 67-100%
]


def mastery_pct(repetitions: int, easiness_factor: float = 2.5) -> int:
    """Return mastery as 0-100 integer.

    Each consecutive correct repetition contributes 20 points.
    EF bonus adds up to 10 points on top for well-retained items.
    5 repetitions with max EF → 100%.
    """
    base = min(100, repetitions * 20)
    ef_bonus = int((easiness_factor - 1.3) / 1.2 * 10)
    return min(100, base + ef_bonus)


def get_mastery_level(repetitions: int, correct_reviews: int, total_reviews: int) -> str:
    """Human-readable mastery label based on review history."""
    if total_reviews == 0:
        return "новый"
    ratio = correct_reviews / total_reviews * 100
    if ratio < 34:
        return "знакомый"
    if ratio < 67:
        return "уверенный"
    return "освоен"


def is_due(next_review: datetime | None) -> bool:
    """Return True if the card is due for review today or overdue."""
    if next_review is None:
        return True
    now = datetime.now(tz=timezone.utc)
    # next_review may be naive (SQLite) — normalise
    if next_review.tzinfo is None:
        next_review = next_review.replace(tzinfo=timezone.utc)
    return now >= next_review


def next_review_date(interval_days: int) -> datetime:
    return datetime.now(tz=timezone.utc) + timedelta(days=interval_days)
