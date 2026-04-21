import uuid
from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from app.db.base import Base


def _uuid() -> str:
    return str(uuid.uuid4())


class DemoUser(Base):
    __tablename__ = "demo_users"

    id = Column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    email = Column(String, nullable=False, unique=True, index=True)
    full_name = Column(String, nullable=False)
    company = Column(String, nullable=False)
    role = Column(String, nullable=False)       # Manager / L&D / Owner / Other
    industry = Column(String, nullable=False)   # HoReCa / Retail / FMCG / Other
    magic_token = Column(String, nullable=False, unique=True, index=True)
    session_expires_at = Column(DateTime(timezone=True), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    archived_at = Column(DateTime(timezone=True), nullable=True)
    ai_calls_today = Column(Integer, default=0, nullable=False, server_default="0")
    ai_calls_reset_at = Column(DateTime(timezone=True), nullable=True)
    # FK to the seeded Course so we can show the graph
    demo_course_id = Column(Integer, ForeignKey("courses.id"), nullable=True)


class DemoFeedback(Base):
    __tablename__ = "demo_feedback"

    id = Column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    demo_user_id = Column(
        UUID(as_uuid=False), ForeignKey("demo_users.id"), nullable=False, index=True
    )
    rating = Column(Integer, nullable=False)         # 1-5
    message = Column(String, nullable=True)
    wants_pilot = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
