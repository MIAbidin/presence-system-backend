# app/schemas/home.py
from pydantic import BaseModel
from typing import Optional, List
from uuid import UUID
from datetime import time


# ─── Jadwal item ──────────────────────────────────────────────

class JadwalItem(BaseModel):
    """Satu matakuliah dalam jadwal hari ini / mingguan."""
    matakuliah_id   : UUID
    kode            : str
    nama            : str
    sks             : int
    hari            : Optional[str]  = None
    jam_mulai       : Optional[str]  = None   # "08:00"
    jam_selesai     : Optional[str]  = None   # "09:40"
    ruangan         : Optional[str]  = None

    # Status presensi hari ini (None jika bukan hari ini / belum ada sesi)
    status_presensi : Optional[str]  = None   # 'hadir'|'terlambat'|'absen'|None
    ada_sesi_aktif  : bool           = False
    sesi_id         : Optional[UUID] = None

    class Config:
        from_attributes = True


# ─── Home Summary ─────────────────────────────────────────────

class StatKehadiran(BaseModel):
    total_pertemuan     : int
    hadir               : int
    terlambat           : int
    absen               : int
    izin                : int
    sakit               : int
    hadir_efektif       : int
    persentase          : float   # 0.0 – 100.0


class SesiAktifInfo(BaseModel):
    sesi_id         : UUID
    matakuliah_nama : str
    mode            : str          # 'offline' | 'online'
    detik_tersisa   : Optional[int] = None
    pertemuan_ke    : int


class HomeSummaryResponse(BaseModel):
    nama_mahasiswa  : str
    nim             : str
    is_face_registered: bool

    # Statistik keseluruhan semester
    stat_semester   : StatKehadiran

    # Presensi hari ini
    presensi_hari_ini: int         # jumlah presensi yang sudah dilakukan hari ini

    # Jadwal hari ini (maks 5 item)
    jadwal_hari_ini  : List[JadwalItem]

    # Sesi yang sedang aktif untuk mahasiswa ini (bisa lebih dari 1)
    sesi_aktif       : List[SesiAktifInfo]
