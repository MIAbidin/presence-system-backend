"""
app/services/sesi_service.py
════════════════════════════
Fase 2 Update:
- 2.1: waktu_buka bisa diset dari jam_mulai matakuliah (bukan waktu sekarang)
- 2.2: tutup_sesi_otomatis() — dipanggil scheduler setiap menit
- 2.3: batas_terlambat kini bisa None (artinya tidak ada batas terlambat)
- 2.4: logika mahasiswa tamu terintegrasi di presensi_service

Alur buka sesi:
  dosen klik "Buka Sesi" → pilih mulai_dari_jam_jadwal (True/False)
  kalau True  → waktu_buka = jam_mulai matakuliah hari ini (UTC)
  kalau False → waktu_buka = sekarang (default lama)
"""

import secrets
import string
import logging
from datetime import datetime, timedelta, timezone, date, time as dtime
from typing import Optional, Tuple
from uuid import UUID

from sqlalchemy.orm import Session

from app.models.sesi import SesiPresensi, SesiMode, SesiStatus
from app.models.kode_usage import KodeUsage
from app.models.matakuliah import Matakuliah
from app.models.jadwal_pengganti import JadwalPengganti

logger = logging.getLogger(__name__)


# ─── GENERATE KODE SESI ───────────────────────────────────────

def generate_kode_sesi(db: Session) -> str:
    """
    Generate kode sesi 6 karakter alfanumerik kapital yang unik.
    Hapus karakter yang membingungkan: O vs 0, I vs 1, L vs 1.
    """
    alphabet = string.ascii_uppercase + string.digits
    for ch in "OI0L1":
        alphabet = alphabet.replace(ch, "")

    while True:
        kode = "".join(secrets.choice(alphabet) for _ in range(6))
        existing = db.query(SesiPresensi).filter(
            SesiPresensi.kode_sesi == kode,
            SesiPresensi.status    == SesiStatus.aktif
        ).first()
        if not existing:
            return kode


# ─── HELPER: jam_mulai matakuliah → datetime hari ini (UTC) ──

def _jam_ke_datetime_utc(jam: dtime, tz_offset_jam: int = 7) -> datetime:
    """
    Konversi jam matakuliah (misal 08:00) ke datetime UTC hari ini.
    Default offset +7 (WIB). Bisa diubah lewat env var nanti.
    """
    now_local = datetime.now(timezone(timedelta(hours=tz_offset_jam)))
    local_dt  = datetime(
        now_local.year, now_local.month, now_local.day,
        jam.hour, jam.minute, 0,
        tzinfo=timezone(timedelta(hours=tz_offset_jam))
    )
    return local_dt.astimezone(timezone.utc)


# ─── BUKA SESI ────────────────────────────────────────────────

