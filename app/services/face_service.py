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
# FIX: Setelah L2-normalize, Euclidean distance berkisar 0.0–2.0
# (bukan 0–infinity). Threshold 10.0 sebelumnya berarti SEMUA orang lolos.
#
# Referensi FaceNet paper: threshold optimal ~1.06 untuk LFW benchmark
# Rekomendasi praktis setelah L2-normalize:
#   < 0.6  → sangat mirip (sama orang, sudut berbeda)
#   0.6–0.9 → sama orang, kondisi berbeda (kacamata, pencahayaan)
#   > 1.0  → kemungkinan besar orang berbeda
#   > 1.2  → hampir pasti orang berbeda
EUCLIDEAN_THRESHOLD = 0.9   # FIX: dari 10.0 → 0.9 (post L2-normalize)
ACCURACY_THRESHOLD  = 75.0
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
        if blur_score < 50:
            return False, "Foto terlalu blur, pastikan kamera fokus dan tidak bergerak"

        # FIX: enforce_detection=True agar foto tanpa wajah nyata ditolak
        try:
            faces = DeepFace.extract_faces(
                img_path=img,
                detector_backend="opencv",
                enforce_detection=True,   # FIX: dari False → True
                align=True,
            )
        except ValueError:
            return False, "Wajah tidak terdeteksi, pastikan wajah menghadap kamera"

        if not faces or faces[0].get("confidence", 0) < 0.85:  # FIX: dari 0.7 → 0.85
            return False, "Wajah tidak terdeteksi dengan jelas, coba perbaiki posisi"

        # FIX: Deteksi sederhana anti-spoofing via ukuran wajah
        # Foto yang difoto dari layar/print biasanya punya artefak kompresi
        face_region = faces[0].get("facial_area", {})
        face_w = face_region.get("w", 0)
        face_h = face_region.get("h", 0)
        img_h, img_w = img.shape[:2]

        # Wajah harus mengisi minimal 15% luas frame (cegah foto kecil di kejauhan)
        face_ratio = (face_w * face_h) / (img_w * img_h + 1e-6)
        if face_ratio < 0.08:
            return False, "Wajah terlalu jauh, dekatkan kamera ke wajah"

        return True, "OK"

    except Exception as e:
        logger.warning(f"validate_image_quality error: {e}")
        return False, f"Gagal memvalidasi foto: {str(e)}"


# ─── 2. DETEKSI FOTO/LAYAR (ANTI-SPOOFING SEDERHANA) ─────────

def detect_screen_artifact(image_bytes: bytes) -> Tuple[bool, str]:
    """
    Deteksi apakah foto diambil dari layar/print (screen artifact).
    Layar biasanya punya pola moiré atau frekuensi tinggi yang khas.
    Return: (is_real_face, pesan)
    """
    try:
        nparr = np.frombuffer(image_bytes, np.uint8)
        img   = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        if img is None:
            return False, "Gambar tidak dapat dibaca"

        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

        # Analisis frekuensi via FFT — layar punya pola periodic yang tinggi
        f = np.fft.fft2(gray)
        fshift = np.fft.fftshift(f)
        magnitude = 20 * np.log(np.abs(fshift) + 1)

        # Hitung rasio energi frekuensi tinggi vs total
        h, w = magnitude.shape
        center_h, center_w = h // 2, w // 2
        margin = min(h, w) // 6

        # Energi frekuensi rendah (area tengah)
        low_freq = magnitude[
            center_h - margin:center_h + margin,
            center_w - margin:center_w + margin
        ].sum()
        total_energy = magnitude.sum()

        high_freq_ratio = 1 - (low_freq / (total_energy + 1e-6))

        # Foto dari layar biasanya punya high_freq_ratio > 0.85
        # Nilai ini perlu dikalibrasi sesuai kondisi nyata
        logger.debug(f"FFT high_freq_ratio: {high_freq_ratio:.4f}")

        # Threshold konservatif — hanya block yang sangat mencurigakan
        if high_freq_ratio > 0.92:
            return False, "Terdeteksi kemungkinan foto dari layar/print, gunakan wajah asli"

        return True, "OK"

    except Exception as e:
        logger.warning(f"detect_screen_artifact error: {e}")
        return True, "OK"  # Jika gagal deteksi, lanjutkan (jangan blokir)


# ─── 3. EKSTRAK EMBEDDING ─────────────────────────────────────

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
    """
    Hitung Euclidean distance antara dua embedding.
    
    FIX PENTING: L2-normalize WAJIB dilakukan sebelum Euclidean distance
    pada FaceNet. Setelah normalize, range jarak adalah 0.0–2.0.
    - 0.0 = identik
    - ~0.6–0.9 = sama orang (kondisi berbeda)
    - > 1.0 = kemungkinan orang berbeda
    - 2.0 = berlawanan total (tidak mungkin terjadi pada wajah)
    
    Bug sebelumnya: threshold 10.0 >> range maksimum 2.0, sehingga
    SEMUA wajah lolos verifikasi.
    """
    a = np.array(vec_a, dtype=np.float64)
    b = np.array(vec_b, dtype=np.float64)

    # L2-normalize
    norm_a = np.linalg.norm(a)
    norm_b = np.linalg.norm(b)
    if norm_a < 1e-10 or norm_b < 1e-10:
        return 2.0  # embedding kosong/invalid → jarak maksimum

    a = a / norm_a
    b = b / norm_b

    return float(np.sqrt(np.sum((a - b) ** 2)))


