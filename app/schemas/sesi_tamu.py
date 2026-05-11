# app/schemas/sesi_tamu.py
"""
Schema Pydantic untuk endpoint GET /sesi/aktif-tamu (Fase B-3).

Dipakai oleh TamuSesiListScreen di Flutter v2.1.0.
Dipanggil saat mahasiswa tap 'Ikut sebagai Tamu' di ScanScreen
ketika tidak ada sesi aktif yang cocok dengan jadwalnya sendiri.

Sesi muncul di list jika memenuhi SALAH SATU syarat:
  1. Dosen sudah daftarkan mahasiswa ini secara manual (is_tamu=True)
     → izin_tamu_source = 'manual'
  2. Kelas / matakuliah memiliki izin_tamu=True
     → izin_tamu_source = 'auto'

Sesi TIDAK muncul jika:
  - Mahasiswa sudah enrolled sebagai mahasiswa ASLI di MK tersebut
    (gunakan alur presensi normal via GET /sesi/aktif-mahasiswa)
  - Mahasiswa sudah punya record presensi di sesi ini
  - Role bukan mahasiswa (dosen/admin mendapat list kosong)
"""
from pydantic import BaseModel
from typing import Optional, List
from uuid import UUID
from datetime import datetime


class SesiTamuItem(BaseModel):
    """
    Satu sesi aktif yang tersedia untuk diikuti mahasiswa sebagai tamu.

    Flutter TamuSesiListScreen menampilkan list ini sebagai kartu-kartu
    yang bisa di-tap mahasiswa untuk memilih sesi mana yang akan diikuti.

    Setelah mahasiswa tap:
    - mode='offline' → navigasi ke ScanScreen dengan sesi_id preset
    - mode='online'  → navigasi ke KodeSesiScreen dengan sesi_id preset
    """

    # ── Identitas sesi ──────────────────────────────────────
    sesi_id         : UUID
    mode            : str           # 'offline' | 'online'
    pertemuan_ke    : int
    waktu_buka      : Optional[datetime] = None

    # ── Info matakuliah ─────────────────────────────────────
    matakuliah_id   : UUID
    matakuliah_nama : str
    matakuliah_kode : str

    # ── Info kelas (Fase B) ─────────────────────────────────
    kelas_id        : Optional[UUID] = None
    kode_kelas      : Optional[str]  = None   # 'A' | 'B' | 'C' | None

    # ── Info dosen ──────────────────────────────────────────
    dosen_nama      : Optional[str]  = None

    # ── Info ruangan / jadwal ────────────────────────────────
    # Diambil dari kelas_matakuliah (via ruangan FK) atau fallback ke
    # field string matakuliah.ruangan untuk backward compatibility.
    ruangan         : Optional[str]  = None   # nama ruangan
    jam_mulai       : Optional[str]  = None   # "07:00" (dari slot mapping)
    jam_selesai     : Optional[str]  = None   # "09:30"
    hari            : Optional[str]  = None   # "Senin", "Selasa", dst

    # ── Koordinat GPS (untuk mode offline) ──────────────────
    # Diambil dari ruangan.koordinat_lat/lng atau fallback ke
    # matakuliah.koordinat_lat/lng untuk GPS validation offline.
    koordinat_lat   : Optional[float] = None
    koordinat_lng   : Optional[float] = None

    # ── Sumber izin ─────────────────────────────────────────
    # 'manual' → dosen daftarkan mahasiswa secara eksplisit (tampil lebih atas)
    # 'auto'   → kelas/matakuliah membuka izin tamu untuk semua
    izin_tamu_source: str = "auto"   # 'manual' | 'auto'

    # ── Countdown (khusus online) ────────────────────────────
    detik_tersisa   : Optional[int]  = None   # None untuk offline

    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "sesi_id"        : "uuid-sesi",
                "mode"           : "offline",
                "pertemuan_ke"   : 10,
                "waktu_buka"     : "2026-05-11T07:05:00Z",
                "matakuliah_id"  : "uuid-mk",
                "matakuliah_nama": "Kecerdasan Buatan",
                "matakuliah_kode": "TIF4011401",
                "kelas_id"       : "uuid-kelas",
                "kode_kelas"     : "A",
                "dosen_nama"     : "Prof. Dr. Hendra Gunawan, M.Kom.",
                "ruangan"        : "Lab Kecerdasan Artifisial",
                "jam_mulai"      : "07:00",
                "jam_selesai"    : "09:30",
                "hari"           : "Rabu",
                "koordinat_lat"  : -5.130650,
                "koordinat_lng"  : 119.488840,
                "izin_tamu_source": "manual",
                "detik_tersisa"  : None,
            }
        }


class SesiTamuListResponse(BaseModel):
    """
    Response wrapper untuk GET /sesi/aktif-tamu.

    Selalu HTTP 200 — tidak pernah 404.
    sesi_list kosong jika tidak ada sesi yang tersedia.

    Flutter logic:
    - Jika sesi_list kosong → tampilkan empty state:
      "Tidak ada sesi yang tersedia. Minta dosen untuk menambahkan
       Anda sebagai tamu atau tunggu dosen membuka izin tamu."
    - Jika ada item → tampilkan sebagai list kartu yang bisa di-tap

    Sesi dengan izin_tamu_source='manual' ditampilkan lebih atas
    (sudah diurutkan di service layer).
    """
    sesi_list : List[SesiTamuItem]
    total     : int
    pesan     : Optional[str] = None   # pesan tambahan jika diperlukan

    class Config:
        json_schema_extra = {
            "example": {
                "sesi_list": [
                    {
                        "sesi_id"        : "uuid-sesi-1",
                        "mode"           : "offline",
                        "pertemuan_ke"   : 10,
                        "matakuliah_nama": "Kecerdasan Buatan",
                        "matakuliah_kode": "TIF4011401",
                        "kode_kelas"     : "A",
                        "dosen_nama"     : "Prof. Dr. Hendra Gunawan, M.Kom.",
                        "ruangan"        : "Lab Kecerdasan Artifisial",
                        "jam_mulai"      : "07:00",
                        "jam_selesai"    : "09:30",
                        "hari"           : "Rabu",
                        "izin_tamu_source": "manual",
                        "detik_tersisa"  : None,
                    }
                ],
                "total": 1,
                "pesan": None,
            }
        }