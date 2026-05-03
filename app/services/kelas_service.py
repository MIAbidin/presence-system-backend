# app/services/kelas_service.py
"""
Fase B — Business logic untuk CRUD Kelas per Matakuliah.

Fungsi:
- list_kelas        : list semua kelas satu MK (dengan dosen, ruangan, enrolled count)
- create_kelas      : tambah kelas baru
- update_kelas      : partial update kelas
- delete_kelas      : hapus kelas (cek mahasiswa terdaftar)
- toggle_izin_tamu_kelas : toggle izin_tamu per kelas
- get_mahasiswa_kelas    : list mahasiswa terdaftar di kelas (asli + tamu)
"""

from typing import Optional, Tuple, Dict, Any, List
from uuid import UUID

from sqlalchemy.orm import Session
from sqlalchemy import func

from app.models.kelas_matakuliah import KelasMatakuliah
from app.models.matakuliah import Matakuliah
from app.models.mahasiswa_matakuliah import MahasiswaMatakuliah
from app.models.user import User, UserRole
from app.models.ruangan import Ruangan
from app.utils.slot_utils import slot_ke_jam, slot_ke_str


# ── Helper ────────────────────────────────────────────────────

def _kelas_to_dict(kelas: KelasMatakuliah, enrolled_count: int = 0) -> Dict[str, Any]:
    """Serialize KelasMatakuliah ke dict yang aman untuk JSON."""
    dosen  = kelas.dosen
    ruangan = kelas.ruangan

    # Hitung jam dari slot
    jam_mulai_str   = None
    jam_selesai_str = None
    jam_range       = None
    if kelas.slot_mulai and kelas.slot_selesai:
        try:
            jam_mulai, jam_selesai = slot_ke_jam(kelas.slot_mulai, kelas.slot_selesai)
            jam_mulai_str   = jam_mulai.strftime("%H:%M")
            jam_selesai_str = jam_selesai.strftime("%H:%M")
            jam_range       = slot_ke_str(kelas.slot_mulai, kelas.slot_selesai)
        except (ValueError, KeyError):
            pass

    return {
        "id"           : str(kelas.id),
        "matakuliah_id": str(kelas.matakuliah_id),
        "kode_kelas"   : kelas.kode_kelas,

        # Dosen
        "dosen_id"     : str(kelas.dosen_id)       if kelas.dosen_id  else None,
        "nama_dosen"   : dosen.nama_lengkap         if dosen           else None,
        "nidn_dosen"   : dosen.nim_nidn             if dosen           else None,

        # Ruangan
        "ruangan_id"   : str(kelas.ruangan_id)      if kelas.ruangan_id else None,
        "kode_ruangan" : ruangan.kode                if ruangan         else None,
        "nama_ruangan" : ruangan.nama                if ruangan         else None,
        "tipe_ruangan" : ruangan.tipe                if ruangan         else None,

        # Jadwal
        "hari"         : kelas.hari,
        "slot_mulai"   : kelas.slot_mulai,
        "slot_selesai" : kelas.slot_selesai,
        "jam_mulai"    : jam_mulai_str,
        "jam_selesai"  : jam_selesai_str,
        "jam_range"    : jam_range,        # "07:00 – 09:30"

        # Info tambahan
        "kode_akses"   : kelas.kode_akses,
        "izin_tamu"    : kelas.izin_tamu,
        "is_active"    : kelas.is_active,
        "total_enrolled": enrolled_count,
        "created_at"   : kelas.created_at.isoformat() if kelas.created_at else None,
    }


# ── LIST KELAS ────────────────────────────────────────────────

