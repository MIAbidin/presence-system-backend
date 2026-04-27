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
# Threshold untuk FaceNet dengan Euclidean distance (BUKAN cosine)
# Nilai lebih kecil = lebih mirip (jarak 0 = identik)
# Referensi DeepFace: threshold default FaceNet = 10.0
EUCLIDEAN_THRESHOLD = 10.0   # jika jarak <= ini → wajah cocok
ACCURACY_THRESHOLD  = 75.0   # persentase minimum yang ditampilkan ke user
MIN_PHOTOS          = 8


# ─── 1. VALIDASI KUALITAS FOTO ────────────────────────────────

def validate_image_quality(image_bytes: bytes) -> Tuple[bool, str]:
    try:
        nparr = np.frombuffer(image_bytes, np.uint8)
        img   = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

        if img is None:
            return False, "Gambar tidak dapat dibaca"

        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

        # Cek kecerahan
        brightness = np.mean(gray)
        if brightness < 40:
            return False, "Foto terlalu gelap, cari tempat dengan pencahayaan lebih baik"
        if brightness > 220:
            return False, "Foto terlalu terang, hindari cahaya langsung ke kamera"

        # Cek blur
        blur_score = cv2.Laplacian(gray, cv2.CV_64F).var()
        if blur_score < 50:   # dikurangi dari 80 → lebih toleran
            return False, "Foto terlalu blur, pastikan kamera fokus dan tidak bergerak"

        # Cek ada wajah
        faces = DeepFace.extract_faces(
            img_path=img,
            detector_backend="opencv",
            enforce_detection=False,
            align=True,
        )
        if not faces or faces[0]["confidence"] < 0.7:   # turunkan dari 0.8
            return False, "Wajah tidak terdeteksi, pastikan wajah menghadap kamera"

        return True, "OK"

    except Exception as e:
        logger.warning(f"validate_image_quality error: {e}")
        return False, f"Gagal memvalidasi foto: {str(e)}"


# ─── 2. EKSTRAK EMBEDDING ─────────────────────────────────────

def extract_embedding(image_bytes: bytes) -> Optional[List[float]]:
    """
    Ekstrak embedding menggunakan FaceNet via DeepFace.
    Return list of float (128 dimensi), atau None jika gagal.
    """
    try:
        image     = Image.open(io.BytesIO(image_bytes)).convert("RGB")
        img_array = np.array(image)

        result = DeepFace.represent(
            img_path         = img_array,
            model_name       = "Facenet",
            detector_backend = "opencv",
            enforce_detection= True,
            align            = True,   # penting untuk akurasi
        )

        embedding = result[0]["embedding"]
        logger.debug(f"Embedding dim: {len(embedding)}")
        return embedding

    except Exception as e:
        logger.warning(f"extract_embedding error: {e}")
        return None


# ─── 3. EUCLIDEAN DISTANCE (BUKAN COSINE) ─────────────────────

def euclidean_distance(vec_a: List[float], vec_b: List[float]) -> float:
    """
    Hitung Euclidean distance antara dua embedding.
    FaceNet dirancang untuk Euclidean distance, BUKAN cosine similarity.
    Nilai lebih kecil = lebih mirip (0 = identik).
    """
    a = np.array(vec_a)
    b = np.array(vec_b)

    # L2-normalize dulu (best practice FaceNet)
    a = a / (np.linalg.norm(a) + 1e-10)
    b = b / (np.linalg.norm(b) + 1e-10)

    return float(np.sqrt(np.sum((a - b) ** 2)))


def jarak_ke_akurasi(jarak: float, threshold: float = EUCLIDEAN_THRESHOLD) -> float:
    """
    Konversi Euclidean distance ke persentase akurasi (0–100).
    Jarak 0    → akurasi 100%
    Jarak = threshold → akurasi ~50%
    Jarak >> threshold → akurasi mendekati 0%
    """
    if jarak <= 0:
        return 100.0
    # Rumus: semakin kecil jarak, semakin tinggi akurasi
    # Normalize: jika jarak = threshold, akurasi = 50
    akurasi = max(0.0, 100.0 * (1.0 - jarak / (threshold * 2)))
    return round(akurasi, 2)


# ─── 4. REGISTRASI WAJAH ──────────────────────────────────────

