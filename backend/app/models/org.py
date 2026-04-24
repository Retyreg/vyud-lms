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

    # Billing plan
    plan = Column(String, nullable=False, default="free")  # 'free' | 'starter' | 'team'

    # White-label branding
    brand_color   = Column(String, nullable=True)   # hex, e.g. "#3b82f6"
    logo_url      = Column(String, nullable=True)   # https://...
    bot_username  = Column(String, nullable=True)   # e.g. "MyCompanyBot"
    display_name  = Column(String, nullable=True)   # shown in TMA header (falls back to name)

    members = relationship("OrgMember", back_populates="org")


class OrgMember(Base):
    __tablename__ = "org_members"

    id           = Column(Integer, primary_key=True, index=True)
    org_id       = Column(Integer, ForeignKey("organizations.id"), nullable=False, index=True)
    user_key     = Column(String, nullable=False)
    display_name = Column(String, nullable=True)
    is_manager   = Column(Boolean, default=False)
    joined_at    = Column(DateTime(timezone=True), server_default=func.now())

    org = relationship("Organization", back_populates="members")
