import uuid

from sqlalchemy import Column, DateTime, ForeignKey, Integer
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from pgvector.sqlalchemy import Vector

from app.database.db import Base


class FaceEmbedding(Base):
    __tablename__ = "face_embeddings"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    embedding = Column(Vector(128), nullable=False)

    foto_index = Column(Integer, nullable=False)

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # RELATIONSHIP BACK
    user = relationship("User", back_populates="face_embeddings")
