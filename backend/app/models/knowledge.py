from sqlalchemy import Column, Integer, String, ForeignKey, Float, Text
from sqlalchemy.orm import relationship
from app.db.base import Base

class KnowledgeNode(Base):
    __tablename__ = "knowledge_nodes"

    id = Column(Integer, primary_key=True, index=True)
    label = Column(String, unique=True, index=True, nullable=False) # Название навыка
    description = Column(Text, nullable=True)
    level = Column(Integer, default=1) # Уровень сложности (1 - база, 5 - эксперт)
    
    # Связь: какие уроки прокачивают этот навык
    # (В будущем можно сделать Many-to-Many, пока упростим)
    
class KnowledgeEdge(Base):
    """Ребра графа. Показывают зависимость: чтобы изучить Target, нужно знать Source."""
    __tablename__ = "knowledge_edges"

    id = Column(Integer, primary_key=True, index=True)
    source_id = Column(Integer, ForeignKey("knowledge_nodes.id"))
    target_id = Column(Integer, ForeignKey("knowledge_nodes.id"))
    
    # Вес связи (насколько сильно зависит)
    weight = Column(Float, default=1.0)
