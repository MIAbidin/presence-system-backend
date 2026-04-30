"""
app/services/admin_service.py
══════════════════════════════
Fase 3 — Statistik dashboard
Fase 4 — CRUD user (mahasiswa & dosen), reset wajah, reset password, face diagnose
"""
from datetime import datetime, timedelta, date
from typing import List, Dict, Any, Optional, Tuple
from uuid import UUID

from sqlalchemy.orm import Session
from sqlalchemy import func, and_, or_

from app.models.user import User, UserRole
from app.models.matakuliah import Matakuliah
from app.models.sesi import SesiPresensi, SesiStatus
from app.models.presensi import Presensi, PresensiStatus
from app.models.face_embedding import FaceEmbedding


# ════════════════════════════════════════════════════════════
# FASE 3 — DASHBOARD STATS
# ════════════════════════════════════════════════════════════

def get_dashboard_stats(db: Session) -> Dict[str, Any]:
    """Semua statistik untuk beranda admin — satu fungsi, satu hit."""

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

    today_start = datetime.combine(date.today(), datetime.min.time())
    total_presensi_hari_ini = db.query(Presensi).filter(
        Presensi.created_at >= today_start
    ).count()

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
    result = []
    today  = date.today()
    for i in range(6, -1, -1):
        target  = today - timedelta(days=i)
        d_start = datetime.combine(target, datetime.min.time())
        d_end   = datetime.combine(target, datetime.max.time())

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
    mk_persen.sort(key=lambda x: x[1])

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


# ════════════════════════════════════════════════════════════
# FASE 4 — USER MANAGEMENT
# ════════════════════════════════════════════════════════════

def _user_to_dict(user: User, total_foto: int = 0) -> Dict:
    """Serialize User model ke dict yang aman untuk JSON response."""
    return {
        "id"               : str(user.id),
        "nim_nidn"         : user.nim_nidn,
        "nama_lengkap"     : user.nama_lengkap,
        "email"            : user.email,
        "role"             : user.role.value,
        "program_studi"    : user.program_studi,
        "is_face_registered": user.is_face_registered,
        "is_active"        : user.is_active,
        "total_foto_wajah" : total_foto,
        "created_at"       : user.created_at.isoformat() if user.created_at else None,
    }


