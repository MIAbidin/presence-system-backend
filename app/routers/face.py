from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, status
from sqlalchemy.orm import Session
from uuid import UUID
from app.database.db import get_db
from app.models.user import User
from app.models.face_embedding import FaceEmbedding
from app.schemas.face import FaceRegisterResponse, FaceVerifyResponse
from app.services import face_service
from app.utils.image_utils import resize_image
from app.routers.auth import get_current_user

router = APIRouter(prefix="/face", tags=["Face Recognition"])

# Tipe file yang diizinkan
ALLOWED_TYPES = {"image/jpeg", "image/jpg", "image/png"}


# ─── POST /face/register ──────────────────────────────────

@router.post("/register", response_model=FaceRegisterResponse)
async def register_face(
    foto: UploadFile = File(..., description="Foto wajah (JPEG/PNG, maks 5MB)"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Upload satu foto wajah untuk registrasi.
    Mahasiswa perlu upload minimal 8 foto dari berbagai sudut.
    Setiap foto diproses terpisah, panggil endpoint ini 8–10 kali.
    """
    # Hanya mahasiswa yang bisa registrasi wajah
    if current_user.role.value != "mahasiswa":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Hanya mahasiswa yang dapat mendaftarkan wajah"
        )

    # Validasi tipe file
    if foto.content_type not in ALLOWED_TYPES:
        raise HTTPException(
            status_code=400,
            detail="Format file tidak didukung, gunakan JPEG atau PNG"
        )

    # Baca dan resize foto sebelum diproses
    image_bytes = await foto.read()
    if len(image_bytes) > 5 * 1024 * 1024:  # maks 5MB
        raise HTTPException(status_code=400, detail="Ukuran file maksimal 5MB")

    image_bytes = resize_image(image_bytes)  # resize ke maks 640px

    # Proses registrasi
    success, pesan, foto_index = face_service.register_face(
        db, current_user.id, image_bytes
    )

    if not success:
        raise HTTPException(status_code=400, detail=pesan)

    # Hitung total foto yang sudah tersimpan
    total = db.query(FaceEmbedding).filter(
        FaceEmbedding.user_id == current_user.id
    ).count()

    return FaceRegisterResponse(
        message    = pesan,
        foto_index = foto_index,
        total_terdaftar = total,
        is_complete = total >= 8
    )


# ─── POST /face/verify ────────────────────────────────────

@router.post("/verify", response_model=FaceVerifyResponse)
async def verify_face(
    foto: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Verifikasi wajah user yang sedang login.
    Dipakai saat proses presensi — dipanggil setelah kode sesi valid (mode online)
    atau setelah GPS valid (mode offline).
    """
    if not current_user.is_face_registered:
        raise HTTPException(
            status_code=400,
            detail="Wajah belum terdaftar, selesaikan registrasi terlebih dahulu"
        )

    image_bytes = await foto.read()
    image_bytes = resize_image(image_bytes)

    passed, akurasi, pesan = face_service.verify_face(db, current_user.id, image_bytes)

    return FaceVerifyResponse(
        passed        = passed,
        akurasi       = akurasi,
        mahasiswa_id  = current_user.id if passed else None,
        pesan         = pesan
    )


# ─── GET /face/status ─────────────────────────────────────

@router.get("/status")
def face_status(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Cek status registrasi wajah user yang sedang login."""
    total = db.query(FaceEmbedding).filter(
        FaceEmbedding.user_id == current_user.id
    ).count()

    return {
        "is_face_registered" : current_user.is_face_registered,
        "total_foto"         : total,
        "foto_dibutuhkan"    : max(0, 8 - total),
        "status"             : "Lengkap ✓" if total >= 8 else f"Belum lengkap ({total}/8 foto)"
    }


# ─── DELETE /face/reset ───────────────────────────────────

@router.delete("/reset")
def reset_face(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Hapus semua data wajah user dan reset flag is_face_registered.
    Dipakai saat admin ingin paksa mahasiswa daftar ulang (F-ADM-05).
    """
    db.query(FaceEmbedding).filter(FaceEmbedding.user_id == current_user.id).delete()
    current_user.is_face_registered = False
    db.commit()
    return {"message": "Data wajah berhasil dihapus, silakan daftar ulang"}