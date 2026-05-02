"""app/services/audit_service.py — tulis & baca audit log."""
import json
import logging
from typing import Optional, Any, Dict
from uuid import UUID

from sqlalchemy.orm import Session

from app.models.audit_log import AuditLog

logger = logging.getLogger(__name__)


def catat(
    db        : Session,
    admin_id  : UUID,
    aksi      : str,
    entitas   : Optional[str] = None,
    entitas_id: Optional[str] = None,
    detail    : Optional[Any] = None,
    ip_address: Optional[str] = None,
) -> None:
    """
    Catat aktivitas admin ke tabel audit_log.
    Aman dipanggil di mana saja — error tidak akan menyebabkan rollback transaksi utama.

    Contoh penggunaan:
        audit_service.catat(
            db, admin.id,
            aksi="CREATE_USER",
            entitas="user",
            entitas_id=str(user.id),
            detail={"nim": user.nim_nidn, "nama": user.nama_lengkap},
        )
    """
    try:
        detail_str: Optional[str] = None
        if detail is not None:
            if isinstance(detail, (dict, list)):
                detail_str = json.dumps(detail, ensure_ascii=False, default=str)
            else:
                detail_str = str(detail)

        log = AuditLog(
            admin_id   = admin_id,
            aksi       = aksi,
            entitas    = entitas,
            entitas_id = str(entitas_id) if entitas_id else None,
            detail     = detail_str,
            ip_address = ip_address,
        )
        db.add(log)
        db.flush()   # Flush tanpa commit — ikut transaksi utama
    except Exception as e:
        logger.warning(f"Gagal catat audit log: {e}")


def get_audit_logs(
    db      : Session,
    page    : int = 1,
    limit   : int = 50,
    admin_id: Optional[UUID] = None,
    entitas : Optional[str]  = None,
    aksi    : Optional[str]  = None,
) -> Dict:
    """Ambil daftar audit log dengan pagination & filter."""
    query = db.query(AuditLog)

    if admin_id:
        query = query.filter(AuditLog.admin_id == admin_id)
    if entitas:
        query = query.filter(AuditLog.entitas == entitas)
    if aksi:
        query = query.filter(AuditLog.aksi.ilike(f"%{aksi}%"))

    total = query.count()
    logs  = (
        query
        .order_by(AuditLog.created_at.desc())
        .offset((page - 1) * limit)
        .limit(limit)
        .all()
    )

    items = []
    for log in logs:
        admin = log.admin
        items.append({
            "id"         : str(log.id),
            "admin_id"   : str(log.admin_id),
            "admin_nama" : admin.nama_lengkap if admin else "-",
            "admin_nidn" : admin.nim_nidn     if admin else "-",
            "aksi"       : log.aksi,
            "entitas"    : log.entitas,
            "entitas_id" : log.entitas_id,
            "detail"     : log.detail,
            "ip_address" : log.ip_address,
            "created_at" : log.created_at.isoformat() if log.created_at else None,
        })

    return {
        "items"      : items,
        "total"      : total,
        "page"       : page,
        "limit"      : limit,
        "total_pages": max(1, (total + limit - 1) // limit),
    }