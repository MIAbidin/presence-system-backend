# app/services/superadmin_service.py
"""
Service layer untuk Super Admin (Fase E).

Mencakup:
1. Manajemen akun Admin Fakultas (CRUD + reset password)
2. Manajemen konfigurasi sistem (baca, update)
3. Helper: get_config_value() — dipakai face_service dan geo_utils
"""
import logging
from typing import Optional
from uuid import UUID

from passlib.context import CryptContext
from sqlalchemy.orm import Session

from app.models.konfigurasi_sistem import KonfigurasiSistem, KonfigKey
from app.models.user import User, UserRole
from app.schemas.superadmin import (
    BuatAdminRequest,
    UpdateAdminRequest,
    UpdateKonfigurasiRequest,
)

logger = logging.getLogger(__name__)
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


# ══════════════════════════════════════════════════════════════
# 1. MANAJEMEN AKUN ADMIN FAKULTAS
# ══════════════════════════════════════════════════════════════

def list_admins(
    db: Session,
    search: Optional[str] = None,
    page: int = 1,
    limit: int = 20,
) -> dict:
    """
    List semua akun Admin Fakultas (role='admin').
    Super Admin (role='super_admin') TIDAK ditampilkan di sini.
    """
    q = db.query(User).filter(
        User.role == UserRole.admin,
    )

    if search:
        like = f"%{search}%"
        q = q.filter(
            (User.nama_lengkap.ilike(like)) |
            (User.nim_nidn.ilike(like)) |
            (User.email.ilike(like))
        )

    total = q.count()
    admins = q.order_by(User.nama_lengkap).offset((page - 1) * limit).limit(limit).all()

    return {
        "total"  : total,
        "page"   : page,
        "limit"  : limit,
        "data"   : admins,
    }


def get_admin(db: Session, admin_id: UUID) -> Optional[User]:
    """Ambil satu akun admin berdasarkan ID."""
    return db.query(User).filter(
        User.id == admin_id,
        User.role == UserRole.admin,
    ).first()


def buat_admin(db: Session, req: BuatAdminRequest) -> User:
    """
    Buat akun Admin Fakultas baru.
    Raises ValueError jika nim_nidn atau email sudah terdaftar.
    """
    # Cek duplikat
    if db.query(User).filter(User.nim_nidn == req.nim_nidn).first():
        raise ValueError(f"NIM/NIDN '{req.nim_nidn}' sudah terdaftar")
    if db.query(User).filter(User.email == req.email).first():
        raise ValueError(f"Email '{req.email}' sudah terdaftar")

    admin = User(
        nim_nidn      = req.nim_nidn,
        nama_lengkap  = req.nama_lengkap,
        email         = req.email,
        password_hash = pwd_context.hash(req.password),
        role          = UserRole.admin,
        program_studi = req.program_studi,
        is_active     = True,
        is_face_registered = False,
    )
    db.add(admin)
    db.commit()
    db.refresh(admin)

    logger.info(f"Akun admin baru dibuat: {admin.nim_nidn} ({admin.nama_lengkap})")
    return admin


def update_admin(db: Session, admin_id: UUID, req: UpdateAdminRequest) -> User:
    """
    Update data Admin Fakultas.
    Raises ValueError jika tidak ditemukan atau duplikat data.
    """
    admin = get_admin(db, admin_id)
    if not admin:
        raise ValueError("Admin tidak ditemukan")

    # Cek duplikat nim_nidn jika diubah
    if req.nim_nidn and req.nim_nidn != admin.nim_nidn:
        if db.query(User).filter(User.nim_nidn == req.nim_nidn).first():
            raise ValueError(f"NIM/NIDN '{req.nim_nidn}' sudah dipakai akun lain")
        admin.nim_nidn = req.nim_nidn

    # Cek duplikat email jika diubah
    if req.email and req.email != admin.email:
        if db.query(User).filter(User.email == req.email).first():
            raise ValueError(f"Email '{req.email}' sudah dipakai akun lain")
        admin.email = req.email

    if req.nama_lengkap is not None:
        admin.nama_lengkap = req.nama_lengkap
    if req.program_studi is not None:
        admin.program_studi = req.program_studi

    db.commit()
    db.refresh(admin)

    logger.info(f"Akun admin diupdate: {admin.nim_nidn}")
    return admin


def toggle_admin_aktif(db: Session, admin_id: UUID, is_active: bool) -> User:
    """
    Aktifkan / nonaktifkan akun Admin Fakultas.
    Super Admin tidak bisa menonaktifkan dirinya sendiri (divalidasi di router).
    """
    admin = get_admin(db, admin_id)
    if not admin:
        raise ValueError("Admin tidak ditemukan")

    admin.is_active = is_active
    db.commit()
    db.refresh(admin)

    status = "diaktifkan" if is_active else "dinonaktifkan"
    logger.info(f"Akun admin {admin.nim_nidn} {status}")
    return admin


def reset_password_admin(
    db: Session,
    admin_id: UUID,
    password_baru: str,
) -> bool:
    """Reset password Admin Fakultas. Return True jika berhasil."""
    admin = get_admin(db, admin_id)
    if not admin:
        raise ValueError("Admin tidak ditemukan")

    admin.password_hash = pwd_context.hash(password_baru)
    db.commit()

    logger.info(f"Password admin {admin.nim_nidn} direset oleh Super Admin")
    return True


