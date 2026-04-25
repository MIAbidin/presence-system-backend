# app/routers/jadwal.py
"""
Endpoint jadwal mahasiswa:
  GET /jadwal/hari-ini   — jadwal + status presensi hari ini
  GET /jadwal/mingguan   — jadwal seminggu penuh
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from app.database.db import get_db
from app.models.user import User, UserRole
from app.routers.auth import get_current_user
from app.services import home_service
from app.schemas.home import JadwalItem

router = APIRouter(prefix="/jadwal", tags=["Jadwal"])


def require_mahasiswa(current_user: User = Depends(get_current_user)):
    if current_user.role != UserRole.mahasiswa:
        raise HTTPException(status_code=403, detail="Endpoint ini hanya untuk mahasiswa")
    return current_user


# ─── GET /jadwal/hari-ini ─────────────────────────────────────

@router.get("/hari-ini", response_model=List[JadwalItem])
def jadwal_hari_ini(
    mahasiswa : User    = Depends(require_mahasiswa),
    db        : Session = Depends(get_db),
):
    """
    Jadwal matakuliah mahasiswa untuk hari ini.

    Setiap item dilengkapi:
    - `ada_sesi_aktif`  : apakah dosen sudah membuka sesi
    - `sesi_id`         : UUID sesi jika aktif (langsung bisa dipakai untuk presensi)
    - `status_presensi` : status mahasiswa di sesi hari ini (null jika belum presensi)
    """
    return home_service.get_jadwal_hari_ini(db, mahasiswa.id)


# ─── GET /jadwal/mingguan ─────────────────────────────────────

@router.get("/mingguan")
def jadwal_mingguan(
    mahasiswa : User    = Depends(require_mahasiswa),
    db        : Session = Depends(get_db),
):
    """
    Jadwal seminggu penuh dikelompokkan per hari.

    Response format:
    ```json
    {
      "Senin"  : [{ matakuliah_id, nama, jam_mulai, ... }, ...],
      "Selasa" : [...],
      ...
    }
    ```
    Hari tanpa jadwal tetap dikembalikan sebagai list kosong.
    """
    return home_service.get_jadwal_mingguan(db, mahasiswa.id)


# ─── GET /jadwal/hari/{nama_hari} ────────────────────────────

@router.get("/hari/{nama_hari}", response_model=List[JadwalItem])
def jadwal_per_hari(
    nama_hari : str,
    mahasiswa : User    = Depends(require_mahasiswa),
    db        : Session = Depends(get_db),
):
    """
    Jadwal untuk hari tertentu.
    `nama_hari` harus salah satu dari: Senin, Selasa, Rabu, Kamis, Jumat, Sabtu, Minggu.
    """
    hari_valid = ["Senin", "Selasa", "Rabu", "Kamis", "Jumat", "Sabtu", "Minggu"]
    # Normalize capitalization
    nama_hari = nama_hari.capitalize()
    if nama_hari not in hari_valid:
        raise HTTPException(
            status_code=400,
            detail=f"Nama hari tidak valid. Pilih dari: {', '.join(hari_valid)}"
        )

    from app.models.matakuliah import Matakuliah
    from app.models.mahasiswa_matakuliah import MahasiswaMatakuliah

    rows = (
        db.query(MahasiswaMatakuliah)
        .filter(MahasiswaMatakuliah.mahasiswa_id == mahasiswa.id)
        .all()
    )
    if not rows:
        return []

    mk_ids = [r.matakuliah_id for r in rows]
    matakuliah_list = (
        db.query(Matakuliah)
        .filter(Matakuliah.id.in_(mk_ids), Matakuliah.hari == nama_hari)
        .all()
    )

    result = []
    for mk in matakuliah_list:
        result.append(JadwalItem(
            matakuliah_id = mk.id,
            kode          = mk.kode,
            nama          = mk.nama,
            sks           = mk.sks,
            hari          = mk.hari,
            jam_mulai     = mk.jam_mulai.strftime("%H:%M") if mk.jam_mulai else None,
            jam_selesai   = mk.jam_selesai.strftime("%H:%M") if mk.jam_selesai else None,
            ruangan       = mk.ruangan,
        ))

    result.sort(key=lambda x: x.jam_mulai or "99:99")
    return result
