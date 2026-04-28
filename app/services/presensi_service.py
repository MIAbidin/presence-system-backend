"""
app/services/presensi_service.py
═════════════════════════════════
Fase 2 Update:
- 2.3: batas_terlambat bisa None (tidak ada batas — selama sesi aktif = hadir)
- 2.4: logika mahasiswa tamu
    - kalau mahasiswa tidak terdaftar di matakuliah:
        a. cek izin_tamu matakuliah
        b. kalau TRUE → presensi diizinkan + otomatis insert ke mahasiswa_matakuliah
           dengan is_tamu=True dan kelas_asal diisi dari matakuliah asli mahasiswa
        c. kalau FALSE → tolak dengan pesan jelas
"""
from datetime import datetime, timezone
from typing import Optional, Tuple
from uuid import UUID
from sqlalchemy.orm import Session

from app.models.presensi import Presensi, PresensiStatus, ModeKelas
from app.models.sesi import SesiPresensi, SesiStatus, SesiMode
from app.models.user import User
from app.models.matakuliah import Matakuliah
from app.models.mahasiswa_matakuliah import MahasiswaMatakuliah
from app.services import face_service, sesi_service
from app.utils.geo_utils import dalam_radius


# ─── HELPER: ambil kelas asal mahasiswa ───────────────────────

def _get_kelas_asal(db: Session, mahasiswa_id: UUID) -> Optional[str]:
    """
    Cari matakuliah asli mahasiswa ini (bukan tamu).
    Return string, misal: "IF302 - Teknik Informatika"
    Dipakai sebagai kelas_asal saat mahasiswa masuk sebagai tamu.
    """
    row = db.query(MahasiswaMatakuliah).filter(
        MahasiswaMatakuliah.mahasiswa_id == mahasiswa_id,
        MahasiswaMatakuliah.is_tamu      == False,  # noqa: E712
    ).first()

    if row and row.matakuliah:
        return f"{row.matakuliah.kode} - {row.matakuliah.nama}"
    return None


# ─── HELPER: pastikan mahasiswa boleh presensi di sesi ini ────

def _pastikan_akses_mahasiswa(
    db          : Session,
    mahasiswa_id: UUID,
    matakuliah_id: UUID,
) -> Tuple[bool, str]:
    """
    Fase 2.4 — Validasi akses mahasiswa ke matakuliah ini.

    Alur:
    1. Cek apakah mahasiswa terdaftar (is_tamu TRUE atau FALSE = boleh semua)
    2. Kalau tidak terdaftar:
       a. Cek izin_tamu matakuliah
       b. Kalau TRUE → insert tamu baru otomatis → return (True, "tamu_baru")
       c. Kalau FALSE → return (False, "tidak terdaftar")

    Return: (boleh, pesan)
    """
    # Cek sudah terdaftar (asli atau tamu sebelumnya)
    terdaftar = db.query(MahasiswaMatakuliah).filter(
        MahasiswaMatakuliah.mahasiswa_id  == mahasiswa_id,
        MahasiswaMatakuliah.matakuliah_id == matakuliah_id,
    ).first()

    if terdaftar:
        return True, "terdaftar"

    # Belum terdaftar — cek izin_tamu
    mk = db.query(Matakuliah).filter(Matakuliah.id == matakuliah_id).first()
    if not mk:
        return False, "Matakuliah tidak ditemukan"

    if not mk.izin_tamu:
        return False, (
            f"Kelas {mk.nama} tidak menerima mahasiswa tamu. "
            "Hubungi dosen untuk mendapatkan akses."
        )

    # izin_tamu = TRUE → daftarkan otomatis sebagai tamu
    kelas_asal = _get_kelas_asal(db, mahasiswa_id)
    db.add(MahasiswaMatakuliah(
        mahasiswa_id  = mahasiswa_id,
        matakuliah_id = matakuliah_id,
        is_tamu       = True,
        kelas_asal    = kelas_asal,
    ))
    # Flush dulu (belum commit) — commit setelah presensi sukses
    db.flush()
    return True, "tamu_baru"


# ─── PROSES PRESENSI UTAMA ────────────────────────────────────

