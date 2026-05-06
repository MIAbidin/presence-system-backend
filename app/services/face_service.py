# app/services/face_service.py
# Update Fase E: EUCLIDEAN_THRESHOLD tidak lagi hardcode.
# Dibaca dari tabel konfigurasi_sistem via superadmin_service._get_threshold(db).
import io
import logging
import numpy as np
from PIL import Image
import cv2
from deepface import DeepFace
from sqlalchemy.orm import Session
from uuid import UUID
from typing import Tuple, List, Optional
from app.models.face_embedding import FaceEmbedding
from app.models.user import User

logger = logging.getLogger(__name__)

# ─── KONFIGURASI ──────────────────────────────────────────────
# Fase E: nilai aktif dibaca dari konfigurasi_sistem via _get_threshold(db).
# Konstanta ini hanya sebagai fallback jika DB belum ada konfigurasi Fase E.
EUCLIDEAN_THRESHOLD_DEFAULT = 0.9
ACCURACY_THRESHOLD          = 75.0
MIN_PHOTOS                  = 8    # fallback; nilai aktif dari _get_min_photos(db)


def _get_threshold(db: Session) -> float:
    """
    Ambil threshold face recognition dari konfigurasi_sistem.
    Fallback ke 0.9 jika tabel/key belum ada (sebelum migration Fase E).
    """
    try:
        from app.services.superadmin_service import get_face_threshold
        return get_face_threshold(db)
    except Exception as e:
        logger.debug(f"Gagal baca face_threshold dari DB ({e}), pakai default {EUCLIDEAN_THRESHOLD_DEFAULT}")
        return EUCLIDEAN_THRESHOLD_DEFAULT


def _get_min_photos(db: Session) -> int:
    """Ambil jumlah foto minimal registrasi dari konfigurasi_sistem."""
    try:
        from app.services.superadmin_service import get_max_foto_registrasi
        return get_max_foto_registrasi(db)
    except Exception:
        return MIN_PHOTOS


# ─── 1. VALIDASI KUALITAS FOTO ────────────────────────────────

def validate_image_quality(image_bytes: bytes) -> Tuple[bool, str]:
    try:
        nparr = np.frombuffer(image_bytes, np.uint8)
        img   = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

        if img is None:
            return False, "Gambar tidak dapat dibaca"

        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

        brightness = np.mean(gray)
        if brightness < 40:
            return False, "Foto terlalu gelap, cari tempat dengan pencahayaan lebih baik"
        if brightness > 220:
            return False, "Foto terlalu terang, hindari cahaya langsung ke kamera"

        blur_score = cv2.Laplacian(gray, cv2.CV_64F).var()
        if blur_score < 50:
            return False, "Foto terlalu blur, pastikan kamera fokus dan tidak bergerak"

        try:
            faces = DeepFace.extract_faces(
                img_path=img,
                detector_backend="opencv",
                enforce_detection=True,
                align=True,
            )
        except ValueError:
            return False, "Wajah tidak terdeteksi, pastikan wajah menghadap kamera"

        if not faces or faces[0].get("confidence", 0) < 0.85:
            return False, "Wajah tidak terdeteksi dengan jelas, coba perbaiki posisi"

        face_region = faces[0].get("facial_area", {})
        face_w = face_region.get("w", 0)
        face_h = face_region.get("h", 0)
        img_h, img_w = img.shape[:2]

        face_ratio = (face_w * face_h) / (img_w * img_h + 1e-6)
        if face_ratio < 0.08:
            return False, "Wajah terlalu jauh, dekatkan kamera ke wajah"

        return True, "OK"

    except Exception as e:
        logger.warning(f"validate_image_quality error: {e}")
        return False, f"Gagal memvalidasi foto: {str(e)}"


# ─── 2. ANTI-SPOOFING ─────────────────────────────────────────

