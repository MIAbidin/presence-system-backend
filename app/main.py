"""
app/main.py
════════════
Update Fase 2:
- Tambah lifespan context manager untuk start/stop APScheduler
- Daftarkan semua router termasuk yang baru (dosen)
"""

from contextlib import asynccontextmanager
import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routers import auth, face, sesi, presensi, matakuliah, mahasiswa, jadwal
from app.scheduler import start_scheduler, stop_scheduler

logger = logging.getLogger(__name__)


# ─── LIFESPAN — startup & shutdown ────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Startup: jalankan APScheduler
    Shutdown: hentikan scheduler dengan graceful
    """
    logger.info("🚀 Server starting up...")
    start_scheduler()
    yield
    logger.info("🛑 Server shutting down...")
    stop_scheduler()


# ─── INISIALISASI FASTAPI ─────────────────────────────────────

app = FastAPI(
    title       = "Presensi Face Recognition API",
    description = (
        "Backend aplikasi presensi mahasiswa berbasis wajah.\n\n"
        "Fase 2 Update:\n"
        "- Sesi otomatis tutup sesuai jam selesai matakuliah\n"
        "- Logika mahasiswa tamu (izin_tamu)\n"
        "- Batas terlambat kini bisa None (tidak ada batas)\n"
        "- APScheduler untuk otomasi"
    ),
    version     = "2.0.0",
    lifespan    = lifespan,
)

# ─── CORS ─────────────────────────────────────────────────────

app.add_middleware(
    CORSMiddleware,
    allow_origins     = ["*"],   # restrict ke domain spesifik saat production
    allow_credentials = True,
    allow_methods     = ["*"],
    allow_headers     = ["*"],
)

# ─── DAFTARKAN SEMUA ROUTER ───────────────────────────────────

app.include_router(auth.router)
app.include_router(face.router)
app.include_router(sesi.router)
app.include_router(presensi.router)
app.include_router(matakuliah.router)
app.include_router(mahasiswa.router)
app.include_router(jadwal.router)

# Fase 3 nanti akan tambah:
# from app.routers import dosen
# app.include_router(dosen.router)


@app.get("/", tags=["Health Check"])
def root():
    return {
        "message": "Backend Presensi v2.0 berjalan!",
        "status" : "ok",
        "fase"   : "Fase 2 — Logika Sesi & Tamu",
    }


@app.get("/health", tags=["Health Check"])
def health():
    """Endpoint untuk monitoring uptime."""
    from app.scheduler import get_scheduler
    scheduler = get_scheduler()
    jobs = [
        {"id": j.id, "name": j.name, "next_run": str(j.next_run_time)}
        for j in scheduler.get_jobs()
    ] if scheduler.running else []

    return {
        "status"   : "ok",
        "scheduler": "running" if scheduler.running else "stopped",
        "jobs"     : jobs,
    }