def proses_presensi(
    db          : Session,
    mahasiswa   : User,
    sesi_id     : UUID,
    image_bytes : bytes,
    kode_sesi   : Optional[str]   = None,
    latitude    : Optional[float] = None,
    longitude   : Optional[float] = None,
) -> Tuple[bool, str, Optional[Presensi]]:
    """
    Proses presensi mahasiswa end-to-end.

    Update Fase 2:
    - 2.3: batas_terlambat=None → semua presensi saat sesi aktif = hadir
    - 2.4: cek izin_tamu kalau mahasiswa belum terdaftar di matakuliah
    """

    # ── 1. Cek sesi aktif ────────────────────────────────────
    sesi = db.query(SesiPresensi).filter(
        SesiPresensi.id     == sesi_id,
        SesiPresensi.status == SesiStatus.aktif
    ).first()
    if not sesi:
        return False, "Sesi tidak ditemukan atau sudah ditutup", None

    # ── 2. Cek akses mahasiswa (2.4) ─────────────────────────
    boleh, pesan_akses = _pastikan_akses_mahasiswa(
        db, mahasiswa.id, sesi.matakuliah_id
    )
    if not boleh:
        return False, pesan_akses, None

    # ── 3. Cek presensi duplikat ──────────────────────────────
    sudah = db.query(Presensi).filter(
        Presensi.mahasiswa_id == mahasiswa.id,
        Presensi.sesi_id      == sesi_id,
        Presensi.status.in_([PresensiStatus.hadir, PresensiStatus.terlambat])
    ).first()
    if sudah:
        return False, "Anda sudah melakukan presensi untuk sesi ini", None

    # ── 4a. MODE OFFLINE — validasi GPS ──────────────────────
    if sesi.mode == SesiMode.offline:
        if latitude is None or longitude is None:
            return False, "GPS wajib untuk mode offline", None

        mk = sesi.matakuliah
        if not mk or mk.koordinat_lat is None:
            return False, "Koordinat kelas belum diset, hubungi admin", None

        ok, jarak = dalam_radius(
            lat_mahasiswa = latitude,
            lng_mahasiswa = longitude,
            lat_kelas     = mk.koordinat_lat,
            lng_kelas     = mk.koordinat_lng,
            radius_meter  = 100.0
        )
        if not ok:
            return False, (
                f"Anda berada di luar radius kelas ({jarak:.0f}m dari ruangan). "
                "Pastikan GPS aktif dan Anda berada di dalam gedung."
            ), None

    # ── 4b. MODE ONLINE — validasi kode sesi ─────────────────
    if sesi.mode == SesiMode.online:
        if not kode_sesi:
            return False, "Kode sesi wajib untuk mode online", None
        valid, pesan_kode, _ = sesi_service.validasi_kode(
            db, kode_sesi, mahasiswa.id
        )
        if not valid:
            return False, pesan_kode, None

    # ── 5. Cek wajah terdaftar ────────────────────────────────
    if not mahasiswa.is_face_registered:
        return False, "Wajah belum terdaftar, selesaikan registrasi terlebih dahulu", None

    # ── 6. FACE RECOGNITION ───────────────────────────────────
    try:
        passed, akurasi, pesan_face = face_service.verify_face(
            db, mahasiswa.id, image_bytes
        )
    except Exception as e:
        return False, f"Error verifikasi wajah: {str(e)}", None

    if not passed:
        return False, pesan_face, None

    # ── 7. Tentukan status (2.3) ──────────────────────────────
    now = datetime.now(timezone.utc)

    waktu_buka = sesi.waktu_buka
    if waktu_buka.tzinfo is None:
        waktu_buka = waktu_buka.replace(tzinfo=timezone.utc)

    if sesi.batas_terlambat is None:
        # Tidak ada batas → semua presensi saat sesi aktif = hadir
        status = PresensiStatus.hadir
    else:
        batas_terlambat = waktu_buka + sesi.batas_terlambat
        status = (
            PresensiStatus.terlambat
            if now > batas_terlambat
            else PresensiStatus.hadir
        )

    # ── 8. Simpan presensi ────────────────────────────────────
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

    # ── 9. Tandai kode dipakai (online) ──────────────────────
    if sesi.mode == SesiMode.online:
        sesi_service.tandai_kode_dipakai(db, sesi_id, mahasiswa.id)

    db.commit()
    db.refresh(presensi)

    return True, f"Presensi berhasil ({status.value})", presensi


# ─── UBAH STATUS MANUAL ───────────────────────────────────────

def ubah_status_manual(
    db         : Session,
    presensi_id: UUID,
    dosen_id   : UUID,
    status_baru: str,
    catatan    : Optional[str] = None
) -> Tuple[bool, str]:
    presensi = db.query(Presensi).filter(Presensi.id == presensi_id).first()
    if not presensi:
        return False, "Data presensi tidak ditemukan"

    try:
        status_enum = PresensiStatus(status_baru)
    except ValueError:
        return False, f"Status tidak valid: {status_baru}"

    presensi.status      = status_enum
    presensi.catatan     = catatan
    presensi.diubah_oleh = dosen_id
    db.commit()
    return True, f"Status berhasil diubah menjadi {status_baru}"


# ─── RIWAYAT MAHASISWA ────────────────────────────────────────

def get_riwayat_mahasiswa(
    db           : Session,
    mahasiswa_id : UUID,
    matakuliah_id: Optional[UUID] = None
):
    query = db.query(Presensi).filter(Presensi.mahasiswa_id == mahasiswa_id)
    if matakuliah_id:
        query = query.join(SesiPresensi).filter(
            SesiPresensi.matakuliah_id == matakuliah_id
        )
    return query.order_by(Presensi.created_at.desc()).all()


# ─── REKAP SESI ───────────────────────────────────────────────

def get_rekap_sesi(db: Session, sesi_id: UUID):
    return db.query(Presensi).filter(Presensi.sesi_id == sesi_id).all()


# ─── HITUNG STATISTIK ─────────────────────────────────────────

def hitung_persentase(presensi_list: list) -> dict:
    total     = len(presensi_list)
    hadir     = sum(p.status == PresensiStatus.hadir     for p in presensi_list)
    terlambat = sum(p.status == PresensiStatus.terlambat for p in presensi_list)
    absen     = sum(p.status == PresensiStatus.absen     for p in presensi_list)
    izin      = sum(p.status == PresensiStatus.izin      for p in presensi_list)
    sakit     = sum(p.status == PresensiStatus.sakit     for p in presensi_list)
    efektif   = hadir + terlambat
    persen    = round(efektif / total * 100, 1) if total else 0.0

    return {
        "total"        : total,
        "hadir"        : hadir,
        "terlambat"    : terlambat,
        "absen"        : absen,
        "izin"         : izin,
        "sakit"        : sakit,
        "hadir_efektif": efektif,
        "persentase"   : persen,
    }