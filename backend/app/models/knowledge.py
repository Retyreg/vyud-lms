from sqlalchemy import Column, Integer, String, ForeignKey, Float, Text, Boolean, JSON
from sqlalchemy.orm import relationship, backref
from app.db.base import Base

class KnowledgeNode(Base):
    __tablename__ = "knowledge_nodes"

    id = Column(Integer, primary_key=True, index=True)
    label = Column(String, index=True, nullable=False) # Название навыка (unique=True убрали)
    description = Column(Text, nullable=True)
    level = Column(Integer, default=1) # Уровень сложности (1 - база, 5 - эксперт)
    is_completed = Column(Boolean, default=False)
    prerequisites = Column(JSON, default=[]) # Список ID необходимых узлов
    parent_id = Column(Integer, ForeignKey("knowledge_nodes.id"), nullable=True) # ID родительского узла
    
    children = relationship("KnowledgeNode", backref=backref("parent", remote_side=[id]))

class KnowledgeEdge(Base):
    """Ребра графа. Показывают зависимость: чтобы изучить Target, нужно знать Source."""
    __tablename__ = "knowledge_edges"

    id = Column(Integer, primary_key=True, index=True)
    source_id = Column(Integer, ForeignKey("knowledge_nodes.id"))
    target_id = Column(Integer, ForeignKey("knowledge_nodes.id"))
    
    # Вес связи (насколько сильно зависит)
    weight = Column(Float, default=1.0)

    source_node = relationship("KnowledgeNode", foreign_keys=[source_id])
    target_node = relationship("KnowledgeNode", foreign_keys=[target_id])
