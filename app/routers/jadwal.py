# app/routers/jadwal.py
"""
Endpoint jadwal mahasiswa:
  GET /jadwal/hari-ini   — jadwal + status presensi hari ini
  GET /jadwal/mingguan   — jadwal seminggu penuh
  GET /jadwal/hari/{nama_hari} — jadwal hari tertentu

Update Fase B-5:
  Semua response sekarang menyertakan:
    - mode_efektif          : mode yang berlaku (dari jadwal_pengganti.mode jika ada)
    - has_jadwal_pengganti  : True jika pertemuan berikutnya punya jadwal pengganti
    - jadwal_pengganti_info : detail perubahan (jam, ruangan, mode baru)

  Flutter JadwalScreen menggunakan field ini untuk:
    - Badge mode (ModeBadge widget) di setiap kartu jadwal
    - Banner kuning 'Jadwal Diganti' (muncul jika has_jadwal_pengganti=True)
    - Banner berisi jam baru, ruangan baru, dan MODE baru
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

HARI_VALID = ["Senin", "Selasa", "Rabu", "Kamis", "Jumat", "Sabtu", "Minggu"]


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
    - `ada_sesi_aktif`        : apakah dosen sudah membuka sesi
    - `sesi_id`               : UUID sesi jika aktif
    - `status_presensi`       : status mahasiswa di sesi hari ini
    - `mode_efektif`          : mode yang berlaku ('offline'|'online'|null)
                                Berasal dari jadwal_pengganti.mode jika ada,
                                null berarti mode tidak ditetapkan secara khusus.
    - `has_jadwal_pengganti`  : True jika pertemuan berikutnya ada jadwal pengganti
    - `jadwal_pengganti_info` : detail perubahan jam, ruangan, dan mode baru
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

    Fase B-5: setiap item jadwal menyertakan mode_efektif,
    has_jadwal_pengganti, dan jadwal_pengganti_info.

    Response format:
    ```json
    {
      "Senin": [
        {
          "matakuliah_id": "...",
          "nama": "Pemrograman Mobile",
          "kode": "TIF3232209",
          "mode_efektif": "online",
          "has_jadwal_pengganti": true,
          "jadwal_pengganti_info": {
            "pertemuan_ke": 10,
            "jam_mulai_baru": "10:00",
            "jam_selesai_baru": "12:30",
            "ruangan_baru": "C-202",
            "mode": "online",
            "keterangan": "Pindah ke online karena dosen dinas"
          },
          ...
        }
      ],
      "Selasa": [...],
      ...
    }
    ```
    Hari tanpa jadwal dikembalikan sebagai list kosong.
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

    Fase B-5: response menyertakan mode_efektif, has_jadwal_pengganti,
    dan jadwal_pengganti_info sama seperti endpoint hari-ini dan mingguan.
    """
    nama_hari = nama_hari.capitalize()
    if nama_hari not in HARI_VALID:
        raise HTTPException(
            status_code=400,
            detail=f"Nama hari tidak valid. Pilih dari: {', '.join(HARI_VALID)}"
        )

    # Gunakan helper di home_service yang sudah include Fase B-5
    return home_service.get_jadwal_per_hari(db, mahasiswa.id, nama_hari)