def list_users(
    db     : Session,
    role   : Optional[str] = None,
    search : Optional[str] = None,
    page   : int = 1,
    limit  : int = 20,
) -> Dict:
    """
    List user dengan filter role, pencarian, dan pagination.
    """
    query = db.query(User)

    # Filter role
    if role:
        try:
            role_enum = UserRole(role)
            query = query.filter(User.role == role_enum)
        except ValueError:
            pass  # role tidak valid, abaikan filter

    # Filter search (NIM/NIDN, nama, email)
    if search:
        term = f"%{search.lower()}%"
        query = query.filter(or_(
            func.lower(User.nim_nidn).like(term),
            func.lower(User.nama_lengkap).like(term),
            func.lower(User.email).like(term),
        ))

    total = query.count()
    users = (
        query
        .order_by(User.created_at.desc())
        .offset((page - 1) * limit)
        .limit(limit)
        .all()
    )

    # Bulk count foto wajah (agar tidak N+1 query)
    user_ids = [u.id for u in users]
    foto_counts: Dict = {}
    if user_ids:
        rows = (
            db.query(FaceEmbedding.user_id, func.count(FaceEmbedding.id).label("cnt"))
            .filter(FaceEmbedding.user_id.in_(user_ids))
            .group_by(FaceEmbedding.user_id)
            .all()
        )
        foto_counts = {str(r.user_id): r.cnt for r in rows}

    return {
        "items"      : [_user_to_dict(u, foto_counts.get(str(u.id), 0)) for u in users],
        "total"      : total,
        "page"       : page,
        "limit"      : limit,
        "total_pages": max(1, (total + limit - 1) // limit),
    }


def create_user(db: Session, req) -> Tuple[bool, str, Optional[Dict]]:
    """
    Buat akun user baru.
    req harus punya: nim_nidn, nama_lengkap, email, password, role, program_studi
    """
    from app.services.auth_service import hash_password

    # Validasi role
    try:
        role_enum = UserRole(req.role)
    except ValueError:
        return False, f"Role tidak valid: {req.role}", None

    # Cek NIM/NIDN sudah ada
    if db.query(User).filter(User.nim_nidn == req.nim_nidn).first():
        return False, f"NIM/NIDN {req.nim_nidn} sudah terdaftar", None

    # Cek email sudah ada
    if db.query(User).filter(User.email == req.email).first():
        return False, f"Email {req.email} sudah terdaftar", None

    user = User(
        nim_nidn      = req.nim_nidn.strip(),
        nama_lengkap  = req.nama_lengkap.strip(),
        email         = req.email.strip().lower(),
        password_hash = hash_password(req.password),
        role          = role_enum,
        program_studi = req.program_studi.strip(),
        is_face_registered = False,
        is_active     = True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return True, f"Akun {user.nama_lengkap} berhasil dibuat", _user_to_dict(user)


def update_user(db: Session, user_id: UUID, req) -> Tuple[bool, str, Optional[Dict]]:
    """Update data user. Hanya field yang diisi (tidak None) yang diubah."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        return False, "User tidak ditemukan", None

    if req.nama_lengkap is not None:
        user.nama_lengkap = req.nama_lengkap.strip()
    if req.email is not None:
        # Cek email tidak duplikat dengan user lain
        existing = db.query(User).filter(
            User.email == req.email.strip().lower(),
            User.id    != user_id
        ).first()
        if existing:
            return False, f"Email {req.email} sudah dipakai akun lain", None
        user.email = req.email.strip().lower()
    if req.program_studi is not None:
        user.program_studi = req.program_studi.strip()
    if req.is_active is not None:
        user.is_active = req.is_active

    db.commit()
    db.refresh(user)
    return True, "Data berhasil diperbarui", _user_to_dict(user)


def soft_delete_user(db: Session, user_id: UUID) -> Tuple[bool, str]:
    """Soft delete — set is_active = False, tidak hapus data."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        return False, "User tidak ditemukan"

    user.is_active = False
    db.commit()
    return True, f"Akun {user.nama_lengkap} berhasil dinonaktifkan"


def reset_face(db: Session, user_id: UUID) -> Tuple[bool, str]:
    """Hapus semua face_embeddings dan reset flag is_face_registered."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        return False, "User tidak ditemukan"

    deleted = (
        db.query(FaceEmbedding)
        .filter(FaceEmbedding.user_id == user_id)
        .delete()
    )
    user.is_face_registered = False
    db.commit()
    return True, f"Data wajah {user.nama_lengkap} berhasil dihapus ({deleted} foto)"


def reset_password(db: Session, user_id: UUID, password_baru: str) -> Tuple[bool, str]:
    """Admin reset password tanpa perlu password lama."""
    from app.services.auth_service import hash_password

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        return False, "User tidak ditemukan"

    if len(password_baru) < 6:
        return False, "Password minimal 6 karakter"

    user.password_hash = hash_password(password_baru)
    db.commit()
    return True, f"Password {user.nama_lengkap} berhasil direset"


def get_face_diagnose_info(db: Session, user_id: UUID) -> Optional[Dict]:
    """
    Informasi diagnostik face recognition untuk mahasiswa tertentu.
    Tidak butuh foto baru — hanya menganalisis embedding tersimpan
    dan memberikan statistik kualitas.
    """
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        return None

    embeddings = (
        db.query(FaceEmbedding)
        .filter(FaceEmbedding.user_id == user_id)
        .order_by(FaceEmbedding.foto_index)
        .all()
    )

    if not embeddings:
        return {
            "user_id"          : str(user_id),
            "nama"             : user.nama_lengkap,
            "nim"              : user.nim_nidn,
            "is_face_registered": user.is_face_registered,
            "total_embeddings" : 0,
            "status"           : "Belum ada data wajah terdaftar",
            "embeddings"       : [],
            "threshold_aktif"  : 0.9,
            "rekomendasi"      : "Mahasiswa perlu melakukan registrasi wajah minimal 8 foto",
        }

    import numpy as np

    def l2_norm(vec):
        v = np.array(vec, dtype=np.float64)
        n = np.linalg.norm(v)
        return v / n if n > 1e-10 else v

    def euclidean(a, b):
        na, nb = l2_norm(a), l2_norm(b)
        return float(np.sqrt(np.sum((na - nb) ** 2)))

    # Hitung jarak antar semua pasang embedding (konsistensi internal)
    emb_vectors = [e.embedding for e in embeddings]
    pairwise_distances = []
    for i in range(len(emb_vectors)):
        for j in range(i + 1, len(emb_vectors)):
            d = euclidean(emb_vectors[i], emb_vectors[j])
            pairwise_distances.append(d)

    avg_internal = round(float(np.mean(pairwise_distances)), 4) if pairwise_distances else 0.0
    max_internal = round(float(np.max(pairwise_distances)), 4)  if pairwise_distances else 0.0

    # Kualitas konsistensi
    if avg_internal < 0.6:
        konsistensi = "Sangat Baik"
        konsistensi_color = "green"
    elif avg_internal < 0.9:
        konsistensi = "Baik"
        konsistensi_color = "blue"
    elif avg_internal < 1.2:
        konsistensi = "Cukup"
        konsistensi_color = "amber"
    else:
        konsistensi = "Buruk — perlu registrasi ulang"
        konsistensi_color = "red"

    rekomendasi = []
    if len(embeddings) < 8:
        rekomendasi.append(f"Tambah {8 - len(embeddings)} foto lagi (minimal 8 foto)")
    if avg_internal > 1.0:
        rekomendasi.append("Konsistensi embedding rendah — coba registrasi ulang di kondisi pencahayaan berbeda")
    if max_internal > 1.5:
        rekomendasi.append("Ada embedding yang sangat berbeda — kemungkinan ada foto blur atau wajah lain")
    if not rekomendasi:
        rekomendasi.append("Data wajah dalam kondisi baik. Jika masih gagal verifikasi, cek threshold (saat ini 0.9)")

    return {
        "user_id"            : str(user_id),
        "nama"               : user.nama_lengkap,
        "nim"                : user.nim_nidn,
        "is_face_registered" : user.is_face_registered,
        "total_embeddings"   : len(embeddings),
        "threshold_aktif"    : 0.9,
        "range_jarak_valid"  : "0.0 – 2.0 (setelah L2-normalize)",
        "konsistensi_internal": {
            "rata_rata_jarak": avg_internal,
            "jarak_maksimum" : max_internal,
            "status"         : konsistensi,
            "warna"          : konsistensi_color,
            "keterangan"     : (
                "Jarak antar embedding terdaftar. Semakin kecil = foto-foto registrasi lebih konsisten "
                "dan akurasi verifikasi lebih tinggi."
            ),
        },
        "embeddings": [
            {
                "foto_index": e.foto_index,
                "embedding_id": str(e.id),
                "created_at": e.created_at.isoformat() if e.created_at else None,
            }
            for e in embeddings
        ],
        "rekomendasi": rekomendasi,
    }