def detect_screen_artifact(image_bytes: bytes) -> Tuple[bool, str]:
    try:
        nparr = np.frombuffer(image_bytes, np.uint8)
        img   = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        if img is None:
            return False, "Gambar tidak dapat dibaca"

        gray      = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        f         = np.fft.fft2(gray)
        fshift    = np.fft.fftshift(f)
        magnitude = 20 * np.log(np.abs(fshift) + 1)

        h, w = magnitude.shape
        center_h, center_w = h // 2, w // 2
        margin   = min(h, w) // 6
        low_freq = magnitude[
            center_h - margin:center_h + margin,
            center_w - margin:center_w + margin
        ].sum()
        total_energy    = magnitude.sum()
        high_freq_ratio = 1 - (low_freq / (total_energy + 1e-6))

        logger.debug(f"FFT high_freq_ratio: {high_freq_ratio:.4f}")

        if high_freq_ratio > 0.92:
            return False, "Terdeteksi kemungkinan foto dari layar/print, gunakan wajah asli"

        return True, "OK"

    except Exception as e:
        logger.warning(f"detect_screen_artifact error: {e}")
        return True, "OK"


# ─── 3. EKSTRAK EMBEDDING ─────────────────────────────────────

def extract_embedding(image_bytes: bytes) -> Optional[List[float]]:
    try:
        image     = Image.open(io.BytesIO(image_bytes)).convert("RGB")
        img_array = np.array(image)

        result = DeepFace.represent(
            img_path         = img_array,
            model_name       = "Facenet",
            detector_backend = "opencv",
            enforce_detection= True,
            align            = True,
        )

        embedding = result[0]["embedding"]
        logger.debug(f"Embedding dim: {len(embedding)}")
        return embedding

    except Exception as e:
        logger.warning(f"extract_embedding error: {e}")
        return None


# ─── 4. EUCLIDEAN DISTANCE (POST L2-NORMALIZE) ────────────────

def euclidean_distance(vec_a: List[float], vec_b: List[float]) -> float:
    a = np.array(vec_a, dtype=np.float64)
    b = np.array(vec_b, dtype=np.float64)

    norm_a = np.linalg.norm(a)
    norm_b = np.linalg.norm(b)
    if norm_a < 1e-10 or norm_b < 1e-10:
        return 2.0

    a = a / norm_a
    b = b / norm_b

    return float(np.sqrt(np.sum((a - b) ** 2)))


def jarak_ke_akurasi(jarak: float, threshold: float = EUCLIDEAN_THRESHOLD_DEFAULT) -> float:
    if jarak <= 0:
        return 100.0
    akurasi = max(0.0, 100.0 * (1.0 - jarak / 2.0))
    return round(akurasi, 2)


# ─── 5. REGISTRASI WAJAH ──────────────────────────────────────

def register_face(
    db         : Session,
    user_id    : UUID,
    image_bytes: bytes,
) -> Tuple[bool, str, int]:
    is_valid, pesan = validate_image_quality(image_bytes)
    if not is_valid:
        return False, pesan, 0

    embedding = extract_embedding(image_bytes)
    if embedding is None:
        return False, "Gagal mengekstrak fitur wajah, coba foto ulang dengan pencahayaan lebih baik", 0

    existing_count = db.query(FaceEmbedding).filter(
        FaceEmbedding.user_id == user_id
    ).count()
    foto_index = existing_count + 1

    face_emb = FaceEmbedding(
        user_id    = user_id,
        embedding  = embedding,
        foto_index = foto_index,
    )
    db.add(face_emb)

    # Fase E: min_photos dibaca dari konfigurasi_sistem
    min_photos = _get_min_photos(db)
    if foto_index >= min_photos:
        user = db.query(User).filter(User.id == user_id).first()
        if user:
            user.is_face_registered = True

    db.commit()
    logger.info(f"Face registered for user {user_id}: foto {foto_index}")
    return True, f"Foto ke-{foto_index} berhasil disimpan", foto_index


# ─── 6. VERIFIKASI WAJAH ──────────────────────────────────────