def buka_sesi(
    db                    : Session,
    dosen_id              : UUID,
    matakuliah_id         : UUID,
    mode                  : SesiMode,
    pertemuan_ke          : int,
    batas_terlambat_menit : Optional[int] = 15,   # None = tidak ada batas
    durasi_menit          : Optional[int] = None,  # wajib untuk online
    mulai_dari_jam_jadwal : bool = False,           # 2.1: pakai jam_mulai mk
    tz_offset_jam         : int  = 7,              # offset timezone lokal
) -> SesiPresensi:
    """
    Buat sesi presensi baru.

    Fase 2.1:
      mulai_dari_jam_jadwal=True  → waktu_buka = jam_mulai matakuliah hari ini
      mulai_dari_jam_jadwal=False → waktu_buka = sekarang (default)

    Fase 2.3:
      batas_terlambat_menit=None → tidak ada batas terlambat,
      selama sesi aktif semua presensi dicatat "hadir"
    """
    if mode == SesiMode.online and not durasi_menit:
        raise ValueError("durasi_menit wajib diisi untuk mode online")

    # ── Tentukan waktu_buka ──────────────────────────────────
    if mulai_dari_jam_jadwal:
        mk = db.query(Matakuliah).filter(Matakuliah.id == matakuliah_id).first()
        if mk and mk.jam_mulai:
            waktu_buka = _jam_ke_datetime_utc(mk.jam_mulai, tz_offset_jam)
            logger.info(
                f"Sesi buka dari jam jadwal: {mk.jam_mulai} "
                f"→ {waktu_buka.isoformat()}"
            )
        else:
            waktu_buka = datetime.now(timezone.utc)
            logger.warning("jam_mulai matakuliah belum diset, pakai waktu sekarang")
    else:
        waktu_buka = datetime.now(timezone.utc)

    # ── Batas terlambat ──────────────────────────────────────
    batas = (
        timedelta(minutes=batas_terlambat_menit)
        if batas_terlambat_menit is not None
        else None   # None = tidak ada batas terlambat
    )

    # ── Kode sesi (online) ───────────────────────────────────
    kode_sesi      = None
    kode_expire_at = None
    if mode == SesiMode.online:
        kode_sesi      = generate_kode_sesi(db)
        kode_expire_at = datetime.now(timezone.utc) + timedelta(minutes=durasi_menit)

    sesi = SesiPresensi(
        dosen_id        = dosen_id,
        matakuliah_id   = matakuliah_id,
        mode            = mode,
        kode_sesi       = kode_sesi,
        kode_expire_at  = kode_expire_at,
        pertemuan_ke    = pertemuan_ke,
        batas_terlambat = batas,
        waktu_buka      = waktu_buka,
        status          = SesiStatus.aktif,
    )
    db.add(sesi)
    db.commit()
    db.refresh(sesi)
    return sesi


# ─── TUTUP SESI OTOMATIS (dipanggil scheduler) ────────────────

def tutup_sesi_otomatis(db: Session) -> int:
    """
    Fase 2.2 — Dipanggil APScheduler setiap menit.

    Cek semua sesi aktif:
    - Ambil jam_selesai dari jadwal_pengganti kalau ada,
      fallback ke jam_selesai reguler matakuliah.
    - Kalau waktu sekarang >= jam_selesai → tutup sesi.
    - Mahasiswa yang belum presensi → insert Absen.

    Return: jumlah sesi yang ditutup
    """
    from app.models.presensi import Presensi, PresensiStatus, ModeKelas
    from app.models.mahasiswa_matakuliah import MahasiswaMatakuliah
    from app.services.notification_service import kirim_notifikasi

    now_utc = datetime.now(timezone.utc)
    sesi_aktif = db.query(SesiPresensi).filter(
        SesiPresensi.status == SesiStatus.aktif
    ).all()

    ditutup = 0
    for sesi in sesi_aktif:
        mk = sesi.matakuliah
        if not mk:
            continue

        # ── Tentukan jam_selesai efektif ─────────────────────
        jam_selesai_efektif = _get_jam_selesai_efektif(
            db, mk, sesi.pertemuan_ke
        )
        if jam_selesai_efektif is None:
            continue   # jam_selesai belum diset, skip

        # Konversi ke datetime UTC hari ini
        waktu_selesai = _jam_ke_datetime_utc(jam_selesai_efektif)

        # Kalau sesi dibuka > jam_selesai (edge case: buka manual malam),
        # jangan langsung tutup — skip
        if waktu_selesai <= sesi.waktu_buka.replace(tzinfo=timezone.utc):
            continue

        if now_utc < waktu_selesai:
            continue  # belum waktunya tutup

        logger.info(
            f"[Scheduler] Tutup sesi otomatis: {sesi.id} "
            f"| MK: {mk.nama} | Pertemuan {sesi.pertemuan_ke}"
        )

        # ── Ambil mahasiswa terdaftar di matakuliah ini ───────
        rows = db.query(MahasiswaMatakuliah).filter(
            MahasiswaMatakuliah.matakuliah_id == sesi.matakuliah_id
        ).all()
        mahasiswa_ids = [r.mahasiswa_id for r in rows]

        # ── Cek siapa yang sudah presensi ─────────────────────
        sudah_presensi = {
            p.mahasiswa_id
            for p in db.query(Presensi).filter(
                Presensi.sesi_id == sesi.id
            ).all()
        }

        # ── Insert Absen untuk yang belum presensi ────────────
        absen_baru = 0
        for mhs_id in mahasiswa_ids:
            if mhs_id not in sudah_presensi:
                db.add(Presensi(
                    mahasiswa_id   = mhs_id,
                    sesi_id        = sesi.id,
                    status         = PresensiStatus.absen,
                    waktu_presensi = None,
                    akurasi_wajah  = None,
                    mode_kelas     = ModeKelas(sesi.mode.value),
                ))
                absen_baru += 1

        # ── Tutup sesi ────────────────────────────────────────
        sesi.status      = SesiStatus.selesai
        sesi.waktu_tutup = now_utc
        sesi.kode_sesi   = None  # hanguskan kode online

        db.commit()
        ditutup += 1

        # ── Notifikasi ke dosen ───────────────────────────────
        try:
            dosen = sesi.dosen
            if dosen and dosen.fcm_token:
                kirim_notifikasi(
                    device_token = dosen.fcm_token,
                    judul        = f"📋 Sesi {mk.nama} Selesai",
                    isi          = (
                        f"Pertemuan {sesi.pertemuan_ke} otomatis ditutup. "
                        f"{absen_baru} mahasiswa tercatat Absen."
                    ),
                    data         = {
                        "type"   : "sesi_selesai",
                        "sesi_id": str(sesi.id),
                    },
                )
        except Exception as e:
            logger.warning(f"Gagal kirim notifikasi dosen: {e}")

    if ditutup > 0:
        logger.info(f"[Scheduler] Total sesi ditutup otomatis: {ditutup}")

    return ditutup


