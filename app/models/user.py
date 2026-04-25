import uuid
import enum

from sqlalchemy import Column, String, Boolean, Enum, DateTime
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database.db import Base


class UserRole(str, enum.Enum):
    mahasiswa = "mahasiswa"
    dosen = "dosen"
    admin = "admin"


class User(Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    nim_nidn = Column(String(20), unique=True, nullable=False)
    nama_lengkap = Column(String(100), nullable=False)
    email = Column(String(100), unique=True, nullable=False)
    password_hash = Column(String(255), nullable=False)

    role = Column(Enum(UserRole), nullable=False)
    program_studi = Column(String(100), nullable=False)

    is_face_registered = Column(Boolean, default=False)
    is_active = Column(Boolean, default=True)

    # 🔥 NOTIFIKASI
    fcm_token = Column(String(255), nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # RELATIONSHIP
    face_embeddings = relationship(
        "FaceEmbedding",
        back_populates="user",
        cascade="all, delete"
    )