def list_kelas(db: Session, matakuliah_id: UUID) -> Optional[Dict]:
    """
    List semua kelas dari satu matakuliah.
    Return None jika matakuliah tidak ditemukan.
    """
    mk = db.query(Matakuliah).filter(Matakuliah.id == matakuliah_id).first()
    if not mk:
        return None

    kelas_list = (
        db.query(KelasMatakuliah)
        .filter(KelasMatakuliah.matakuliah_id == matakuliah_id)
        .order_by(KelasMatakuliah.kode_kelas)
        .all()
    )

    if not kelas_list:
        return {
            "matakuliah_id": str(matakuliah_id),
            "kode_mk"      : mk.kode,
            "nama_mk"      : mk.nama,
            "total_kelas"  : 0,
            "kelas"        : [],
        }

    # Bulk count enrolled mahasiswa per kelas
    kelas_ids = [k.id for k in kelas_list]
    count_rows = (
        db.query(
            MahasiswaMatakuliah.kelas_id,
            func.count(MahasiswaMatakuliah.id).label("cnt")
        )
        .filter(MahasiswaMatakuliah.kelas_id.in_(kelas_ids))
        .group_by(MahasiswaMatakuliah.kelas_id)
        .all()
    )
    count_map = {str(r.kelas_id): r.cnt for r in count_rows}

    # Juga hitung yang enrolled di MK ini tanpa kelas_id (legacy)
    legacy_count = (
        db.query(func.count(MahasiswaMatakuliah.id))
        .filter(
            MahasiswaMatakuliah.matakuliah_id == matakuliah_id,
            MahasiswaMatakuliah.kelas_id.is_(None),
        )
        .scalar()
    ) or 0

    kelas_dicts = [
        _kelas_to_dict(k, count_map.get(str(k.id), 0))
        for k in kelas_list
    ]

    return {
        "matakuliah_id" : str(matakuliah_id),
        "kode_mk"       : mk.kode,
        "nama_mk"       : mk.nama,
        "total_kelas"   : len(kelas_list),
        "legacy_enrolled": legacy_count,   # enrollment lama tanpa kelas
        "kelas"         : kelas_dicts,
    }


# ── CREATE KELAS ──────────────────────────────────────────────

def create_kelas(
    db           : Session,
    matakuliah_id: UUID,
    req,
) -> Tuple[bool, str, Optional[Dict]]:
    """
    Tambah kelas baru ke matakuliah.
    Return: (success, pesan, kelas_dict | None)
    """
    mk = db.query(Matakuliah).filter(Matakuliah.id == matakuliah_id).first()
    if not mk:
        return False, "Matakuliah tidak ditemukan", None

    # Normalisasi kode kelas ke uppercase
    kode = req.kode_kelas.strip().upper()

    # Cek duplikat kode kelas dalam MK ini
    existing = db.query(KelasMatakuliah).filter(
        KelasMatakuliah.matakuliah_id == matakuliah_id,
        KelasMatakuliah.kode_kelas    == kode,
    ).first()
    if existing:
        return False, f"Kelas {kode} sudah ada di matakuliah {mk.kode}", None

    # Validasi dosen (jika diisi)
    if req.dosen_id:
        dosen = db.query(User).filter(
            User.id   == req.dosen_id,
            User.role == UserRole.dosen,
        ).first()
        if not dosen:
            return False, "Dosen tidak ditemukan atau bukan role dosen", None

    # Validasi ruangan (jika diisi)
    if req.ruangan_id:
        ruangan = db.query(Ruangan).filter(Ruangan.id == req.ruangan_id).first()
        if not ruangan:
            return False, "Ruangan tidak ditemukan", None
        if not ruangan.is_active:
            return False, f"Ruangan {ruangan.kode} tidak aktif", None

    kelas = KelasMatakuliah(
        matakuliah_id = matakuliah_id,
        kode_kelas    = kode,
        dosen_id      = req.dosen_id or None,
        ruangan_id    = req.ruangan_id or None,
        hari          = req.hari or None,
        slot_mulai    = req.slot_mulai or None,
        slot_selesai  = req.slot_selesai or None,
        kode_akses    = req.kode_akses or None,
        izin_tamu     = req.izin_tamu,
        is_active     = True,
    )
    db.add(kelas)
    db.commit()
    db.refresh(kelas)

    return True, f"Kelas {kode} berhasil ditambahkan ke {mk.kode}", _kelas_to_dict(kelas)


# ── UPDATE KELAS ──────────────────────────────────────────────

