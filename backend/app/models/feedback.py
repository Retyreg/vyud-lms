from sqlalchemy import Column, Integer, String, Text, DateTime
from sqlalchemy.sql import func
from app.db.base import Base


class Feedback(Base):
    __tablename__ = "feedback"

    id         = Column(Integer, primary_key=True, index=True)
    user_key   = Column(String, nullable=True)        # anonymous if absent
    rating     = Column(Integer, nullable=True)        # 1-5
    liked      = Column(Text, nullable=True)           # что понравилось
    missing    = Column(Text, nullable=True)           # чего не хватает
    feature    = Column(Text, nullable=True)           # запрос фичи
    contact    = Column(String, nullable=True)         # email / telegram
    page       = Column(String, nullable=True)         # url path
    created_at = Column(DateTime(timezone=True), server_default=func.now())
