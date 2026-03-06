from sqlalchemy import Column, Integer, String, ForeignKey, Float
from sqlalchemy.orm import relationship
from app.db.base import Base

class KnowledgeNode(Base):
    __tablename__ = "knowledge_nodes"

    id = Column(Integer, primary_key=True, index=True)
    topic_name = Column(String, unique=True, index=True)
    # Связь с уроком, где эта тема раскрывается
    lesson_id = Column(Integer, ForeignKey("lessons.id"), nullable=True)

class KnowledgeEdge(Base):
    """Связи между темами (Граф знаний). 
    Например: 'Python Basics' -> 'Functions' с весом уверенности."""
    __tablename__ = "knowledge_edges"

    id = Column(Integer, primary_key=True, index=True)
    source_id = Column(Integer, ForeignKey("knowledge_nodes.id"))
    target_id = Column(Integer, ForeignKey("knowledge_nodes.id"))
    weight = Column(Float, default=1.0) # Сила связи
