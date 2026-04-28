"""
app/scheduler.py
════════════════
Fase 2.2 & 2.3 — APScheduler untuk otomasi backend.

Job yang dijalankan:
1. tutup_sesi_expired()  — setiap 1 menit
   Cek semua sesi aktif. Kalau jam_selesai sudah lewat → tutup + absenkan.

2. notif_pengingat_buka_sesi() — setiap 1 menit
   15 menit sebelum jam_mulai matakuliah → kirim push ke dosen pengingat.

Install: pip install apscheduler
"""

import logging
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger

logger = logging.getLogger(__name__)

# Singleton scheduler — diinisialisasi sekali di main.py
_scheduler: BackgroundScheduler | None = None


def get_scheduler() -> BackgroundScheduler:
    global _scheduler
    if _scheduler is None:
        _scheduler = BackgroundScheduler(
            job_defaults={
                "coalesce"        : True,   # skip job yang terlewat, jangan tumpuk
                "max_instances"   : 1,      # satu job tidak jalan paralel
                "misfire_grace_time": 60,   # toleransi 60 detik terlambat
            },
            timezone="UTC",
        )
    return _scheduler


# ─── JOB 1: Tutup sesi yang sudah lewat jam selesai ──────────

def _job_tutup_sesi_expired():
    """Dipanggil scheduler setiap 1 menit."""
    from app.database.db import SessionLocal
    from app.services.sesi_service import tutup_sesi_otomatis

    db = SessionLocal()
    try:
        ditutup = tutup_sesi_otomatis(db)
        if ditutup > 0:
            logger.info(f"[Scheduler] tutup_sesi_expired: {ditutup} sesi ditutup")
    except Exception as e:
        logger.error(f"[Scheduler] Error tutup_sesi_expired: {e}", exc_info=True)
    finally:
        db.close()


# ─── JOB 2: Pengingat buka sesi 15 menit sebelum jam mulai ───

def _job_notif_pengingat_buka_sesi():
    """
    Setiap 1 menit, cek matakuliah yang jam_mulainya 15 menit lagi.
    Kalau belum ada sesi aktif → kirim push notification ke dosen.

    Cara kerja:
    - Ambil waktu sekarang + 15 menit
    - Cari matakuliah yang jam_mulai == sekarang+15 (window ±1 menit)
    - Cek apakah dosen sudah buka sesi (SesiPresensi aktif hari ini)
    - Kalau belum → kirim notif FCM ke dosen
    """
    from datetime import datetime, timezone, timedelta
    from app.database.db import SessionLocal
    from app.models.matakuliah import Matakuliah
    from app.models.sesi import SesiPresensi, SesiStatus
    from app.models.user import User, UserRole
    from app.services.notification_service import kirim_notifikasi

    db = SessionLocal()
    try:
        now_utc = datetime.now(timezone.utc)
        # Waktu target: 15 menit dari sekarang (WIB = UTC+7)
        now_wib     = now_utc + timedelta(hours=7)
        target_wib  = now_wib + timedelta(minutes=15)

        # Ambil semua dosen aktif
        dosen_list = db.query(User).filter(
            User.role     == UserRole.dosen,
            User.is_active== True,
            User.fcm_token != None,  # noqa: E711
        ).all()

        for dosen in dosen_list:
            # Cari matakuliah yang diampu dosen ini yang mulai 15 menit lagi
            from app.models.sesi import SesiPresensi
            sesi_mk_ids = {
                s.matakuliah_id
                for s in db.query(SesiPresensi).filter(
                    SesiPresensi.dosen_id == dosen.id
                ).all()
            }

            # Fallback: ambil semua matakuliah (kalau belum pernah buka sesi)
            mk_list = db.query(Matakuliah).all()

            for mk in mk_list:
                if not mk.jam_mulai:
                    continue

                # Cek hari (WIB)
                hari_map = {
                    0: "Senin", 1: "Selasa", 2: "Rabu", 3: "Kamis",
                    4: "Jumat", 5: "Sabtu", 6: "Minggu",
                }
                hari_sekarang = hari_map.get(now_wib.weekday(), "")
                if mk.hari != hari_sekarang:
                    continue

                # Cek apakah jam_mulai dalam window ±1 menit dari target
                jam = mk.jam_mulai
                selisih_menit = abs(
                    (target_wib.hour * 60 + target_wib.minute)
                    - (jam.hour * 60 + jam.minute)
                )
                if selisih_menit > 1:
                    continue

                # Cek apakah sesi sudah aktif
                sesi_aktif = db.query(SesiPresensi).filter(
                    SesiPresensi.matakuliah_id == mk.id,
                    SesiPresensi.dosen_id      == dosen.id,
                    SesiPresensi.status        == SesiStatus.aktif,
                ).first()
                if sesi_aktif:
                    continue  # sudah buka sesi, tidak perlu pengingat

                # Kirim notif
                kirim_notifikasi(
                    device_token = dosen.fcm_token,
                    judul        = f"⏰ {mk.nama} Mulai 15 Menit Lagi",
                    isi          = (
                        f"Jangan lupa buka sesi presensi perkuliahan "
                        f"{mk.nama} pukul {jam.strftime('%H:%M')} WIB."
                    ),
                    data         = {
                        "type"          : "pengingat_buka_sesi",
                        "matakuliah_id" : str(mk.id),
                    },
                )
                logger.info(
                    f"[Scheduler] Notif pengingat terkirim ke {dosen.nama_lengkap} "
                    f"untuk {mk.nama}"
                )

    except Exception as e:
        logger.error(f"[Scheduler] Error notif_pengingat: {e}", exc_info=True)
    finally:
        db.close()


# ─── START & STOP ─────────────────────────────────────────────

def start_scheduler():
    """
    Dipanggil di app/main.py saat FastAPI startup.
    Daftarkan semua job dan mulai scheduler.
    """
    scheduler = get_scheduler()

    if scheduler.running:
        logger.info("[Scheduler] Sudah berjalan, skip start")
        return

    # Job 1: tutup sesi expired — setiap 1 menit
    scheduler.add_job(
        func    = _job_tutup_sesi_expired,
        trigger = IntervalTrigger(minutes=1),
        id      = "tutup_sesi_expired",
        name    = "Tutup sesi yang sudah lewat jam selesai",
        replace_existing=True,
    )

    # Job 2: notif pengingat — setiap 1 menit
    scheduler.add_job(
        func    = _job_notif_pengingat_buka_sesi,
        trigger = IntervalTrigger(minutes=1),
        id      = "notif_pengingat_buka_sesi",
        name    = "Notifikasi pengingat buka sesi 15 menit sebelum mulai",
        replace_existing=True,
    )

    scheduler.start()
    logger.info("[Scheduler] APScheduler started — 2 job aktif")


def stop_scheduler():
    """Dipanggil saat FastAPI shutdown."""
    scheduler = get_scheduler()
    if scheduler.running:
        scheduler.shutdown(wait=False)
        logger.info("[Scheduler] APScheduler stopped")