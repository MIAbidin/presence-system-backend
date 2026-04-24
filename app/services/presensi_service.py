# app/services/presensi_service.py
from datetime import datetime, timezone
from typing import Optional, Tuple
from uuid import UUID
from sqlalchemy.orm import Session

from app.models.presensi import Presensi, PresensiStatus, ModeKelas
from app.models.sesi import SesiPresensi, SesiStatus, SesiMode
from app.models.user import User
from app.services import face_service, sesi_service
from app.utils.geo_utils import dalam_radius


# ─── PROSES PRESENSI UTAMA ────────────────────────────────

def proses_presensi(
    db          : Session,
    mahasiswa   : User,
    sesi_id     : UUID,
    image_bytes : bytes,
    kode_sesi   : Optional[str] = None,   # wajib untuk mode online
    latitude    : Optional[float] = None,  # wajib untuk mode offline
    longitude   : Optional[float] = None,
) -> Tuple[bool, str, Optional[Presensi]]:
    """
    Logika inti presensi — urutan validasi:
    1. Cek sesi masih aktif
    2. Cek mahasiswa belum presensi di sesi ini
    3. Mode offline → validasi GPS geofencing
       Mode online  → validasi kode sesi (one-time-use)
    4. Verifikasi wajah (face recognition)
    5. Tentukan status: Hadir atau Terlambat
    6. Simpan ke database

    Return: (success, pesan_error_atau_sukses, presensi_object)
    """

    # ── Validasi 1: Cek sesi aktif ────────────────────────
    sesi = db.query(SesiPresensi).filter(
        SesiPresensi.id     == sesi_id,
        SesiPresensi.status == SesiStatus.aktif
    ).first()

    if not sesi:
        return False, "Sesi tidak ditemukan atau sudah ditutup", None

    # ── Validasi 2: Cek double presensi ───────────────────
    sudah_presensi = db.query(Presensi).filter(
        Presensi.mahasiswa_id == mahasiswa.id,
        Presensi.sesi_id      == sesi_id,
        Presensi.status.in_([PresensiStatus.hadir, PresensiStatus.terlambat])
    ).first()

    if sudah_presensi:
        return False, "Anda sudah melakukan presensi untuk sesi ini", None

    # ── Validasi 3a: GPS untuk mode offline ───────────────
    if sesi.mode == SesiMode.offline:
        if latitude is None or longitude is None:
            return False, "Data GPS wajib untuk presensi mode offline", None

        # Ambil koordinat ruang kelas dari relasi matakuliah
        matakuliah = sesi.matakuliah
        if not matakuliah or matakuliah.koordinat_lat is None:
            return False, "Koordinat ruang kelas belum dikonfigurasi, hubungi admin", None

        ok, jarak = dalam_radius(
            lat_mahasiswa=latitude,
            lng_mahasiswa=longitude,
            lat_kelas=matakuliah.koordinat_lat,
            lng_kelas=matakuliah.koordinat_lng,
            radius_meter=100.0
        )
        if not ok:
            return False, f"Anda berada di luar radius ruang kelas ({jarak:.0f}m dari ruangan, maks 100m)", None

    # ── Validasi 3b: Kode sesi untuk mode online ──────────
    if sesi.mode == SesiMode.online:
        if not kode_sesi:
            return False, "Kode sesi wajib dimasukkan untuk presensi mode online", None

        valid, pesan_kode, _ = sesi_service.validasi_kode(db, kode_sesi, mahasiswa.id)
        if not valid:
            return False, pesan_kode, None

    # ── Validasi 4: Verifikasi wajah ──────────────────────
    if not mahasiswa.is_face_registered:
        return False, "Wajah belum terdaftar, selesaikan registrasi terlebih dahulu", None

    passed, akurasi, pesan_wajah = face_service.verify_face(db, mahasiswa.id, image_bytes)
    if not passed:
        return False, pesan_wajah, None

    # ── Tentukan status: Hadir atau Terlambat ─────────────
    now = datetime.now(timezone.utc)
    batas_terlambat = sesi.waktu_buka + sesi.batas_terlambat

    if now > batas_terlambat:
        status = PresensiStatus.terlambat
    else:
        status = PresensiStatus.hadir

    # ── Simpan presensi ke database ───────────────────────
    presensi = Presensi(
        mahasiswa_id   = mahasiswa.id,
        sesi_id        = sesi_id,
        status         = status,
        waktu_presensi = now,
        akurasi_wajah  = akurasi,
        mode_kelas     = ModeKelas(sesi.mode.value),
        latitude       = latitude,
        longitude      = longitude,
    )
    db.add(presensi)

    # ── Tandai kode sudah dipakai (khusus online) ─────────
    if sesi.mode == SesiMode.online:
        sesi_service.tandai_kode_dipakai(db, sesi_id, mahasiswa.id)

    db.commit()
    db.refresh(presensi)

    pesan = f"Presensi berhasil! Status: {status.value.upper()}, Akurasi wajah: {akurasi:.1f}%"
    return True, pesan, presensi