def update_kelas(
    db           : Session,
    matakuliah_id: UUID,
    kelas_id     : UUID,
    req,
) -> Tuple[bool, str, Optional[Dict]]:
    """
    Partial update kelas. Semua field opsional.
    Return: (success, pesan, kelas_dict | None)
    """
    kelas = db.query(KelasMatakuliah).filter(
        KelasMatakuliah.id            == kelas_id,
        KelasMatakuliah.matakuliah_id == matakuliah_id,
    ).first()
    if not kelas:
        return False, "Kelas tidak ditemukan", None

    # Update kode_kelas (cek duplikat)
    if req.kode_kelas is not None:
        kode_baru = req.kode_kelas.strip().upper()
        if kode_baru != kelas.kode_kelas:
            existing = db.query(KelasMatakuliah).filter(
                KelasMatakuliah.matakuliah_id == matakuliah_id,
                KelasMatakuliah.kode_kelas    == kode_baru,
                KelasMatakuliah.id            != kelas_id,
            ).first()
            if existing:
                return False, f"Kelas {kode_baru} sudah ada di matakuliah ini", None
        kelas.kode_kelas = kode_baru

    # Validasi dan update dosen
    if req.dosen_id is not None:
        if req.dosen_id:
            dosen = db.query(User).filter(
                User.id   == req.dosen_id,
                User.role == UserRole.dosen,
            ).first()
            if not dosen:
                return False, "Dosen tidak ditemukan", None
        kelas.dosen_id = req.dosen_id or None

    # Validasi dan update ruangan
    if req.ruangan_id is not None:
        if req.ruangan_id:
            ruangan = db.query(Ruangan).filter(Ruangan.id == req.ruangan_id).first()
            if not ruangan:
                return False, "Ruangan tidak ditemukan", None
        kelas.ruangan_id = req.ruangan_id or None

    if req.hari         is not None: kelas.hari         = req.hari or None
    if req.slot_mulai   is not None: kelas.slot_mulai   = req.slot_mulai
    if req.slot_selesai is not None: kelas.slot_selesai = req.slot_selesai
    if req.kode_akses   is not None: kelas.kode_akses   = req.kode_akses or None
    if req.izin_tamu    is not None: kelas.izin_tamu    = req.izin_tamu
    if req.is_active    is not None: kelas.is_active    = req.is_active

    db.commit()
    db.refresh(kelas)

    return True, f"Kelas {kelas.kode_kelas} berhasil diperbarui", _kelas_to_dict(kelas)


# ── DELETE KELAS ──────────────────────────────────────────────

def delete_kelas(
    db           : Session,
    matakuliah_id: UUID,
    kelas_id     : UUID,
) -> Tuple[bool, str]:
    """
    Hapus kelas.
    Gagal jika masih ada mahasiswa terdaftar di kelas ini.
    """
    kelas = db.query(KelasMatakuliah).filter(
        KelasMatakuliah.id            == kelas_id,
        KelasMatakuliah.matakuliah_id == matakuliah_id,
    ).first()
    if not kelas:
        return False, "Kelas tidak ditemukan"

    # Cek mahasiswa yang enrolled dengan kelas_id ini
    enrolled = db.query(MahasiswaMatakuliah).filter(
        MahasiswaMatakuliah.kelas_id == kelas_id
    ).count()

    if enrolled > 0:
        return False, (
            f"Tidak dapat menghapus Kelas {kelas.kode_kelas} karena masih ada "
            f"{enrolled} mahasiswa terdaftar. Pindahkan atau hapus enrollment terlebih dahulu."
        )

    kode = kelas.kode_kelas
    db.delete(kelas)
    db.commit()
    return True, f"Kelas {kode} berhasil dihapus"


# ── TOGGLE IZIN TAMU PER KELAS ────────────────────────────────

def toggle_izin_tamu_kelas(
    db      : Session,
    kelas_id: UUID,
    izin    : bool,
) -> Tuple[bool, str, Optional[Dict]]:
    """
    Toggle izin_tamu per kelas (override dari izin_tamu matakuliah).
    Return: (success, pesan, kelas_dict | None)
    """
    kelas = db.query(KelasMatakuliah).filter(KelasMatakuliah.id == kelas_id).first()
    if not kelas:
        return False, "Kelas tidak ditemukan", None

    kelas.izin_tamu = izin
    db.commit()
    db.refresh(kelas)

    status = "diaktifkan" if izin else "dinonaktifkan"
    return True, f"Izin tamu Kelas {kelas.kode_kelas} berhasil {status}", _kelas_to_dict(kelas)


# ── MAHASISWA PER KELAS ───────────────────────────────────────

