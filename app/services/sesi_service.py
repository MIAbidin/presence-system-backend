import secrets
import string
from datetime import datetime, timedelta, timezone
from typing import Optional, Tuple
from uuid import UUID
from sqlalchemy.orm import Session
from app.models.sesi import SesiPresensi, SesiMode, SesiStatus
from app.models.kode_usage import KodeUsage


# ─── GENERATE KODE SESI ───────────────────────────────────

def generate_kode_sesi(db: Session) -> str:
    """
    Generate kode sesi 6 karakter alfanumerik kapital yang unik.
    Contoh output: A7X3K2
    Gunakan secrets untuk kriptografis aman — tidak bisa ditebak.
    """
    alphabet = string.ascii_uppercase + string.digits
    # Hapus karakter yang membingungkan (O vs 0, I vs 1)
    alphabet = alphabet.replace("O", "").replace("I", "").replace("0", "").replace("1", "")

    while True:
        kode = "".join(secrets.choice(alphabet) for _ in range(6))
        # Pastikan kode benar-benar unik di database
        existing = db.query(SesiPresensi).filter(
            SesiPresensi.kode_sesi == kode,
            SesiPresensi.status == SesiStatus.aktif
        ).first()
        if not existing:
            return kode


# ─── BUKA SESI ────────────────────────────────────────────

def buka_sesi(
    db           : Session,
    dosen_id     : UUID,
    matakuliah_id: UUID,
    mode         : SesiMode,
    pertemuan_ke : int,
    batas_terlambat_menit: int = 15,
    durasi_menit : Optional[int] = None   # wajib untuk mode online
) -> SesiPresensi:
    """
    Buat sesi presensi baru.
    Mode offline: tidak ada kode sesi.
    Mode online: generate kode + set waktu expire.
    """
    kode_sesi      = None
    kode_expire_at = None

    if mode == SesiMode.online:
        if not durasi_menit:
            raise ValueError("durasi_menit wajib diisi untuk mode online")
        kode_sesi      = generate_kode_sesi(db)
        kode_expire_at = datetime.now(timezone.utc) + timedelta(minutes=durasi_menit)

    sesi = SesiPresensi(
        dosen_id              = dosen_id,
        matakuliah_id         = matakuliah_id,
        mode                  = mode,
        kode_sesi             = kode_sesi,
        kode_expire_at        = kode_expire_at,
        pertemuan_ke          = pertemuan_ke,
        batas_terlambat       = timedelta(minutes=batas_terlambat_menit),
        status                = SesiStatus.aktif,
    )
    db.add(sesi)
    db.commit()
    db.refresh(sesi)
    return sesi


# ─── VALIDASI KODE SESI ───────────────────────────────────

def validasi_kode(
    db          : Session,
    kode        : str,
    mahasiswa_id: UUID
) -> Tuple[bool, str, Optional[SesiPresensi]]:
    """
    Validasi kode sesi online dari mahasiswa.
    Cek urutan:
    1. Kode ada di database dan sesi masih aktif?
    2. Kode belum expired?
    3. Mahasiswa ini belum pernah pakai kode ini?

    Return: (valid, pesan_error, sesi_object)
    """
    # Cek 1: kode ada dan sesi aktif
    sesi = db.query(SesiPresensi).filter(
        SesiPresensi.kode_sesi == kode.upper(),
        SesiPresensi.status    == SesiStatus.aktif
    ).first()

    if not sesi:
        return False, "Kode sesi tidak valid", None

    # Cek 2: kode belum expired
    now = datetime.now(timezone.utc)
    if sesi.kode_expire_at and now > sesi.kode_expire_at:
        return False, "Sesi telah berakhir, hubungi dosen untuk memperpanjang", None

    # Cek 3: mahasiswa belum pernah pakai kode ini (one-time-use per mahasiswa)
    already_used = db.query(KodeUsage).filter(
        KodeUsage.sesi_id      == sesi.id,
        KodeUsage.mahasiswa_id == mahasiswa_id
    ).first()

    if already_used:
        return False, "Anda sudah melakukan presensi untuk sesi ini", None

    return True, "OK", sesi


# ─── TANDAI KODE SUDAH DIPAKAI ────────────────────────────

def tandai_kode_dipakai(db: Session, sesi_id: UUID, mahasiswa_id: UUID):
    """
    Insert record ke kode_usage setelah presensi berhasil.
    Dipanggil dari presensi_service setelah semua validasi lolos.
    """
    usage = KodeUsage(sesi_id=sesi_id, mahasiswa_id=mahasiswa_id)
    db.add(usage)
    db.commit()


