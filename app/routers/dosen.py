"""
app/routers/dosen.py
══════════════════════
Fase 3 — Endpoint khusus dosen:

  3.1  GET  /dosen/beranda                          — jadwal hari ini + status sesi
  3.2  GET  /dosen/matakuliah/{mk_id}               — detail matakuliah lengkap
  3.3  PATCH /dosen/matakuliah/{mk_id}/izin-tamu    — toggle izin tamu on/off
  3.4a POST  /dosen/matakuliah/{mk_id}/tamu         — tambah tamu manual via NIM
  3.4b DELETE /dosen/matakuliah/{mk_id}/tamu/{mhs_id} — hapus akses tamu
  3.5a POST  /dosen/matakuliah/{mk_id}/jadwal-pengganti — simpan/update jadwal pengganti
  3.5b GET   /dosen/matakuliah/{mk_id}/jadwal-pengganti — list jadwal pengganti
  3.5c DELETE /dosen/matakuliah/{mk_id}/jadwal-pengganti/{pertemuan_ke} — hapus

Semua endpoint wajib autentikasi JWT dengan role dosen.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from uuid import UUID

from app.database.db import get_db
from app.models.user import User, UserRole
from app.routers.auth import get_current_user
from app.schemas.jadwal_pengganti import (
    JadwalPenggantiRequest,
    IzinTamuRequest,
    TambahTamuRequest,
)
from app.services import dosen_service

router = APIRouter(prefix="/dosen", tags=["Dosen"])


# ── Dependency: pastikan role dosen ───────────────────────────

def require_dosen(current_user: User = Depends(get_current_user)) -> User:
    if current_user.role != UserRole.dosen:
        raise HTTPException(
            status_code=403,
            detail="Endpoint ini hanya untuk dosen"
        )
    return current_user


# ─── 3.1 — GET /dosen/beranda ────────────────────────────────

@router.get("/beranda")
def get_beranda(
    dosen: User    = Depends(require_dosen),
    db   : Session = Depends(get_db),
):
    """
    Beranda dosen — satu hit untuk semua data yang dibutuhkan:
    - Jadwal hari ini dengan status sesi (belum_mulai / aktif / selesai)
    - Semua matakuliah yang diampu untuk section daftar lengkap

    Flutter hit endpoint ini sekali saat halaman beranda dibuka.
    """
    data = dosen_service.get_beranda_dosen(db, dosen)
    return data


# ─── 3.2 — GET /dosen/matakuliah/{mk_id} ─────────────────────

@router.get("/matakuliah/{mk_id}")
def get_detail_matakuliah(
    mk_id: UUID,
    dosen: User    = Depends(require_dosen),
    db   : Session = Depends(get_db),
):
    """
    Detail lengkap satu matakuliah:
    - Info matakuliah (jadwal reguler, koordinat GPS, toggle izin_tamu)
    - Daftar mahasiswa (asli dan tamu) dengan label kelas asal
    - Jadwal pengganti yang pernah dibuat dosen ini
    - Riwayat sesi 10 terakhir dengan ringkasan kehadiran

    Dipakai oleh halaman DetailMatakuliahScreen di Flutter dosen.
    """
    data = dosen_service.get_detail_matakuliah(db, dosen, mk_id)
    if not data:
        raise HTTPException(status_code=404, detail="Matakuliah tidak ditemukan")
    return data


# ─── 3.3 — PATCH /dosen/matakuliah/{mk_id}/izin-tamu ─────────

@router.patch("/matakuliah/{mk_id}/izin-tamu")
def toggle_izin_tamu(
    mk_id: UUID,
    req  : IzinTamuRequest,
    dosen: User    = Depends(require_dosen),
    db   : Session = Depends(get_db),
):
    """
    Toggle izin tamu per matakuliah.

    izin_tamu = true  → Mahasiswa dari kelas lain boleh presensi langsung
                        tanpa perlu diizinkan manual oleh dosen.
                        Saat scan wajah berhasil, sistem otomatis insert
                        mereka ke mahasiswa_matakuliah dengan flag is_tamu=TRUE.

    izin_tamu = false → Hanya mahasiswa terdaftar (asli + tamu manual) yang bisa
                        presensi. Mahasiswa lain ditolak dengan pesan jelas.

    Endpoint ini HANYA mengubah toggle. Tidak mengubah daftar mahasiswa yang
    sudah terdaftar (baik asli maupun tamu).
    """
    data = dosen_service.toggle_izin_tamu(db, mk_id, req.izin_tamu)
    if not data:
        raise HTTPException(status_code=404, detail="Matakuliah tidak ditemukan")
    return data


# ─── 3.4a — POST /dosen/matakuliah/{mk_id}/tamu ──────────────

@router.post("/matakuliah/{mk_id}/tamu", status_code=201)
def tambah_tamu(
    mk_id: UUID,
    req  : TambahTamuRequest,
    dosen: User    = Depends(require_dosen),
    db   : Session = Depends(get_db),
):
    """
    Dosen tambah mahasiswa tamu secara manual berdasarkan NIM.

    Cara kerja:
    1. Sistem cari mahasiswa berdasarkan NIM
    2. Cek sudah terdaftar atau belum
    3. Cari kelas asal mahasiswa otomatis dari matakuliah pertama yang bukan tamu
    4. Insert ke mahasiswa_matakuliah dengan is_tamu=TRUE dan kelas_asal terisi

    Dipakai saat dosen tap "Tambah Tamu Manual" di halaman Detail Matakuliah.
    """
    success, pesan, data = dosen_service.tambah_tamu_manual(db, mk_id, req.nim)
    if not success:
        raise HTTPException(status_code=400, detail=pesan)
    return {"message": pesan, "data": data}


# ─── 3.4b — DELETE /dosen/matakuliah/{mk_id}/tamu/{mhs_id} ───

@router.delete("/matakuliah/{mk_id}/tamu/{mahasiswa_id}")
def hapus_tamu(
    mk_id       : UUID,
    mahasiswa_id: UUID,
    dosen       : User    = Depends(require_dosen),
    db          : Session = Depends(get_db),
):
    """
    Hapus akses tamu mahasiswa dari matakuliah.

    Catatan penting:
    - Hanya bisa hapus mahasiswa yang is_tamu = TRUE.
    - Mahasiswa asli kelas tidak bisa dihapus lewat endpoint ini
      (harus melalui admin kampus).
    - Riwayat presensi mahasiswa tamu tersebut TIDAK dihapus,
      hanya akses ke depannya yang dicabut.
    """
    success, pesan = dosen_service.hapus_tamu(db, mk_id, mahasiswa_id)
    if not success:
        raise HTTPException(status_code=400, detail=pesan)
    return {"message": pesan}


# ─── 3.5a — POST /dosen/matakuliah/{mk_id}/jadwal-pengganti ──

@router.post("/matakuliah/{mk_id}/jadwal-pengganti", status_code=201)
def simpan_jadwal_pengganti(
    mk_id: UUID,
    req  : JadwalPenggantiRequest,
    dosen: User    = Depends(lambda: None),   # placeholder — gunakan Depends asli di router
    db   : Session = Depends(get_db),
):
    """
    Simpan jadwal pengganti untuk satu pertemuan tertentu.
 
    Kalau untuk pertemuan_ke yang sama sudah ada → otomatis UPDATE.
    Kalau belum ada → INSERT baru.
 
    Update Fase B-1:
    - Field mode (Optional: 'offline' | 'online' | null) ditambahkan
    - null/kosong = mode tidak berubah dari jadwal reguler kelas
    - 'online' = pertemuan ini berubah ke online meski jadwal reguler offline
    - 'offline' = pertemuan ini berubah ke tatap muka meski jadwal reguler online
    - Validasi: jam_selesai_baru harus lebih besar dari jam_mulai_baru (divalidasi di schema)
 
    Minimal satu kolom perubahan harus diisi (jam, ruangan, mode, atau keterangan).
    """
    # Validasi: minimal satu perubahan diisi (termasuk mode sekarang)
    if not any([req.jam_mulai_baru, req.jam_selesai_baru,
                req.ruangan_baru, req.mode, req.keterangan]):
        raise HTTPException(
            status_code=400,
            detail="Minimal satu perubahan harus diisi (jam, ruangan, mode, atau keterangan)"
        )
 
    success, pesan, data = dosen_service.simpan_jadwal_pengganti(
        db               = db,
        dosen            = dosen,
        matakuliah_id    = mk_id,
        pertemuan_ke     = req.pertemuan_ke,
        jam_mulai_baru   = req.jam_mulai_baru,
        jam_selesai_baru = req.jam_selesai_baru,
        ruangan_baru     = req.ruangan_baru,
        keterangan       = req.keterangan,
        mode             = req.mode,           # ← Fase B-1: teruskan ke service
    )
    if not success:
        raise HTTPException(status_code=400, detail=pesan)
    return {"message": pesan, "data": data}

# ─── 3.5b — GET /dosen/matakuliah/{mk_id}/jadwal-pengganti ───

@router.get("/matakuliah/{mk_id}/jadwal-pengganti")
def list_jadwal_pengganti(
    mk_id: UUID,
    dosen: User    = Depends(require_dosen),
    db   : Session = Depends(get_db),
):
    """
    List semua jadwal pengganti yang pernah dibuat untuk matakuliah ini.
    Diurutkan berdasarkan pertemuan_ke (ascending).
    """
    data = dosen_service.get_jadwal_pengganti_list(db, mk_id)
    return {"matakuliah_id": str(mk_id), "jadwal_pengganti": data}


# ─── 3.5c — DELETE /dosen/matakuliah/{mk_id}/jadwal-pengganti/{pertemuan_ke}

@router.delete("/matakuliah/{mk_id}/jadwal-pengganti/{pertemuan_ke}")
def hapus_jadwal_pengganti(
    mk_id       : UUID,
    pertemuan_ke: int,
    dosen       : User    = Depends(require_dosen),
    db          : Session = Depends(get_db),
):
    """
    Hapus jadwal pengganti untuk pertemuan tertentu.
    Setelah dihapus, sistem kembali menggunakan jam reguler dari tabel matakuliah.
    """
    success, pesan = dosen_service.hapus_jadwal_pengganti(db, mk_id, pertemuan_ke)
    if not success:
        raise HTTPException(status_code=404, detail=pesan)
    return {"message": pesan}