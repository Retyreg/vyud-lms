import secrets
from sqlalchemy import Column, Integer, String, ForeignKey, Boolean, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.db.base import Base


class Organization(Base):
    __tablename__ = "organizations"

    id          = Column(Integer, primary_key=True, index=True)
    name        = Column(String, nullable=False)
    invite_code = Column(String, unique=True, index=True, nullable=False,
                         default=lambda: secrets.token_urlsafe(8))
    created_at  = Column(DateTime(timezone=True), server_default=func.now())

    members = relationship("OrgMember", back_populates="org")


class OrgMember(Base):
    __tablename__ = "org_members"

    id         = Column(Integer, primary_key=True, index=True)
    org_id     = Column(Integer, ForeignKey("organizations.id"), nullable=False, index=True)
    # Простая идентификация для пилота: email или Telegram user_id как строка
    user_key   = Column(String, nullable=False)
    is_manager = Column(Boolean, default=False)
    joined_at  = Column(DateTime(timezone=True), server_default=func.now())

    org = relationship("Organization", back_populates="members")
