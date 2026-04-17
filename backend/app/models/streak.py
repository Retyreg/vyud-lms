from sqlalchemy import Column, Integer, String, Date, JSON
from app.db.base import Base


class UserStreak(Base):
    __tablename__ = "user_streaks"

    id = Column(Integer, primary_key=True, index=True)
    user_key = Column(String, index=True, nullable=False, unique=True)
    current_streak = Column(Integer, default=0, nullable=False)
    longest_streak = Column(Integer, default=0, nullable=False)
    last_activity_date = Column(Date, nullable=True)
    total_days_active = Column(Integer, default=0, nullable=False)
    # ISO date strings of active days, kept for last 365 days
    activity_dates = Column(JSON, default=list, nullable=False, server_default="[]")