# ══════════════════════════════════════════════════════════════
# 2. MANAJEMEN KONFIGURASI SISTEM
# ══════════════════════════════════════════════════════════════

def list_konfigurasi(db: Session) -> list[KonfigurasiSistem]:
    """Ambil semua konfigurasi sistem, urut berdasarkan key."""
    return db.query(KonfigurasiSistem).order_by(KonfigurasiSistem.key).all()


def get_konfigurasi(db: Session, key: str) -> Optional[KonfigurasiSistem]:
    """Ambil satu konfigurasi berdasarkan key."""
    return db.query(KonfigurasiSistem).filter(
        KonfigurasiSistem.key == key
    ).first()


def update_konfigurasi(
    db: Session,
    key: str,
    req: UpdateKonfigurasiRequest,
) -> KonfigurasiSistem:
    """
    Update nilai konfigurasi sistem.
    Raises ValueError jika key tidak ditemukan atau readonly.
    """
    konfig = get_konfigurasi(db, key)
    if not konfig:
        raise ValueError(f"Konfigurasi '{key}' tidak ditemukan")
    if konfig.is_readonly:
        raise ValueError(f"Konfigurasi '{key}' bersifat read-only dan tidak bisa diubah via API")

    # Validasi tipe + range
    _validasi_nilai(konfig, req.value)

    konfig.value = req.value
    db.commit()
    db.refresh(konfig)

    logger.info(f"Konfigurasi '{key}' diubah → '{req.value}'")
    return konfig


def _validasi_nilai(konfig: KonfigurasiSistem, value: str) -> None:
    """
    Validasi nilai sesuai tipe dan range min/max.
    Raises ValueError jika tidak valid.
    """
    tipe = konfig.tipe

    if tipe == "float":
        try:
            v = float(value)
        except ValueError:
            raise ValueError(f"Nilai harus berupa angka desimal, bukan '{value}'")
        if konfig.nilai_min and v < float(konfig.nilai_min):
            raise ValueError(f"Nilai minimum adalah {konfig.nilai_min}")
        if konfig.nilai_max and v > float(konfig.nilai_max):
            raise ValueError(f"Nilai maksimum adalah {konfig.nilai_max}")

    elif tipe == "integer":
        try:
            v = int(value)
        except ValueError:
            raise ValueError(f"Nilai harus berupa bilangan bulat, bukan '{value}'")
        if konfig.nilai_min and v < int(konfig.nilai_min):
            raise ValueError(f"Nilai minimum adalah {konfig.nilai_min}")
        if konfig.nilai_max and v > int(konfig.nilai_max):
            raise ValueError(f"Nilai maksimum adalah {konfig.nilai_max}")

    elif tipe == "boolean":
        if value.lower() not in ("true", "false"):
            raise ValueError(f"Nilai boolean harus 'true' atau 'false', bukan '{value}'")


# ══════════════════════════════════════════════════════════════
# 3. HELPER: get_config_value() — dipakai service lain
# ══════════════════════════════════════════════════════════════

def get_config_value(db: Session, key: str, default: str = "") -> str:
    """
    Ambil nilai konfigurasi sebagai string.
    Return default jika key tidak ada di database.

    Dipakai oleh:
      - face_service.py   → face_threshold
      - geo_utils.py      → geofencing_radius
    """
    konfig = get_konfigurasi(db, key)
    return konfig.value if konfig else default


def get_face_threshold(db: Session) -> float:
    """
    Ambil threshold face recognition dari konfigurasi sistem.
    Fallback ke 0.9 jika belum ada di DB (misal: sebelum migration Fase E).
    """
    raw = get_config_value(db, KonfigKey.FACE_THRESHOLD, default="0.9")
    try:
        return float(raw)
    except ValueError:
        logger.warning(f"face_threshold tidak valid ({raw!r}), pakai default 0.9")
        return 0.9


def get_geofencing_radius(db: Session) -> float:
    """
    Ambil radius geofencing dari konfigurasi sistem.
    Fallback ke 100.0 meter jika belum ada di DB.
    """
    raw = get_config_value(db, KonfigKey.GEOFENCING_RADIUS, default="100")
    try:
        return float(raw)
    except ValueError:
        logger.warning(f"geofencing_radius tidak valid ({raw!r}), pakai default 100")
        return 100.0


def is_maintenance_mode(db: Session) -> bool:
    """
    Cek apakah sistem sedang dalam mode maintenance.
    Return False jika konfigurasi belum ada.
    """
    raw = get_config_value(db, KonfigKey.MAINTENANCE_MODE, default="false")
    return raw.lower() == "true"


def get_max_foto_registrasi(db: Session) -> int:
    """
    Ambil jumlah foto minimal registrasi wajah dari konfigurasi.
    Fallback ke 8 jika belum ada.
    """
    raw = get_config_value(db, KonfigKey.MAX_FOTO_REGISTRASI, default="8")
    try:
        return int(raw)
    except ValueError:
        return 8