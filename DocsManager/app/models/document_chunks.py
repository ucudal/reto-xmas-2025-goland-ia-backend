
from DocsManager.app.core.db_connection import Base
from sqlalchemy import Column, Integer, Text, TIMESTAMP, ForeignKey, UniqueConstraint, func
from pgvector.sqlalchemy import Vector
from sqlalchemy.orm import relationship



class DocumentChunk(Base):
    __tablename__ = "document_chunks"
    __table_args__ = (
        UniqueConstraint("document_id", "chunk_index", name="unique_document_chunk"),
    )

    id = Column(Integer, primary_key=True)
    document_id = Column(
        Integer,
        ForeignKey("documents.id", ondelete="CASCADE"),
        nullable=False
    )
    chunk_index = Column(Integer, nullable=False)
    content = Column(Text, nullable=False)
    embedding = Column(Vector(1536), nullable=False)
    created_at = Column(TIMESTAMP, server_default=func.current_timestamp(), nullable=False)

    document = relationship("Document", back_populates="chunks")
