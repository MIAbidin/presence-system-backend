from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy.orm import Session
from app.models.user import User
from app.config import settings

# Setup bcrypt untuk hashing password
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


# ─── PASSWORD ────────────────────────────────────────────

def hash_password(password: str) -> str:
    """Hash password dengan bcrypt salt factor 12."""
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Bandingkan password plain dengan hash yang tersimpan."""
    return pwd_context.verify(plain_password, hashed_password)


# ─── JWT ─────────────────────────────────────────────────

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """
    Generate JWT access token.
    data: biasanya berisi {"sub": nim_nidn, "role": "mahasiswa"}
    """
    to_encode = data.copy()
    expire = datetime.utcnow() + (
        expires_delta or timedelta(hours=settings.ACCESS_TOKEN_EXPIRE_HOURS)
    )
    to_encode.update({"exp": expire, "type": "access"})
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def create_refresh_token(data: dict) -> str:
    """Generate JWT refresh token dengan masa berlaku 7 hari."""
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode.update({"exp": expire, "type": "refresh"})
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def verify_token(token: str) -> Optional[dict]:
    """
    Decode dan validasi JWT token.
    Return payload dict jika valid, None jika tidak valid/expired.
    """
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        return payload
    except JWTError:
        return None


# ─── DATABASE HELPER ─────────────────────────────────────

def get_user_by_nim_nidn(db: Session, nim_nidn: str) -> Optional[User]:
    """Cari user di database berdasarkan NIM (mahasiswa) atau NIDN (dosen)."""
    return db.query(User).filter(User.nim_nidn == nim_nidn).first()


def authenticate_user(db: Session, nim_nidn: str, password: str) -> Optional[User]:
    """
    Validasi login: cek user ada + password cocok + akun aktif.
    Return User object jika berhasil, None jika gagal.
    """
    user = get_user_by_nim_nidn(db, nim_nidn)
    if not user:
        return None
    if not user.is_active:
        return None
    if not verify_password(password, user.password_hash):
        return None
    return user