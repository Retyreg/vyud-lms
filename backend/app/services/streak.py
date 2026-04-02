from datetime import date, timedelta
from sqlalchemy.orm import Session
from app.models.streak import UserStreak


def update_streak(user_key: str, db: Session) -> UserStreak:
    """Call on any user activity (review, complete).
    - Same day → no change (already counted)
    - Yesterday → extend streak
    - Older / never → reset to 1
    """
    today = date.today()

    streak = db.query(UserStreak).filter(UserStreak.user_key == user_key).first()
    if streak is None:
        streak = UserStreak(user_key=user_key, current_streak=0, longest_streak=0, total_days_active=0)
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

    db.commit()
    db.refresh(streak)
    return streak


def get_streak(user_key: str, db: Session) -> UserStreak | None:
    """Return current streak record for a user, or None if not found."""
    return db.query(UserStreak).filter(UserStreak.user_key == user_key).first()
