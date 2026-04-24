import io
import numpy as np
from PIL import Image
import cv2
from deepface import DeepFace
from sqlalchemy.orm import Session
from uuid import UUID
from typing import Tuple, List, Optional
from app.models.face_embedding import FaceEmbedding
from app.models.user import User

# Threshold akurasi minimum — sesuai SKS: >= 85%
ACCURACY_THRESHOLD = 85.0
# Jumlah foto minimum untuk registrasi dianggap selesai
MIN_PHOTOS = 8


# ─── 1. VALIDASI KUALITAS FOTO ────────────────────────────

def validate_image_quality(image_bytes: bytes) -> Tuple[bool, str]:
    """
    Validasi foto sebelum diproses:
    - Cek minimal 1 wajah terdeteksi
    - Cek tidak blur (Laplacian variance)
    - Cek kecerahan tidak terlalu gelap/terang
    Return: (is_valid, pesan_error)
    """
    try:
        # Konversi bytes ke numpy array untuk OpenCV
        nparr = np.frombuffer(image_bytes, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

        if img is None:
            return False, "Gambar tidak dapat dibaca"

        # ── Cek kecerahan (brightness) ────────────────────
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        brightness = np.mean(gray)
        if brightness < 40:
            return False, "Foto terlalu gelap, cari tempat dengan pencahayaan lebih baik"
        if brightness > 220:
            return False, "Foto terlalu terang, hindari cahaya langsung ke kamera"

        # ── Cek blur (Laplacian variance) ────────────────
        blur_score = cv2.Laplacian(gray, cv2.CV_64F).var()
        if blur_score < 80:
            return False, "Foto terlalu blur, pastikan kamera fokus dan tidak bergerak"

        # ── Cek ada wajah menggunakan DeepFace ───────────
        faces = DeepFace.extract_faces(
            img_path=img,
            detector_backend="opencv",
            enforce_detection=False
        )
        if not faces or faces[0]["confidence"] < 0.8:
            return False, "Wajah tidak terdeteksi, pastikan wajah menghadap kamera dengan jelas"

        return True, "OK"

    except Exception as e:
        return False, f"Gagal memvalidasi foto: {str(e)}"


# ─── 2. EKSTRAK EMBEDDING ─────────────────────────────────

def extract_embedding(image_bytes: bytes) -> Optional[List[float]]:
    """
    Ekstrak vektor embedding 128 dimensi dari foto wajah menggunakan FaceNet.
    Return list of float (128 angka), atau None jika gagal.
    """
    try:
        # Konversi bytes ke PIL Image lalu ke numpy
        image = Image.open(io.BytesIO(image_bytes)).convert("RGB")
        img_array = np.array(image)

        # Ekstrak embedding dengan model FaceNet via DeepFace
        result = DeepFace.represent(
            img_path=img_array,
            model_name="Facenet",       # model 128 dimensi
            detector_backend="opencv",   # detector cepat
            enforce_detection=True
        )

        # result adalah list, ambil embedding dari index pertama
        embedding = result[0]["embedding"]  # list 128 float
        return embedding

    except Exception:
        return None


# ─── 3. COSINE SIMILARITY ─────────────────────────────────

def cosine_similarity(vec_a: List[float], vec_b: List[float]) -> float:
    """
    Hitung kemiripan dua vektor embedding (0.0 = berbeda, 1.0 = identik).
    Dikonversi ke skala 0-100 untuk kemudahan baca.
    """
    a = np.array(vec_a)
    b = np.array(vec_b)
    similarity = np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b))
    # Konversi ke persentase (0–100)
    return float(np.clip(similarity * 100, 0, 100))


# ─── 4. REGISTRASI WAJAH ──────────────────────────────────

def register_face(
    db: Session,
    user_id: UUID,
    image_bytes: bytes
) -> Tuple[bool, str, int]:
    """
    Proses registrasi satu foto wajah:
    1. Validasi kualitas foto
    2. Ekstrak embedding
    3. Simpan ke database
    4. Update is_face_registered jika sudah >= 8 foto

    Return: (success, pesan, jumlah_foto_tersimpan)
    """
    # Langkah 1: validasi
    is_valid, pesan = validate_image_quality(image_bytes)
    if not is_valid:
        return False, pesan, 0

    # Langkah 2: ekstrak embedding
    embedding = extract_embedding(image_bytes)
    if embedding is None:
        return False, "Gagal mengekstrak fitur wajah, coba foto ulang", 0

    # Hitung foto_index (urutan foto ke berapa)
    existing_count = db.query(FaceEmbedding).filter(
        FaceEmbedding.user_id == user_id
    ).count()
    foto_index = existing_count + 1

    # Langkah 3: simpan ke database
    face_emb = FaceEmbedding(
        user_id    = user_id,
        embedding  = embedding,
        foto_index = foto_index
    )
    db.add(face_emb)

    # Langkah 4: update flag is_face_registered jika sudah cukup
    if foto_index >= MIN_PHOTOS:
        user = db.query(User).filter(User.id == user_id).first()
        if user:
            user.is_face_registered = True

    db.commit()
    return True, f"Foto ke-{foto_index} berhasil disimpan", foto_index


# ─── 5. VERIFIKASI WAJAH ──────────────────────────────────

def verify_face(
    db: Session,
    user_id: UUID,
    image_bytes: bytes
) -> Tuple[bool, float, str]:
    """
    Verifikasi apakah foto yang dikirim cocok dengan wajah terdaftar.
    Bandingkan dengan SEMUA embedding user, ambil skor tertinggi.

    Return: (passed, akurasi, pesan)
    """
    # Ambil semua embedding yang tersimpan untuk user ini
    stored_embeddings = db.query(FaceEmbedding).filter(
        FaceEmbedding.user_id == user_id
    ).all()

    if not stored_embeddings:
        return False, 0.0, "Wajah belum terdaftar, lakukan registrasi terlebih dahulu"

    # Ekstrak embedding dari foto yang masuk
    new_embedding = extract_embedding(image_bytes)
    if new_embedding is None:
        return False, 0.0, "Wajah tidak terdeteksi pada foto, coba ulangi scan"

    # Bandingkan dengan semua embedding, ambil skor tertinggi
    scores = []
    for stored in stored_embeddings:
        score = cosine_similarity(new_embedding, stored.embedding)
        scores.append(score)

    best_score = max(scores)
    passed = best_score >= ACCURACY_THRESHOLD

    if passed:
        pesan = f"Wajah terverifikasi dengan akurasi {best_score:.1f}%"
    else:
        pesan = f"Wajah tidak cocok (akurasi {best_score:.1f}%, minimum {ACCURACY_THRESHOLD}%)"

    return passed, round(best_score, 2), pesan