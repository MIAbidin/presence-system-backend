# app/schemas/jadwal_pengganti.py
"""
Schema Pydantic untuk endpoint jadwal pengganti dan manajemen tamu.

Update Fase B-1:
- Tambah field mode (Optional[str]) di JadwalPenggantiRequest
- Tambah field mode (Optional[str]) di JadwalPenggantiResponse
- Validasi: mode harus 'offline', 'online', atau None

Dipakai di:
  - POST /dosen/matakuliah/{mk_id}/jadwal-pengganti
  - GET  /dosen/matakuliah/{mk_id}/jadwal-pengganti
  - PATCH /dosen/matakuliah/{mk_id}/izin-tamu
  - POST  /dosen/matakuliah/{mk_id}/tamu
  - DELETE /dosen/matakuliah/{mk_id}/tamu/{mahasiswa_id}
"""
from pydantic import BaseModel, Field, field_validator
from typing import Optional, Literal
from uuid import UUID
from datetime import time, datetime


# ─── JADWAL PENGGANTI ─────────────────────────────────────────

class JadwalPenggantiRequest(BaseModel):
    """Body request saat dosen simpan jadwal pengganti."""
    pertemuan_ke      : int   = Field(..., ge=1, le=16,
                                description="Pertemuan ke berapa yang diganti (1–16)")
    jam_mulai_baru    : Optional[str] = Field(None,
                                description="Jam mulai baru, format HH:MM, mis. 10:00")
    jam_selesai_baru  : Optional[str] = Field(None,
                                description="Jam selesai baru, format HH:MM, mis. 12:30")
    ruangan_baru      : Optional[str] = Field(None, max_length=50,
                                description="Ruangan baru, mis. C-202. Kosongkan jika tidak ganti.")
    keterangan        : Optional[str] = Field(None,
                                description="Keterangan, mis. Pindah karena ruang dipakai seminar")

    # ── Fase B-1: field mode baru ─────────────────────────────
    mode              : Optional[Literal["offline", "online"]] = Field(
        None,
        description=(
            "Mode pertemuan pengganti. "
            "Kosongkan / null = mode tidak berubah dari jadwal reguler kelas. "
            "'offline' = pertemuan ini berubah ke tatap muka. "
            "'online'  = pertemuan ini berubah ke online."
        ),
    )

    @field_validator('jam_mulai_baru', 'jam_selesai_baru', mode='before')
    @classmethod
    def validasi_format_jam(cls, v):
        """Pastikan format jam HH:MM sebelum disimpan."""
        if v is None:
            return v
        try:
            jam, menit = v.split(':')
            assert 0 <= int(jam) <= 23
            assert 0 <= int(menit) <= 59
            return v
        except Exception:
            raise ValueError(f"Format jam tidak valid: '{v}'. Gunakan HH:MM, mis. 08:30")

    @field_validator('jam_selesai_baru', mode='before')
    @classmethod
    def validasi_jam_selesai_lebih_besar(cls, v, info):
        """
        Validasi: jam_selesai_baru harus lebih besar dari jam_mulai_baru
        jika keduanya diisi.
        """
        if v is None:
            return v
        jam_mulai = info.data.get('jam_mulai_baru')
        if jam_mulai is None:
            return v
        try:
            h_m, m_m = jam_mulai.split(':')
            h_s, m_s = v.split(':')
            total_mulai   = int(h_m) * 60 + int(m_m)
            total_selesai = int(h_s) * 60 + int(m_s)
            if total_selesai <= total_mulai:
                raise ValueError(
                    f"jam_selesai_baru ({v}) harus lebih besar dari "
                    f"jam_mulai_baru ({jam_mulai})"
                )
        except ValueError as e:
            if "harus lebih besar" in str(e):
                raise
        return v

    class Config:
        json_schema_extra = {
            "example": {
                "pertemuan_ke"    : 5,
                "jam_mulai_baru"  : "10:00",
                "jam_selesai_baru": "12:30",
                "ruangan_baru"    : "C-202",
                "mode"            : "online",
                "keterangan"      : "Pindah ke online karena dosen dinas luar kota"
            }
        }


class JadwalPenggantiResponse(BaseModel):
    """Response setelah jadwal pengganti disimpan atau di-list."""
    id               : UUID
    matakuliah_id    : UUID
    pertemuan_ke     : int
    jam_mulai_baru   : Optional[str] = None   # format "HH:MM"
    jam_selesai_baru : Optional[str] = None
    ruangan_baru     : Optional[str] = None

    # ── Fase B-1: field mode di response ──────────────────────
    mode             : Optional[str] = None   # 'offline' | 'online' | null

    keterangan       : Optional[str] = None
    created_at       : datetime
    updated_at       : datetime

    class Config:
        from_attributes = True


# ─── IZIN TAMU ────────────────────────────────────────────────

class IzinTamuRequest(BaseModel):
    """Toggle izin tamu per matakuliah."""
    izin_tamu: bool = Field(
        ...,
        description=(
            "TRUE = mahasiswa kelas lain boleh presensi langsung tanpa izin. "
            "FALSE = hanya yang ada di daftar mahasiswa resmi + tamu manual."
        )
    )

    class Config:
        json_schema_extra = {"example": {"izin_tamu": True}}


class IzinTamuResponse(BaseModel):
    """Response setelah toggle izin tamu."""
    matakuliah_id : UUID
    nama          : str
    izin_tamu     : bool
    pesan         : str


# ─── MANAJEMEN TAMU MANUAL ────────────────────────────────────

class TambahTamuRequest(BaseModel):
    """
    Dosen tambah mahasiswa tamu dari kelas lain secara manual.
    Cukup input NIM — sistem cari otomatis dan tentukan kelas_asal.
    """
    nim: str = Field(..., min_length=8, max_length=20,
                     description="NIM mahasiswa yang mau diizinkan jadi tamu")

    class Config:
        json_schema_extra = {"example": {"nim": "2021001003"}}


class MahasiswaTamuResponse(BaseModel):
    """Info satu mahasiswa tamu dalam daftar."""
    mahasiswa_id : UUID
    nim          : str
    nama_lengkap : str
    program_studi: str
    is_tamu      : bool
    kelas_asal   : Optional[str] = None   # None jika mahasiswa asli


class DaftarMahasiswaResponse(BaseModel):
    """Response GET daftar mahasiswa per matakuliah (asli + tamu)."""
    matakuliah_id   : UUID
    nama_matakuliah : str
    izin_tamu       : bool
    total_asli      : int
    total_tamu      : int
    mahasiswa       : list[MahasiswaTamuResponse]