def register_face(
    db        : Session,
    user_id   : UUID,
    image_bytes: bytes
) -> Tuple[bool, str, int]:
    """
    Proses registrasi satu foto wajah.
    Return: (success, pesan, jumlah_foto_tersimpan)
    """
    # Validasi kualitas
    is_valid, pesan = validate_image_quality(image_bytes)
    if not is_valid:
        return False, pesan, 0

    # Ekstrak embedding
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
        foto_index = foto_index
    )
    db.add(face_emb)

    if foto_index >= MIN_PHOTOS:
        user = db.query(User).filter(User.id == user_id).first()
        if user:
            user.is_face_registered = True

    db.commit()
    logger.info(f"Face registered for user {user_id}: foto {foto_index}")
    return True, f"Foto ke-{foto_index} berhasil disimpan", foto_index


# ─── 5. VERIFIKASI WAJAH ──────────────────────────────────────

def verify_face(
    db         : Session,
    user_id    : UUID,
    image_bytes: bytes
) -> Tuple[bool, float, str]:
    """
    Verifikasi apakah foto cocok dengan wajah terdaftar.
    
    Algoritma:
    - Ambil semua embedding yang tersimpan
    - Hitung Euclidean distance ke setiap embedding
    - Ambil jarak TERKECIL (paling mirip)
    - Jika jarak <= EUCLIDEAN_THRESHOLD → passed
    
    Return: (passed, akurasi_persen, pesan)
    """
    stored_embeddings = db.query(FaceEmbedding).filter(
        FaceEmbedding.user_id == user_id
    ).all()

    if not stored_embeddings:
        return False, 0.0, "Wajah belum terdaftar, lakukan registrasi terlebih dahulu"

    # Ekstrak embedding foto baru
    new_embedding = extract_embedding(image_bytes)
    if new_embedding is None:
        return False, 0.0, "Wajah tidak terdeteksi pada foto, coba ulangi scan dengan pencahayaan baik"

    # Bandingkan dengan semua embedding, ambil JARAK TERKECIL
    distances = []
    for stored in stored_embeddings:
        d = euclidean_distance(new_embedding, stored.embedding)
        distances.append(d)
        logger.debug(f"  foto_index={stored.foto_index} → distance={d:.4f}")

    best_distance = min(distances)
    akurasi       = jarak_ke_akurasi(best_distance)
    passed        = best_distance <= EUCLIDEAN_THRESHOLD

    logger.info(
        f"verify_face user={user_id} | "
        f"best_distance={best_distance:.4f} | "
        f"threshold={EUCLIDEAN_THRESHOLD} | "
        f"akurasi={akurasi}% | "
        f"passed={passed} | "
        f"embeddings_count={len(distances)}"
    )

    if passed:
        pesan = f"Wajah terverifikasi dengan akurasi {akurasi:.1f}%"
    else:
        pesan = (
            f"Wajah tidak cocok — jarak={best_distance:.2f}, "
            f"threshold={EUCLIDEAN_THRESHOLD} (akurasi={akurasi:.1f}%)"
        )

    return passed, round(akurasi, 2), pesan


# ─── 6. DIAGNOSTIC TOOL (untuk debug) ────────────────────────

def diagnose_face(
    db         : Session,
    user_id    : UUID,
    image_bytes: bytes
) -> dict:
    """
    Endpoint debug: tampilkan semua jarak ke setiap embedding tersimpan.
    Panggil via GET /face/diagnose saat testing.
    """
    stored_embeddings = db.query(FaceEmbedding).filter(
        FaceEmbedding.user_id == user_id
    ).all()

    if not stored_embeddings:
        return {"error": "Belum ada embedding terdaftar"}

    new_embedding = extract_embedding(image_bytes)
    if new_embedding is None:
        return {"error": "Gagal ekstrak embedding dari foto scan"}

    hasil = []
    for stored in stored_embeddings:
        d       = euclidean_distance(new_embedding, stored.embedding)
        akurasi = jarak_ke_akurasi(d)
        hasil.append({
            "foto_index"     : stored.foto_index,
            "euclidean_dist" : round(d, 4),
            "akurasi_persen" : akurasi,
            "passed"         : d <= EUCLIDEAN_THRESHOLD,
        })

    hasil.sort(key=lambda x: x["euclidean_dist"])
    best = hasil[0]

    return {
        "threshold"         : EUCLIDEAN_THRESHOLD,
        "total_embeddings"  : len(hasil),
        "best_match"        : best,
        "overall_passed"    : best["passed"],
        "all_results"       : hasil,
        "rekomendasi"       : (
            "LULUS ✓" if best["passed"]
            else f"GAGAL — perlu jarak <= {EUCLIDEAN_THRESHOLD}, dapat {best['euclidean_dist']}"
        ),
    }