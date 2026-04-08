"""Streak and badge endpoints."""
import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.dependencies import get_db
from app.services.streak import get_streak

logger = logging.getLogger(__name__)

router = APIRouter()


def _compute_badge(current_streak: int) -> str | None:
    if current_streak >= 30:
        return "🔥 Легенда"
    if current_streak >= 14:
        return "⚡ Эксперт"
    if current_streak >= 7:
        return "🌟 Мастер"
    if current_streak >= 3:
        return "💪 В ударе"
    if current_streak >= 1:
        return "🌱 Новичок"
    return None


@router.get("/api/streaks/{user_key}")
def get_user_streak(user_key: str, db: Session = Depends(get_db)):
    """Return streak info and badge for a user."""
    streak = get_streak(user_key, db)
    if streak is None:
        return {
            "current_streak": 0,
            "longest_streak": 0,
            "total_days_active": 0,
            "last_activity_date": None,
            "badge": None,
        }
    return {
        "current_streak": streak.current_streak,
        "longest_streak": streak.longest_streak,
        "total_days_active": streak.total_days_active,
        "last_activity_date": streak.last_activity_date.isoformat() if streak.last_activity_date else None,
        "badge": _compute_badge(streak.current_streak),
    }
