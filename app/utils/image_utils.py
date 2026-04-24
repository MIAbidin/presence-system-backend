# app/utils/image_utils.py
import io
from PIL import Image

def resize_image(image_bytes: bytes, max_size: int = 640) -> bytes:
    """
    Resize foto ke maksimal 640px (sisi terpanjang) sebelum dikirim ke DeepFace.
    Mengurangi waktu proses dan ukuran upload secara signifikan.
    """
    image = Image.open(io.BytesIO(image_bytes)).convert("RGB")
    w, h = image.size

    # Hanya resize jika memang lebih besar dari max_size
    if max(w, h) > max_size:
        ratio = max_size / max(w, h)
        new_size = (int(w * ratio), int(h * ratio))
        image = image.resize(new_size, Image.LANCZOS)

    output = io.BytesIO()
    image.save(output, format="JPEG", quality=85)
    return output.getvalue()