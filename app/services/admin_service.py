"""
app/services/admin_service.py
Fase 3 — Business logic beranda admin dashboard
"""
from datetime import datetime, timedelta, date
from typing import List, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import func, and_

from app.models.user import User, UserRole
from app.models.matakuliah import Matakuliah
from app.models.sesi import SesiPresensi, SesiStatus
from app.models.presensi import Presensi, PresensiStatus


def get_dashboard_stats(db: Session) -> Dict[str, Any]:
    """Semua statistik untuk beranda admin — satu fungsi, satu hit."""

    # 1. Statistik dasar
    total_mahasiswa = db.query(User).filter(
        User.role == UserRole.mahasiswa, User.is_active == True
    ).count()
    total_dosen = db.query(User).filter(
        User.role == UserRole.dosen, User.is_active == True
    ).count()
    total_matakuliah = db.query(Matakuliah).count()
    total_sesi_aktif = db.query(SesiPresensi).filter(
        SesiPresensi.status == SesiStatus.aktif
    ).count()

    # 2. Presensi hari ini
    today_start = datetime.combine(date.today(), datetime.min.time())
    total_presensi_hari_ini = db.query(Presensi).filter(
        Presensi.created_at >= today_start
    ).count()

    # 3. Rata-rata akurasi wajah
    akurasi_avg = db.query(func.avg(Presensi.akurasi_wajah)).filter(
        Presensi.akurasi_wajah.isnot(None)
    ).scalar()
    akurasi_rata_rata = round(float(akurasi_avg), 1) if akurasi_avg else 0.0

    return {
        "total_mahasiswa"          : total_mahasiswa,
        "total_dosen"              : total_dosen,
        "total_matakuliah"         : total_matakuliah,
        "total_presensi_hari_ini"  : total_presensi_hari_ini,
        "total_sesi_aktif"         : total_sesi_aktif,
        "akurasi_rata_rata"        : akurasi_rata_rata,
        "grafik_kehadiran_7_hari"  : _get_grafik_7_hari(db),
        "distribusi_status"        : _get_distribusi_status(db),
        "top_mk_kehadiran_terendah": _get_top_mk_kehadiran_terendah(db),
        "scheduler_status"         : _get_scheduler_status(),
    }


def _get_grafik_7_hari(db: Session) -> List[Dict]:
    """Jumlah presensi per hari untuk 7 hari terakhir."""
    result = []
    today  = date.today()
    for i in range(6, -1, -1):
        target   = today - timedelta(days=i)
        d_start  = datetime.combine(target, datetime.min.time())
        d_end    = datetime.combine(target, datetime.max.time())

        hadir = db.query(Presensi).filter(and_(
            Presensi.created_at >= d_start,
            Presensi.created_at <= d_end,
            Presensi.status.in_([PresensiStatus.hadir, PresensiStatus.terlambat])
        )).count()

        absen = db.query(Presensi).filter(and_(
            Presensi.created_at >= d_start,
            Presensi.created_at <= d_end,
            Presensi.status == PresensiStatus.absen
        )).count()

        result.append({
            "tanggal"    : target.strftime("%d %b"),
            "tanggal_iso": target.isoformat(),
            "hadir"      : hadir,
            "absen"      : absen,
        })
    return result


def _get_distribusi_status(db: Session) -> List[Dict]:
    """Distribusi status kehadiran (semua waktu)."""
    rows  = db.query(
        Presensi.status, func.count(Presensi.id).label("jumlah")
    ).group_by(Presensi.status).all()
    total = sum(r.jumlah for r in rows)
    COLOR = {
        "hadir": "#22c55e", "terlambat": "#f59e0b",
        "absen": "#ef4444", "izin": "#3b82f6", "sakit": "#a855f7",
    }
    return [{
        "status": r.status.value,
        "jumlah": r.jumlah,
        "persen": round(r.jumlah / total * 100, 1) if total else 0.0,
        "warna" : COLOR.get(r.status.value, "#64748b"),
    } for r in rows]


def _get_top_mk_kehadiran_terendah(db: Session, limit: int = 5) -> List[Dict]:
    """Top 5 matakuliah dengan persentase kehadiran terendah."""
    sesi_selesai = db.query(SesiPresensi).filter(
        SesiPresensi.status == SesiStatus.selesai
    ).all()
    if not sesi_selesai:
        return []

    sesi_ids    = [s.id for s in sesi_selesai]
    sesi_mk_map = {s.id: s.matakuliah_id for s in sesi_selesai}

    all_presensi = db.query(Presensi).filter(
        Presensi.sesi_id.in_(sesi_ids)
    ).all()

    mk_stats: Dict = {}
    for p in all_presensi:
        mk_id = sesi_mk_map.get(p.sesi_id)
        if not mk_id:
            continue
        if mk_id not in mk_stats:
            mk_stats[mk_id] = {"total": 0, "hadir": 0}
        mk_stats[mk_id]["total"] += 1
        if p.status in (PresensiStatus.hadir, PresensiStatus.terlambat):
            mk_stats[mk_id]["hadir"] += 1

    mk_persen = [
        (mk_id, round(s["hadir"] / s["total"] * 100, 1), s["total"])
        for mk_id, s in mk_stats.items() if s["total"] > 0
    ]
    mk_persen.sort(key=lambda x: x[1])  # ascending — terendah duluan

    top_ids = [x[0] for x in mk_persen[:limit]]
    mk_map  = {
        mk.id: mk for mk in
        db.query(Matakuliah).filter(Matakuliah.id.in_(top_ids)).all()
    }

    return [
        {
            "matakuliah_id" : str(mk_id),
            "kode"          : mk_map[mk_id].kode,
            "nama"          : mk_map[mk_id].nama,
            "persentase"    : persen,
            "total_presensi": total,
        }
        for mk_id, persen, total in mk_persen[:limit]
        if mk_id in mk_map
    ]


def _get_scheduler_status() -> Dict:
    """Status APScheduler yang sedang berjalan."""
    try:
        from app.scheduler import get_scheduler
        scheduler  = get_scheduler()
        is_running = scheduler.running
        jobs = [
            {
                "id"           : j.id,
                "name"         : j.name,
                "next_run_time": j.next_run_time.isoformat()
                                 if j.next_run_time else None,
            }
            for j in scheduler.get_jobs()
        ] if is_running else []
        return {
            "running": is_running,
            "status" : "running" if is_running else "stopped",
            "jobs"   : jobs,
        }
    except Exception:
        return {"running": False, "status": "unknown", "jobs": []}