def verify_face(
    db         : Session,
    user_id    : UUID,
    image_bytes: bytes,
) -> Tuple[bool, float, str]:
    """
    Fase E: threshold dibaca dari konfigurasi_sistem (dinamis).
    Fallback ke 0.9 jika konfigurasi belum ada.
    """
    stored_embeddings = db.query(FaceEmbedding).filter(
        FaceEmbedding.user_id == user_id
    ).all()

    if not stored_embeddings:
        return False, 0.0, "Wajah belum terdaftar, lakukan registrasi terlebih dahulu"

    is_real, spoof_pesan = detect_screen_artifact(image_bytes)
    if not is_real:
        logger.warning(f"Spoofing detected for user {user_id}")
        return False, 0.0, spoof_pesan

    new_embedding = extract_embedding(image_bytes)
    if new_embedding is None:
        return False, 0.0, "Wajah tidak terdeteksi pada foto, coba ulangi scan dengan pencahayaan baik"

    # Fase E: baca threshold secara dinamis dari konfigurasi_sistem
    threshold = _get_threshold(db)

    distances = []
    for stored in stored_embeddings:
        d = euclidean_distance(new_embedding, stored.embedding)
        distances.append(d)
        logger.debug(f"  foto_index={stored.foto_index} → distance={d:.4f} (threshold={threshold})")

    best_distance = min(distances)
    akurasi       = jarak_ke_akurasi(best_distance)
    passed        = best_distance <= threshold

    logger.info(
        f"verify_face user={user_id} | "
        f"best_distance={best_distance:.4f} | "
        f"threshold={threshold} (dari konfigurasi_sistem) | "
        f"akurasi={akurasi}% | "
        f"passed={passed} | "
        f"embeddings_count={len(distances)}"
    )

    if passed:
        pesan = f"Wajah terverifikasi dengan akurasi {akurasi:.1f}%"
    else:
        pesan = (
            f"Wajah tidak cocok (akurasi {akurasi:.1f}%), "
            f"pastikan pencahayaan cukup dan wajah terlihat jelas"
        )

    return passed, round(akurasi, 2), pesan


# ─── 7. DIAGNOSTIC TOOL ───────────────────────────────────────

def diagnose_face(
    db         : Session,
    user_id    : UUID,
    image_bytes: bytes,
) -> dict:
    """Debug tool: tampilkan semua jarak ke setiap embedding tersimpan."""
    stored_embeddings = db.query(FaceEmbedding).filter(
        FaceEmbedding.user_id == user_id
    ).all()

    if not stored_embeddings:
        return {"error": "Belum ada embedding terdaftar"}

    new_embedding = extract_embedding(image_bytes)
    if new_embedding is None:
        return {"error": "Gagal ekstrak embedding dari foto scan"}

    # Fase E: threshold dinamis
    threshold = _get_threshold(db)

    hasil = []
    for stored in stored_embeddings:
        d       = euclidean_distance(new_embedding, stored.embedding)
        akurasi = jarak_ke_akurasi(d)
        hasil.append({
            "foto_index"       : stored.foto_index,
            "euclidean_dist"   : round(d, 4),
            "akurasi_persen"   : akurasi,
            "passed"           : d <= threshold,
            "threshold_dipakai": threshold,
            "catatan"          : (
                "✓ LOLOS" if d <= threshold
                else f"✗ GAGAL (jarak {d:.3f} > threshold {threshold})"
            ),
        })

    hasil.sort(key=lambda x: x["euclidean_dist"])
    best = hasil[0]

    return {
        "threshold_aktif"   : threshold,
        "sumber_threshold"  : "konfigurasi_sistem (Fase E — dinamis)",
        "range_jarak_valid" : "0.0 – 2.0 (setelah L2-normalize)",
        "total_embeddings"  : len(hasil),
        "best_match"        : best,
        "overall_passed"    : best["passed"],
        "all_results"       : hasil,
        "rekomendasi"       : (
            f"LULUS ✓ (jarak {best['euclidean_dist']:.4f} <= {threshold})"
            if best["passed"]
            else f"GAGAL ✗ (jarak {best['euclidean_dist']:.4f} > threshold {threshold})"
        ),
        "tips_kalibrasi": (
            f"Threshold saat ini: {threshold}. "
            "Ubah via Super Admin → Konfigurasi Sistem → face_threshold. "
            "Nilai lebih kecil = lebih ketat. Rekomendasi: 0.7–1.0."
        ),
    }