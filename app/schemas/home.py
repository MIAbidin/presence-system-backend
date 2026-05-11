# app/schemas/home.py
from pydantic import BaseModel
from typing import Optional, List
from uuid import UUID
from datetime import time


# ─── Jadwal Pengganti Info (nested di JadwalItem) ─────────────

class JadwalPenggantiInfo(BaseModel):
    """
    Info ringkas jadwal pengganti yang disertakan dalam JadwalItem.

    Fase B-5: dipakai oleh JadwalScreen Flutter v2.1.0 untuk
    menampilkan banner kuning pada kartu jadwal yang punya jadwal pengganti.
    Banner berisi jam baru, ruangan baru, dan MODE baru (field Fase B-1).
    """
    pertemuan_ke     : int
    jam_mulai_baru   : Optional[str]  = None   # "10:00"
    jam_selesai_baru : Optional[str]  = None   # "12:30"
    ruangan_baru     : Optional[str]  = None
    # mode dari jadwal_pengganti (Fase B-1):
    # 'offline' | 'online' | None (tidak berubah dari reguler)
    mode             : Optional[str]  = None
    keterangan       : Optional[str]  = None


# ─── Jadwal item ──────────────────────────────────────────────

class JadwalItem(BaseModel):
    """
    Satu matakuliah dalam jadwal hari ini / mingguan mahasiswa.

    Update Fase B-5:
    - mode_efektif         : mode yang berlaku saat ini
                             (dari jadwal_pengganti.mode jika ada, else None)
    - has_jadwal_pengganti : True jika pertemuan berikutnya punya jadwal pengganti
    - jadwal_pengganti_info: detail perubahan (jam, ruangan, mode)
                             Nil jika has_jadwal_pengganti=False

    Flutter JadwalScreen menggunakan field ini untuk:
    - ModeBadge  → tampilkan badge Offline/Online per kartu jadwal
    - Banner kuning 'Jadwal Diganti' → muncul jika has_jadwal_pengganti=True
    - Banner berisi jam_mulai_baru, ruangan_baru, dan MODE baru
    """
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

    # ── Fase B-5: Mode efektif & info jadwal pengganti ────────
    # mode_efektif: mode yang berlaku untuk sesi berikutnya.
    #   Diambil dari jadwal_pengganti.mode jika ada, else None.
    #   None berarti mode tidak ditetapkan / ikut mode reguler kelas.
    mode_efektif          : Optional[str]  = None   # 'offline'|'online'|None

    # has_jadwal_pengganti: True jika pertemuan berikutnya punya jadwal pengganti.
    # Flutter menampilkan banner kuning jika True.
    has_jadwal_pengganti  : bool           = False

    # jadwal_pengganti_info: detail perubahan (jam baru, ruangan baru, mode baru).
    # None jika has_jadwal_pengganti=False.
    jadwal_pengganti_info : Optional[JadwalPenggantiInfo] = None

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