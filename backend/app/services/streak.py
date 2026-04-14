from datetime import date, timedelta
from sqlalchemy.orm import Session
from app.models.streak import UserStreak

_KEEP_DAYS = 365


def update_streak(user_key: str, db: Session) -> UserStreak:
    """Call on any user activity (review, complete).
    - Same day → no change (already counted)
    - Yesterday → extend streak
    - Older / never → reset to 1
    Also appends today to activity_dates (kept for last 365 days).
    """
    today = date.today()

    streak = db.query(UserStreak).filter(UserStreak.user_key == user_key).first()
    if streak is None:
        streak = UserStreak(
            user_key=user_key,
            current_streak=0,
            longest_streak=0,
            total_days_active=0,
            activity_dates=[],
        )
        db.add(streak)

    last = streak.last_activity_date

    if last == today:
        return streak  # already counted today

    if last == today - timedelta(days=1):
        streak.current_streak += 1
    else:
        streak.current_streak = 1

    if streak.current_streak > streak.longest_streak:
        streak.longest_streak = streak.current_streak

    streak.last_activity_date = today
    streak.total_days_active += 1

    # Append today and keep only last _KEEP_DAYS dates
    today_str = today.isoformat()
    dates: list = list(streak.activity_dates or [])
    if today_str not in dates:
        dates.append(today_str)
    cutoff = (today - timedelta(days=_KEEP_DAYS)).isoformat()
    dates = [d for d in dates if d >= cutoff]
    streak.activity_dates = dates

    db.commit()
    db.refresh(streak)
    return streak


def get_streak(user_key: str, db: Session) -> UserStreak | None:
    """Return current streak record for a user, or None if not found."""
    return db.query(UserStreak).filter(UserStreak.user_key == user_key).first()