def get_mahasiswa_kelas(db: Session, kelas_id: UUID) -> Optional[Dict]:
    """
    List mahasiswa terdaftar di kelas tertentu.
    Pisahkan mahasiswa asli (is_tamu=False) dan tamu (is_tamu=True).
    """
    kelas = db.query(KelasMatakuliah).filter(KelasMatakuliah.id == kelas_id).first()
    if not kelas:
        return None

    rows = (
        db.query(MahasiswaMatakuliah)
        .filter(MahasiswaMatakuliah.kelas_id == kelas_id)
        .all()
    )

    mahasiswa_list = []
    for row in rows:
        mhs = row.mahasiswa
        if not mhs:
            continue
        mahasiswa_list.append({
            "mahasiswa_id" : str(mhs.id),
            "nim"          : mhs.nim_nidn,
            "nama_lengkap" : mhs.nama_lengkap,
            "email"        : mhs.email,
            "program_studi": mhs.program_studi,
            "is_active"    : mhs.is_active,
            "is_tamu"      : row.is_tamu,
            "kelas_asal"   : row.kelas_asal,
            "enrolled_at"  : row.created_at.isoformat() if row.created_at else None,
        })

    asli = [m for m in mahasiswa_list if not m["is_tamu"]]
    tamu = [m for m in mahasiswa_list if m["is_tamu"]]

    mk = kelas.matakuliah
    return {
        "kelas_id"       : str(kelas_id),
        "kode_kelas"     : kelas.kode_kelas,
        "matakuliah_id"  : str(kelas.matakuliah_id),
        "kode_mk"        : mk.kode if mk else "-",
        "nama_mk"        : mk.nama if mk else "-",
        "izin_tamu"      : kelas.izin_tamu,
        "total_asli"     : len(asli),
        "total_tamu"     : len(tamu),
        "mahasiswa_asli" : sorted(asli, key=lambda x: x["nama_lengkap"]),
        "mahasiswa_tamu" : sorted(tamu, key=lambda x: x["nama_lengkap"]),
    }


# ── ENROLL MAHASISWA KE KELAS ─────────────────────────────────

def enroll_mahasiswa_ke_kelas(
    db          : Session,
    kelas_id    : UUID,
    mahasiswa_id: UUID,
    is_tamu     : bool = False,
    kelas_asal  : Optional[str] = None,
) -> Tuple[bool, str]:
    """
    Daftarkan mahasiswa ke kelas tertentu.
    Otomatis juga mendaftarkan ke matakuliah (mahasiswa_matakuliah)
    jika belum terdaftar.
    """
    kelas = db.query(KelasMatakuliah).filter(KelasMatakuliah.id == kelas_id).first()
    if not kelas:
        return False, "Kelas tidak ditemukan"

    mhs = db.query(User).filter(
        User.id   == mahasiswa_id,
        User.role == UserRole.mahasiswa,
    ).first()
    if not mhs:
        return False, "Mahasiswa tidak ditemukan"

    # Cek sudah enrolled di kelas ini
    existing_kelas = db.query(MahasiswaMatakuliah).filter(
        MahasiswaMatakuliah.mahasiswa_id  == mahasiswa_id,
        MahasiswaMatakuliah.kelas_id      == kelas_id,
    ).first()
    if existing_kelas:
        return False, f"{mhs.nama_lengkap} sudah terdaftar di kelas ini"

    # Cek sudah enrolled di MK (mungkin di kelas lain atau legacy)
    existing_mk = db.query(MahasiswaMatakuliah).filter(
        MahasiswaMatakuliah.mahasiswa_id  == mahasiswa_id,
        MahasiswaMatakuliah.matakuliah_id == kelas.matakuliah_id,
    ).first()

    if existing_mk:
        # Sudah di MK, update kelas_id saja jika belum punya kelas
        if existing_mk.kelas_id is None:
            existing_mk.kelas_id = kelas_id
            db.commit()
            return True, f"{mhs.nama_lengkap} berhasil dipindahkan ke kelas ini"
        else:
            return False, f"{mhs.nama_lengkap} sudah terdaftar di kelas lain dalam MK ini"

    # Insert baru
    db.add(MahasiswaMatakuliah(
        mahasiswa_id  = mahasiswa_id,
        matakuliah_id = kelas.matakuliah_id,
        kelas_id      = kelas_id,
        is_tamu       = is_tamu,
        kelas_asal    = kelas_asal,
    ))
    db.commit()
    return True, f"{mhs.nama_lengkap} berhasil didaftarkan ke kelas ini"