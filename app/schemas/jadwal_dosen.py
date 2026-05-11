# app/schemas/jadwal_dosen.py
"""
Schema Pydantic untuk endpoint jadwal mingguan dosen (Fase B-4).

Dipakai oleh JadwalDosenScreen Flutter v2.1.0 — screen baru yang
menampilkan jadwal dosen per hari (Tab Hari Ini + Tab Mingguan).

Beranda dosen (GET /dosen/beranda) hanya menampilkan jadwal HARI INI.
Endpoint baru GET /dosen/jadwal/mingguan menampilkan SEMUA HARI dalam
seminggu, dikelompokkan per hari, lengkap dengan info kelas, slot waktu,
ruangan, jumlah mahasiswa, status sesi, dan jadwal pengganti.

Perubahan dari Fase B-1 sudah dimasukkan:
- field mode di JadwalPenggantiInfoItem (override mode per pertemuan)
"""
from pydantic import BaseModel
from typing import Optional, List
from uuid import UUID
from datetime import datetime


# ── Sub-schema: Info jadwal pengganti ────────────────────────

class JadwalPenggantiInfoItem(BaseModel):
    """
    Info jadwal pengganti yang relevan untuk tampilan di JadwalDosenScreen.
    Dipakai sebagai nested field di JadwalMingguanDosenItem.

    Jika ada jadwal pengganti untuk pertemuan yang sedang aktif atau
    akan datang, Flutter menampilkan banner kuning di kartu jadwal
    berisi perubahan yang terjadi (jam, ruangan, mode).
    """
    jp_id            : UUID
    pertemuan_ke     : int
    jam_mulai_baru   : Optional[str]  = None   # "10:00"
    jam_selesai_baru : Optional[str]  = None   # "12:30"
    ruangan_baru     : Optional[str]  = None
    # Fase B-1: mode pengganti — null = tidak berubah dari reguler
    mode             : Optional[str]  = None   # 'offline' | 'online' | null
    keterangan       : Optional[str]  = None

    class Config:
        from_attributes = True


# ── Schema utama: satu item jadwal per kelas ─────────────────