def _get_jam_selesai_efektif(
    db           : Session,
    mk           : Matakuliah,
    pertemuan_ke : int,
) -> Optional[dtime]:
    """
    Ambil jam_selesai efektif:
    1. Cek jadwal_pengganti untuk pertemuan ini
    2. Kalau tidak ada, pakai jam_selesai reguler matakuliah
    """
    pengganti = db.query(JadwalPengganti).filter(
        JadwalPengganti.matakuliah_id == mk.id,
        JadwalPengganti.pertemuan_ke  == pertemuan_ke,
    ).first()

    if pengganti and pengganti.jam_selesai_baru:
        return pengganti.jam_selesai_baru

    return mk.jam_selesai  # bisa None kalau belum diset


# ─── VALIDASI KODE SESI ───────────────────────────────────────

def validasi_kode(
    db          : Session,
    kode        : str,
    mahasiswa_id: UUID
) -> Tuple[bool, str, Optional[SesiPresensi]]:
    """Validasi kode sesi online dari mahasiswa."""
    sesi = db.query(SesiPresensi).filter(
        SesiPresensi.kode_sesi == kode.upper(),
        SesiPresensi.status    == SesiStatus.aktif
    ).first()

    if not sesi:
        return False, "Kode sesi tidak valid", None

    now = datetime.now(timezone.utc)
    if sesi.kode_expire_at and now > sesi.kode_expire_at:
        return False, "Sesi telah berakhir, hubungi dosen untuk memperpanjang", None

    already_used = db.query(KodeUsage).filter(
        KodeUsage.sesi_id      == sesi.id,
        KodeUsage.mahasiswa_id == mahasiswa_id
    ).first()
    if already_used:
        return False, "Anda sudah melakukan presensi untuk sesi ini", None

    return True, "OK", sesi


# ─── TANDAI KODE SUDAH DIPAKAI ────────────────────────────────

def tandai_kode_dipakai(db: Session, sesi_id: UUID, mahasiswa_id: UUID):
    """Insert record ke kode_usage setelah presensi berhasil."""
    usage = KodeUsage(sesi_id=sesi_id, mahasiswa_id=mahasiswa_id)
    db.add(usage)
    db.commit()