# ─── PERPANJANG DURASI KODE ───────────────────────────────

def extend_kode(
    db            : Session,
    sesi_id       : UUID,
    dosen_id      : UUID,
    tambahan_menit: int
) -> Tuple[bool, str, Optional[SesiPresensi]]:
    """
    Tambah durasi kode aktif tanpa generate kode baru.
    Kode yang sama tetap berlaku, timer bertambah.
    """
    sesi = db.query(SesiPresensi).filter(
        SesiPresensi.id       == sesi_id,
        SesiPresensi.dosen_id == dosen_id,
        SesiPresensi.status   == SesiStatus.aktif
    ).first()

    if not sesi:
        return False, "Sesi tidak ditemukan atau bukan milik Anda", None

    if sesi.mode != SesiMode.online:
        return False, "Perpanjangan kode hanya untuk mode online", None

    # Perpanjang dari waktu expire yang ada (bukan dari sekarang)
    base_time = sesi.kode_expire_at or datetime.now(timezone.utc)
    sesi.kode_expire_at = base_time + timedelta(minutes=tambahan_menit)
    db.commit()
    db.refresh(sesi)
    return True, f"Kode diperpanjang +{tambahan_menit} menit", sesi


# ─── REGENERASI KODE BARU ─────────────────────────────────

def regen_kode(
    db      : Session,
    sesi_id : UUID,
    dosen_id: UUID,
    durasi_menit: int = 30
) -> Tuple[bool, str, Optional[SesiPresensi]]:
    """
    Generate kode baru — kode lama langsung hangus.
    Mahasiswa yang belum presensi harus pakai kode baru ini.
    Dipakai saat kode bocor ke grup yang tidak seharusnya.
    """
    sesi = db.query(SesiPresensi).filter(
        SesiPresensi.id       == sesi_id,
        SesiPresensi.dosen_id == dosen_id,
        SesiPresensi.status   == SesiStatus.aktif
    ).first()

    if not sesi:
        return False, "Sesi tidak ditemukan", None

    # Generate kode baru, kode lama otomatis tidak valid
    # karena query validasi_kode mencari berdasarkan kode_sesi terbaru
    sesi.kode_sesi      = generate_kode_sesi(db)
    sesi.kode_expire_at = datetime.now(timezone.utc) + timedelta(minutes=durasi_menit)
    db.commit()
    db.refresh(sesi)
    return True, f"Kode baru: {sesi.kode_sesi}", sesi


# ─── TUTUP SESI ───────────────────────────────────────────

def tutup_sesi(
    db      : Session,
    sesi_id : UUID,
    dosen_id: UUID
) -> Tuple[bool, str]:
    """
    Tutup sesi — set status selesai dan waktu_tutup.
    Kode online langsung tidak valid karena sesi.status != aktif.
    """
    sesi = db.query(SesiPresensi).filter(
        SesiPresensi.id       == sesi_id,
        SesiPresensi.dosen_id == dosen_id,
        SesiPresensi.status   == SesiStatus.aktif
    ).first()

    if not sesi:
        return False, "Sesi tidak ditemukan atau sudah ditutup"

    sesi.status      = SesiStatus.selesai
    sesi.waktu_tutup = datetime.now(timezone.utc)
    sesi.kode_sesi   = None   # hapus kode agar tidak bisa dipakai lagi
    db.commit()
    return True, "Sesi berhasil ditutup"


# ─── CEK SESI AKTIF ───────────────────────────────────────

def get_sesi_aktif(
    db           : Session,
    matakuliah_id: UUID
) -> Optional[SesiPresensi]:
    """Ambil sesi yang sedang aktif untuk matakuliah tertentu."""
    return db.query(SesiPresensi).filter(
        SesiPresensi.matakuliah_id == matakuliah_id,
        SesiPresensi.status        == SesiStatus.aktif
    ).first()


# ─── HITUNG DETIK TERSISA ─────────────────────────────────

def hitung_detik_tersisa(sesi: SesiPresensi) -> Optional[int]:
    """Hitung sisa detik kode aktif — untuk countdown timer di frontend."""
    if not sesi.kode_expire_at:
        return None
    delta = sesi.kode_expire_at - datetime.now(timezone.utc)
    return max(0, int(delta.total_seconds()))