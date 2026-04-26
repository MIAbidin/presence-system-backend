#!/usr/bin/env python3
"""
generate_secrets.py
═══════════════════
Script setup sekali pakai untuk generate SECRET_KEY yang aman
dan membuat file .env dari template .env.example

Jalankan sekali saat pertama kali setup project:
    python generate_secrets.py
"""

import secrets
import shutil
import sys
from pathlib import Path


def generate_secret_key(length: int = 64) -> str:
    """Generate kriptografis-aman secret key."""
    return secrets.token_hex(length)


def main():
    env_example = Path(".env.example")
    env_file    = Path(".env")

    # Cek .env.example ada
    if not env_example.exists():
        print("❌ .env.example tidak ditemukan. Pastikan kamu di root project.")
        sys.exit(1)

    # Cek .env sudah ada
    if env_file.exists():
        overwrite = input("⚠️  File .env sudah ada. Timpa? (y/N): ").strip().lower()
        if overwrite != "y":
            print("✓ Dibatalkan, .env tidak diubah.")
            sys.exit(0)

    # Copy template
    shutil.copy(env_example, env_file)
    print("✓ .env dibuat dari .env.example")

    # Generate SECRET_KEY baru
    new_secret = generate_secret_key(64)

    # Replace placeholder di .env
    content = env_file.read_text()
    content = content.replace(
        "GANTI_DENGAN_RANDOM_STRING_64_KARAKTER_MINIMUM",
        new_secret
    )
    env_file.write_text(content)

    print(f"✓ SECRET_KEY baru di-generate ({len(new_secret * 2)} hex chars)")
    print()
    print("═" * 60)
    print("Langkah selanjutnya:")
    print("  1. Edit .env — isi DATABASE_URL dengan password database kamu")
    print("  2. Edit .env — isi FCM_CREDENTIALS_PATH jika pakai push notif")
    print("  3. Edit .env — isi ALLOWED_ORIGINS untuk CORS")
    print("  4. Pastikan .env ada di .gitignore (sudah ditambahkan)")
    print("  5. Jalankan: uvicorn app.main:app --reload")
    print("═" * 60)
    print()
    print("⚠️  JANGAN commit .env ke git!")


if __name__ == "__main__":
    main()