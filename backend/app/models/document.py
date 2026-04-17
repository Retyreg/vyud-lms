from sqlalchemy import Column, Integer, Text, ForeignKey
from pgvector.sqlalchemy import Vector
from app.db.base import Base


class DocumentChunk(Base):
    __tablename__ = "document_chunks"

    id = Column(Integer, primary_key=True, index=True)
    course_id = Column(Integer, ForeignKey("courses.id"), index=True, nullable=False)
    chunk_text = Column(Text, nullable=False)
    chunk_index = Column(Integer, nullable=False)
    embedding = Column(Vector(1536), nullable=True)
