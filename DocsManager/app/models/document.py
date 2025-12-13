from sqlalchemy import (
    Column,
    Integer,
    Text,
    TIMESTAMP,
    func
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from db_connection import Base

class Document(Base):
    __tablename__ = "documents"

    id = Column(Integer, primary_key=True)
    filename = Column(Text, nullable=False)
    minio_path = Column(Text, nullable=False)
    uploaded_at = Column(TIMESTAMP, server_default=func.current_timestamp())

    chunks = relationship(
        "DocumentChunk",
        back_populates="document",
        cascade="all, delete-orphan"
    )