# ─── PERPANJANG DURASI KODE ───────────────────────────────────

def extend_kode(
    db            : Session,
    sesi_id       : UUID,
    dosen_id      : UUID,
    tambahan_menit: int
) -> Tuple[bool, str, Optional[SesiPresensi]]:
    """Tambah durasi kode aktif tanpa generate kode baru."""
    sesi = db.query(SesiPresensi).filter(
        SesiPresensi.id       == sesi_id,
        SesiPresensi.dosen_id == dosen_id,
        SesiPresensi.status   == SesiStatus.aktif
    ).first()

    if not sesi:
        return False, "Sesi tidak ditemukan atau bukan milik Anda", None
    if sesi.mode != SesiMode.online:
        return False, "Perpanjangan kode hanya untuk mode online", None

    base_time = sesi.kode_expire_at or datetime.now(timezone.utc)
    sesi.kode_expire_at = base_time + timedelta(minutes=tambahan_menit)
    db.commit()
    db.refresh(sesi)
    return True, f"Kode diperpanjang +{tambahan_menit} menit", sesi


# ─── REGENERASI KODE BARU ─────────────────────────────────────

def regen_kode(
    db          : Session,
    sesi_id     : UUID,
    dosen_id    : UUID,
    durasi_menit: int = 30
) -> Tuple[bool, str, Optional[SesiPresensi]]:
    """Generate kode baru — kode lama langsung hangus."""
    sesi = db.query(SesiPresensi).filter(
        SesiPresensi.id       == sesi_id,
        SesiPresensi.dosen_id == dosen_id,
        SesiPresensi.status   == SesiStatus.aktif
    ).first()

    if not sesi:
        return False, "Sesi tidak ditemukan", None

    sesi.kode_sesi      = generate_kode_sesi(db)
    sesi.kode_expire_at = datetime.now(timezone.utc) + timedelta(minutes=durasi_menit)
    db.commit()
    db.refresh(sesi)
    return True, f"Kode baru: {sesi.kode_sesi}", sesi


# ─── TUTUP SESI MANUAL ────────────────────────────────────────

def tutup_sesi(
    db      : Session,
    sesi_id : UUID,
    dosen_id: UUID
) -> Tuple[bool, str]:
    """Tutup sesi manual oleh dosen."""
    sesi = db.query(SesiPresensi).filter(
        SesiPresensi.id       == sesi_id,
        SesiPresensi.dosen_id == dosen_id,
        SesiPresensi.status   == SesiStatus.aktif
    ).first()

    if not sesi:
        return False, "Sesi tidak ditemukan atau sudah ditutup"

    sesi.status      = SesiStatus.selesai
    sesi.waktu_tutup = datetime.now(timezone.utc)
    sesi.kode_sesi   = None
    db.commit()
    return True, "Sesi berhasil ditutup"


# ─── CEK SESI AKTIF ───────────────────────────────────────────

def get_sesi_aktif(
    db           : Session,
    matakuliah_id: UUID
) -> Optional[SesiPresensi]:
    """Ambil sesi yang sedang aktif untuk matakuliah tertentu."""
    return db.query(SesiPresensi).filter(
        SesiPresensi.matakuliah_id == matakuliah_id,
        SesiPresensi.status        == SesiStatus.aktif
    ).first()


# ─── HITUNG DETIK TERSISA ─────────────────────────────────────

def hitung_detik_tersisa(sesi: SesiPresensi) -> Optional[int]:
    """Hitung sisa detik kode aktif — untuk countdown timer di frontend."""
    if not sesi.kode_expire_at:
        return None
    kode_expire = sesi.kode_expire_at
    if kode_expire.tzinfo is None:
        kode_expire = kode_expire.replace(tzinfo=timezone.utc)
    delta = kode_expire - datetime.now(timezone.utc)
    return max(0, int(delta.total_seconds()))