# ─── UBAH STATUS MANUAL (DOSEN) ───────────────────────────

def ubah_status_manual(
    db          : Session,
    presensi_id : UUID,
    dosen_id    : UUID,
    status_baru : str,
    catatan     : Optional[str] = None
) -> Tuple[bool, str]:
    """
    Dosen mengubah status presensi mahasiswa secara manual.
    Contoh: dari Absen menjadi Izin dengan keterangan sakit.
    """
    presensi = db.query(Presensi).filter(Presensi.id == presensi_id).first()
    if not presensi:
        return False, "Data presensi tidak ditemukan"

    # Validasi status yang diinput
    try:
        status_enum = PresensiStatus(status_baru)
    except ValueError:
        valid = [s.value for s in PresensiStatus]
        return False, f"Status tidak valid. Pilihan: {', '.join(valid)}"

    presensi.status      = status_enum
    presensi.catatan     = catatan
    presensi.diubah_oleh = dosen_id
    db.commit()

    return True, f"Status berhasil diubah menjadi {status_baru}"


# ─── RIWAYAT KEHADIRAN MAHASISWA ──────────────────────────

def get_riwayat_mahasiswa(
    db          : Session,
    mahasiswa_id: UUID,
    matakuliah_id: Optional[UUID] = None
) -> list:
    """
    Ambil riwayat presensi mahasiswa.
    Bisa difilter per matakuliah (opsional).
    """
    query = db.query(Presensi).filter(
        Presensi.mahasiswa_id == mahasiswa_id
    )

    if matakuliah_id:
        # Join ke sesi untuk filter matakuliah
        query = query.join(SesiPresensi).filter(
            SesiPresensi.matakuliah_id == matakuliah_id
        )

    return query.order_by(Presensi.created_at.desc()).all()


# ─── REKAP SATU SESI (DOSEN) ──────────────────────────────

def get_rekap_sesi(db: Session, sesi_id: UUID) -> list:
    """Ambil semua presensi untuk satu sesi tertentu."""
    return db.query(Presensi).filter(
        Presensi.sesi_id == sesi_id
    ).order_by(Presensi.waktu_presensi.asc()).all()


# ─── HITUNG PERSENTASE KEHADIRAN ──────────────────────────

def hitung_persentase(presensi_list: list) -> dict:
    """Hitung statistik kehadiran dari list presensi."""
    total     = len(presensi_list)
    hadir     = sum(1 for p in presensi_list if p.status == PresensiStatus.hadir)
    terlambat = sum(1 for p in presensi_list if p.status == PresensiStatus.terlambat)
    absen     = sum(1 for p in presensi_list if p.status == PresensiStatus.absen)
    izin      = sum(1 for p in presensi_list if p.status == PresensiStatus.izin)
    sakit     = sum(1 for p in presensi_list if p.status == PresensiStatus.sakit)

    hadir_efektif = hadir + terlambat  # terlambat tetap dihitung hadir
    persen = round((hadir_efektif / total * 100), 1) if total > 0 else 0.0

    return {
        "total"         : total,
        "hadir"         : hadir,
        "terlambat"     : terlambat,
        "absen"         : absen,
        "izin"          : izin,
        "sakit"         : sakit,
        "hadir_efektif" : hadir_efektif,
        "persentase"    : persen,
    }