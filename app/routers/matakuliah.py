# app/routers/matakuliah.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from uuid import UUID

from app.database.db import get_db
from app.models.user import User, UserRole
from app.models.matakuliah import Matakuliah
from app.models.mahasiswa_matakuliah import MahasiswaMatakuliah
from app.models.sesi import SesiPresensi, SesiStatus
from app.routers.auth import get_current_user

router = APIRouter(prefix="/matakuliah", tags=["Matakuliah"])


@router.get("/saya")
def get_matakuliah_saya(
    current_user: User    = Depends(get_current_user),
    db          : Session = Depends(get_db),
):
    """
    Dosen  → matakuliah yang pernah dibuat sesinya (atau semua jika belum pernah).
    Mahasiswa → redirect ke /mahasiswa/matakuliah (atau langsung return juga OK).
    Admin  → semua matakuliah.
    """
    if current_user.role == UserRole.mahasiswa:
        # Ambil dari tabel relasi
        rows = db.query(MahasiswaMatakuliah).filter(
            MahasiswaMatakuliah.mahasiswa_id == current_user.id
        ).all()
        mk_ids  = [r.matakuliah_id for r in rows]
        mk_list = db.query(Matakuliah).filter(Matakuliah.id.in_(mk_ids)).all() if mk_ids else []

    elif current_user.role == UserRole.dosen:
        sesi_list = db.query(SesiPresensi).filter(
            SesiPresensi.dosen_id == current_user.id
        ).all()
        mk_ids = list({s.matakuliah_id for s in sesi_list})
        mk_list = (
            db.query(Matakuliah).filter(Matakuliah.id.in_(mk_ids)).all()
            if mk_ids
            else db.query(Matakuliah).all()
        )
    else:
        mk_list = db.query(Matakuliah).all()

    return [
        {
            "id"           : str(mk.id),
            "kode"         : mk.kode,
            "nama"         : mk.nama,
            "sks"          : mk.sks,
            "hari"         : mk.hari,
            "jam_mulai"    : mk.jam_mulai.strftime("%H:%M") if mk.jam_mulai else None,
            "jam_selesai"  : mk.jam_selesai.strftime("%H:%M") if mk.jam_selesai else None,
            "ruangan"      : mk.ruangan,
        }
        for mk in mk_list
    ]


@router.get("/semua")
def get_semua_matakuliah(
    db: Session = Depends(get_db),
    _: User     = Depends(get_current_user),
):
    """Semua matakuliah (untuk admin / dropdown buka sesi)."""
    mk_list = db.query(Matakuliah).all()
    return [
        {
            "id"            : str(mk.id),
            "kode"          : mk.kode,
            "nama"          : mk.nama,
            "sks"           : mk.sks,
            "hari"          : mk.hari,
            "jam_mulai"     : mk.jam_mulai.strftime("%H:%M") if mk.jam_mulai else None,
            "jam_selesai"   : mk.jam_selesai.strftime("%H:%M") if mk.jam_selesai else None,
            "ruangan"       : mk.ruangan,
            "koordinat_lat" : mk.koordinat_lat,
            "koordinat_lng" : mk.koordinat_lng,
        }
        for mk in mk_list
    ]


# ── Admin: daftarkan mahasiswa ke matakuliah ──────────────────

@router.post("/{mk_id}/enroll/{mahasiswa_id}")
def admin_enroll(
    mk_id        : UUID,
    mahasiswa_id : UUID,
    current_user : User    = Depends(get_current_user),
    db           : Session = Depends(get_db),
):
    """Admin mendaftarkan mahasiswa ke sebuah matakuliah."""
    if current_user.role not in [UserRole.admin, UserRole.dosen]:
        raise HTTPException(status_code=403, detail="Hanya admin/dosen yang bisa mendaftarkan mahasiswa")

    mk = db.query(Matakuliah).filter(Matakuliah.id == mk_id).first()
    if not mk:
        raise HTTPException(status_code=404, detail="Matakuliah tidak ditemukan")

    existing = db.query(MahasiswaMatakuliah).filter(
        MahasiswaMatakuliah.mahasiswa_id  == mahasiswa_id,
        MahasiswaMatakuliah.matakuliah_id == mk_id,
    ).first()
    if existing:
        return {"message": "Mahasiswa sudah terdaftar"}

    db.add(MahasiswaMatakuliah(mahasiswa_id=mahasiswa_id, matakuliah_id=mk_id))
    db.commit()
    return {"message": f"Berhasil mendaftarkan mahasiswa ke {mk.nama}"}


# ── Admin: bulk enroll semua mahasiswa ke satu matakuliah ─────

@router.post("/{mk_id}/enroll-bulk")
def admin_enroll_bulk(
    mk_id        : UUID,
    mahasiswa_ids: list[UUID],
    current_user : User    = Depends(get_current_user),
    db           : Session = Depends(get_db),
):
    """Daftarkan banyak mahasiswa sekaligus ke sebuah matakuliah."""
    if current_user.role not in [UserRole.admin, UserRole.dosen]:
        raise HTTPException(status_code=403, detail="Hanya admin/dosen")

    mk = db.query(Matakuliah).filter(Matakuliah.id == mk_id).first()
    if not mk:
        raise HTTPException(status_code=404, detail="Matakuliah tidak ditemukan")

    added = 0
    for mhs_id in mahasiswa_ids:
        existing = db.query(MahasiswaMatakuliah).filter(
            MahasiswaMatakuliah.mahasiswa_id  == mhs_id,
            MahasiswaMatakuliah.matakuliah_id == mk_id,
        ).first()
        if not existing:
            db.add(MahasiswaMatakuliah(mahasiswa_id=mhs_id, matakuliah_id=mk_id))
            added += 1

    db.commit()
    return {"message": f"{added} mahasiswa berhasil didaftarkan ke {mk.nama}"}
