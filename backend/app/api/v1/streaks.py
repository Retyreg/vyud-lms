from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.deps import get_db
from app.services.streak import get_streak

router = APIRouter(prefix="/api", tags=["streaks"])

# (streak_days, badge_id, label)
_STREAK_BADGES = [
    (30, "legend",  "🔥 Легенда"),
    (14, "expert",  "⚡ Эксперт"),
    (7,  "master",  "🌟 Мастер"),
    (3,  "hot",     "💪 В ударе"),
    (1,  "newbie",  "🌱 Новичок"),
]

# Total active days milestones
_DAYS_BADGES = [
    (100, "century",  "🏆 Сотня дней"),
    (50,  "fifty",    "🎯 50 дней"),
    (20,  "regular",  "📅 Регуляр"),
    (10,  "bookworm", "📚 Книжник"),
]


def _compute_current_badge(current_streak: int) -> str | None:
    for days, _, label in _STREAK_BADGES:
        if current_streak >= days:
            return label
    return None


def _compute_achievements(current_streak: int, total_days: int) -> list[dict]:
    """Return all earned achievements sorted by prestige."""
    earned = []
    for days, badge_id, label in _STREAK_BADGES:
        if current_streak >= days:
            earned.append({"id": badge_id, "label": label, "type": "streak", "threshold": days})
    for days, badge_id, label in _DAYS_BADGES:
        if total_days >= days:
            earned.append({"id": badge_id, "label": label, "type": "days", "threshold": days})
    return earned


def _next_milestone(current_streak: int, total_days: int) -> dict | None:
    """Return the next badge the user can unlock."""
    for days, badge_id, label in reversed(_STREAK_BADGES):
        if current_streak < days:
            return {"label": label, "streak_needed": days, "days_left": days - current_streak}
    for days, badge_id, label in reversed(_DAYS_BADGES):
        if total_days < days:
            return {"label": label, "days_needed": days, "days_left": days - total_days}
    return None


@router.get("/streaks/{user_key}")
def get_user_streak(user_key: str, db: Session = Depends(get_db)):
    """Return streak info, badge, activity heatmap dates, and achievements."""
    streak = get_streak(user_key, db)
    if streak is None:
        return {
            "current_streak": 0,
            "longest_streak": 0,
            "total_days_active": 0,
            "last_activity_date": None,
            "badge": None,
            "activity_dates": [],
            "achievements": [],
            "next_milestone": {"label": "🌱 Новичок", "streak_needed": 1, "days_left": 1},
        }
    return {
        "current_streak": streak.current_streak,
        "longest_streak": streak.longest_streak,
        "total_days_active": streak.total_days_active,
        "last_activity_date": (
            streak.last_activity_date.isoformat() if streak.last_activity_date else None
        ),
        "badge": _compute_current_badge(streak.current_streak),
        "activity_dates": streak.activity_dates or [],
        "achievements": _compute_achievements(streak.current_streak, streak.total_days_active),
        "next_milestone": _next_milestone(streak.current_streak, streak.total_days_active),
    }