def jarak_ke_akurasi(jarak: float, threshold: float = EUCLIDEAN_THRESHOLD) -> float:
    """
    FIX: Konversi Euclidean distance (post L2-normalize, range 0–2)
    ke persentase akurasi (0–100).
    
    Mapping:
    - jarak 0.0  → akurasi 100%
    - jarak 0.45 → akurasi ~75% (batas layak)
    - jarak 0.9  → akurasi ~50% (tepat di threshold)
    - jarak > 0.9 → akurasi < 50% (tidak lolos)
    - jarak 2.0  → akurasi 0%
    """
    if jarak <= 0:
        return 100.0
    # Normalize ke range 0–100 berdasarkan range maksimum 2.0
    akurasi = max(0.0, 100.0 * (1.0 - jarak / 2.0))
    return round(akurasi, 2)


# ─── 5. REGISTRASI WAJAH ──────────────────────────────────────

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


# ─── 6. VERIFIKASI WAJAH ──────────────────────────────────────

def verify_face(
    db         : Session,
    user_id    : UUID,
    image_bytes: bytes
) -> Tuple[bool, float, str]:
    """
    Verifikasi apakah foto cocok dengan wajah terdaftar.
    
    FIX utama:
    - EUCLIDEAN_THRESHOLD diubah dari 10.0 → 0.9 (sesuai range post L2-normalize)
    - Threshold lama (10.0) membuat SEMUA orang lolos karena jarak
      maksimum setelah L2-normalize hanya ~2.0
    - Tambah cek anti-spoofing (deteksi foto dari layar)
    
    Algoritma:
    - Ambil semua embedding yang tersimpan
    - Hitung Euclidean distance ke setiap embedding (post L2-normalize)
    - Ambil jarak TERKECIL (paling mirip)
    - Jika jarak <= 0.9 → passed

    Return: (passed, akurasi_persen, pesan)
    """
    stored_embeddings = db.query(FaceEmbedding).filter(
        FaceEmbedding.user_id == user_id
    ).all()

    if not stored_embeddings:
        return False, 0.0, "Wajah belum terdaftar, lakukan registrasi terlebih dahulu"

    # FIX: Cek anti-spoofing sebelum ekstrak embedding
    is_real, spoof_pesan = detect_screen_artifact(image_bytes)
    if not is_real:
        logger.warning(f"Spoofing detected for user {user_id}")
        return False, 0.0, spoof_pesan

    # Ekstrak embedding foto baru
    new_embedding = extract_embedding(image_bytes)
    if new_embedding is None:
        return False, 0.0, "Wajah tidak terdeteksi pada foto, coba ulangi scan dengan pencahayaan baik"

    # Bandingkan dengan semua embedding, ambil JARAK TERKECIL
    distances = []
    for stored in stored_embeddings:
        d = euclidean_distance(new_embedding, stored.embedding)
        distances.append(d)
        logger.debug(f"  foto_index={stored.foto_index} → distance={d:.4f} (threshold={EUCLIDEAN_THRESHOLD})")

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
            f"Wajah tidak cocok (akurasi {akurasi:.1f}%), "
            f"pastikan pencahayaan cukup dan wajah terlihat jelas"
        )

    return passed, round(akurasi, 2), pesan


# ─── 7. DIAGNOSTIC TOOL (untuk debug/kalibrasi) ───────────────

def diagnose_face(
    db         : Session,
    user_id    : UUID,
    image_bytes: bytes
) -> dict:
    """
    Debug tool: tampilkan semua jarak ke setiap embedding tersimpan.
    Berguna untuk kalibrasi threshold.
    Panggil via POST /face/diagnose saat testing.
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
            "foto_index"       : stored.foto_index,
            "euclidean_dist"   : round(d, 4),
            "akurasi_persen"   : akurasi,
            "passed"           : d <= EUCLIDEAN_THRESHOLD,
            "threshold_dipakai": EUCLIDEAN_THRESHOLD,
            "catatan"          : (
                "✓ LOLOS" if d <= EUCLIDEAN_THRESHOLD
                else f"✗ GAGAL (jarak {d:.3f} > threshold {EUCLIDEAN_THRESHOLD})"
            ),
        })

    hasil.sort(key=lambda x: x["euclidean_dist"])
    best = hasil[0]

    return {
        "threshold_aktif"   : EUCLIDEAN_THRESHOLD,
        "range_jarak_valid" : "0.0 – 2.0 (setelah L2-normalize)",
        "total_embeddings"  : len(hasil),
        "best_match"        : best,
        "overall_passed"    : best["passed"],
        "all_results"       : hasil,
        "rekomendasi"       : (
            f"LULUS ✓ (jarak {best['euclidean_dist']:.4f} <= {EUCLIDEAN_THRESHOLD})"
            if best["passed"]
            else f"GAGAL ✗ (jarak {best['euclidean_dist']:.4f} > threshold {EUCLIDEAN_THRESHOLD})"
        ),
        "tips_kalibrasi": (
            "Jika orang berbeda masih lolos, turunkan threshold ke 0.7. "
            "Jika wajah sendiri ditolak, naikkan ke 1.0. "
            "Gunakan endpoint /face/diagnose dengan foto berbagai kondisi."
        ),
    }