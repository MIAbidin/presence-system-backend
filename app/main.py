# app/main.py

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routers import auth, face, sesi, presensi, matakuliah, mahasiswa, jadwal

app = FastAPI(
    title       = "Presensi Face Recognition API",
    description = "Backend aplikasi presensi mahasiswa berbasis wajah",
    version     = "1.0.0",
)

# CORS — izinkan request dari Flutter app
app.add_middleware(
    CORSMiddleware,
    allow_origins     = ["*"],   # di-restrict ke domain spesifik saat production
    allow_credentials = True,
    allow_methods     = ["*"],
    allow_headers     = ["*"],
)

# Daftarkan semua router
app.include_router(auth.router)
app.include_router(face.router)
app.include_router(sesi.router)
app.include_router(presensi.router)
app.include_router(matakuliah.router)
app.include_router(mahasiswa.router)   # ← baru: home-summary, profil, daftar mk
app.include_router(jadwal.router)      # ← baru: jadwal hari-ini & mingguan


@app.get("/")
def root():
    return {"message": "Backend Presensi berjalan!", "status": "ok"}
