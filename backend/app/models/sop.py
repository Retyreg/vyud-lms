import secrets

from sqlalchemy import Boolean, Column, Date, Integer, String, Text, ForeignKey, JSON, DateTime
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.db.base import Base


class SOP(Base):
    __tablename__ = "sops"

    id = Column(Integer, primary_key=True, index=True)
    org_id = Column(Integer, ForeignKey("organizations.id"), nullable=False, index=True)
    title = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    status = Column(String, default="draft", nullable=False)
    created_by = Column(String, nullable=False)
    quiz_json = Column(JSON, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    steps = relationship("SOPStep", back_populates="sop", order_by="SOPStep.step_number")


class SOPStep(Base):
    __tablename__ = "sop_steps"

    id = Column(Integer, primary_key=True, index=True)
    sop_id = Column(Integer, ForeignKey("sops.id", ondelete="CASCADE"), nullable=False, index=True)
    step_number = Column(Integer, nullable=False)
    title = Column(String, nullable=False)
    content = Column(Text, nullable=False)
    image_url = Column(String, nullable=True)

    sop = relationship("SOP", back_populates="steps")


class SOPCompletion(Base):
    __tablename__ = "sop_completions"

    id = Column(Integer, primary_key=True, index=True)
    sop_id = Column(Integer, ForeignKey("sops.id", ondelete="CASCADE"), nullable=False, index=True)
    user_key = Column(String, nullable=False, index=True)
    score = Column(Integer, nullable=True)
    max_score = Column(Integer, nullable=True)
    completed_at = Column(DateTime(timezone=True), server_default=func.now())
    time_spent_sec = Column(Integer, nullable=True)


class SOPAssignment(Base):
    __tablename__ = "sop_assignments"

    id = Column(Integer, primary_key=True, index=True)
    org_id = Column(Integer, ForeignKey("organizations.id"), nullable=False, index=True)
    sop_id = Column(Integer, ForeignKey("sops.id", ondelete="CASCADE"), nullable=False, index=True)
    user_key = Column(String, nullable=False, index=True)
    assigned_by = Column(String, nullable=False)
    deadline = Column(Date, nullable=False)
    assigned_at = Column(DateTime(timezone=True), server_default=func.now())
    reminder_sent = Column(Boolean, default=False, nullable=False)


class SOPCertificate(Base):
    __tablename__ = "sop_certificates"

    id         = Column(Integer, primary_key=True, index=True)
    user_key   = Column(String, nullable=False, index=True)
    sop_id     = Column(Integer, ForeignKey("sops.id", ondelete="CASCADE"), nullable=False, index=True)
    org_id     = Column(Integer, ForeignKey("organizations.id"), nullable=False)
    cert_token = Column(String, unique=True, nullable=False, default=lambda: secrets.token_urlsafe(12))
    score      = Column(Integer, nullable=True)
    max_score  = Column(Integer, nullable=True)
    issued_at  = Column(DateTime(timezone=True), server_default=func.now())
