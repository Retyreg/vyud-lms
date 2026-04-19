from sqlalchemy import Column, DateTime, Integer, String, text
from sqlalchemy.dialects.postgresql import JSON

from app.db.base import Base


class SOPTemplate(Base):
    __tablename__ = "sop_templates"

    id = Column(Integer, primary_key=True)
    title = Column(String, nullable=False)
    description = Column(String, nullable=True)
    category = Column(String, nullable=False)
    steps = Column(JSON, nullable=False)
    quiz_json = Column(JSON, nullable=True)
    created_at = Column(DateTime, server_default=text("now()"), nullable=False)