class JadwalMingguanDosenItem(BaseModel):
    """
    Satu kelas yang diampu dosen dalam jadwal mingguan.

    Satu matakuliah bisa muncul beberapa kali (satu per kelas A/B/C)
    jika dosen mengampu lebih dari satu kelas untuk MK yang sama.

    Flutter JadwalDosenScreen menampilkan ini sebagai kartu per kelas,
    dikelompokkan per hari. Setiap kartu menampilkan:
    - Nama MK + kode kelas (badge)
    - Slot dan jam (07:00 – 09:30)
    - Nama ruangan
    - Jumlah mahasiswa enrolled
    - Status sesi (aktif/belum_dibuka/selesai hari ini)
    - Banner jadwal pengganti jika ada (termasuk mode baru)
    - Tombol buka sesi langsung dari kartu
    """
    # ── Identitas kelas ──────────────────────────────────────
    kelas_id         : UUID
    kode_kelas       : str             # 'A' | 'B' | 'C' | 'X'
    matakuliah_id    : UUID
    matakuliah_kode  : str
    matakuliah_nama  : str
    sks              : int

    # ── Jadwal ───────────────────────────────────────────────
    hari             : Optional[str]  = None   # 'Senin' dst
    slot_mulai       : Optional[int]  = None   # 1–12
    slot_selesai     : Optional[int]  = None   # 1–12
    jam_mulai        : Optional[str]  = None   # "07:00"
    jam_selesai      : Optional[str]  = None   # "09:30"
    jam_range        : Optional[str]  = None   # "07:00 – 09:30"

    # ── Ruangan ──────────────────────────────────────────────
    ruangan_id       : Optional[UUID] = None
    kode_ruangan     : Optional[str]  = None
    nama_ruangan     : Optional[str]  = None
    koordinat_lat    : Optional[float] = None
    koordinat_lng    : Optional[float] = None

    # ── Statistik mahasiswa ───────────────────────────────────
    jumlah_mahasiswa : int = 0         # total enrolled di kelas ini (asli + tamu)
    jumlah_tamu      : int = 0         # dari is_tamu=True

    # ── Status sesi (hanya relevan untuk hari ini) ────────────
    # 'aktif'        → sesi sedang berlangsung, bisa lihat peserta
    # 'selesai'      → sesi sudah ditutup hari ini
    # 'belum_dibuka' → dosen belum buka sesi (bisa tap untuk buka)
    # null           → hari ini bukan hari jadwal kelas ini
    status_sesi      : Optional[str]  = None
    sesi_id          : Optional[UUID] = None   # ada jika aktif atau selesai hari ini
    pertemuan_ke_berikutnya : int      = 1     # pertemuan berikutnya yang akan dibuka

    # ── Jadwal pengganti (jika ada untuk pertemuan berikutnya) ─
    # Flutter menampilkan banner kuning jika field ini terisi.
    ada_jadwal_pengganti : bool = False
    jadwal_pengganti     : Optional[JadwalPenggantiInfoItem] = None

    # ── Izin tamu ────────────────────────────────────────────
    izin_tamu        : bool = False

    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "kelas_id"       : "uuid-kelas",
                "kode_kelas"     : "A",
                "matakuliah_id"  : "uuid-mk",
                "matakuliah_kode": "TIF3232209",
                "matakuliah_nama": "Pemrograman Mobile",
                "sks"            : 3,
                "hari"           : "Senin",
                "slot_mulai"     : 7,
                "slot_selesai"   : 9,
                "jam_mulai"      : "13:00",
                "jam_selesai"    : "15:30",
                "jam_range"      : "13:00 – 15:30",
                "kode_ruangan"   : "LABMOBILE",
                "nama_ruangan"   : "Lab Mobile Computing",
                "jumlah_mahasiswa": 15,
                "jumlah_tamu"    : 1,
                "status_sesi"    : "belum_dibuka",
                "sesi_id"        : None,
                "pertemuan_ke_berikutnya": 10,
                "ada_jadwal_pengganti": False,
                "jadwal_pengganti": None,
                "izin_tamu"      : True,
            }
        }


# ── Response wrapper: jadwal dikelompokkan per hari ──────────

HARI_ORDER = ["Senin", "Selasa", "Rabu", "Kamis", "Jumat", "Sabtu", "Minggu"]


class JadwalMingguanDosenResponse(BaseModel):
    """
    Response GET /dosen/jadwal/mingguan.

    Jadwal dikelompokkan per hari, diurutkan dari Senin hingga Minggu.
    Hari tanpa jadwal tetap ada tapi dengan list kosong.

    Flutter JadwalDosenScreen menggunakan struktur ini untuk:
    - Tab Hari Ini: filter jadwal_per_hari[hari_ini]
    - Tab Mingguan: render semua hari dengan accordion/section per hari

    Informasi tambahan:
    - hari_ini: nama hari sekarang (WIB) untuk filter tab
    - total_kelas: jumlah kelas yang diampu dosen dalam seminggu
    - total_sesi_aktif: jumlah sesi yang sedang aktif sekarang
    """
    nama_dosen       : str
    nidn             : str
    hari_ini         : str             # 'Senin' | 'Selasa' dst (WIB)
    total_kelas      : int
    total_sesi_aktif : int

    # Dict: hari → list kelas. Semua 7 hari selalu ada (bisa list kosong).
    jadwal_per_hari  : dict[str, List[JadwalMingguanDosenItem]]

    class Config:
        json_schema_extra = {
            "example": {
                "nama_dosen"      : "Dr. Ir. Budi Santoso, M.T.",
                "nidn"            : "0012038901",
                "hari_ini"        : "Senin",
                "total_kelas"     : 4,
                "total_sesi_aktif": 1,
                "jadwal_per_hari" : {
                    "Senin"  : ["... list JadwalMingguanDosenItem ..."],
                    "Selasa" : [],
                    "Rabu"   : [],
                    "Kamis"  : ["... list JadwalMingguanDosenItem ..."],
                    "Jumat"  : [],
                    "Sabtu"  : [],
                    "Minggu" : [],
                },
            }
        }