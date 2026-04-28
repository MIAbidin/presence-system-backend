"""
app/main.py
════════════
Update Fase 3:
- Daftarkan router dosen baru (endpoint 3.1–3.5)
- Tetap ada lifespan APScheduler dari Fase 2
"""

from contextlib import asynccontextmanager
import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routers import auth, face, sesi, presensi, matakuliah, mahasiswa, jadwal, dosen
from app.scheduler import start_scheduler, stop_scheduler

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("🚀 Server starting up...")
    start_scheduler()
    yield
    logger.info("🛑 Server shutting down...")
    stop_scheduler()


app = FastAPI(
    title       = "Presensi Face Recognition API",
    description = (
        "Backend aplikasi presensi mahasiswa berbasis wajah.\n\n"
        "Fase 3 Update:\n"
        "- Endpoint beranda dosen\n"
        "- Manajemen mahasiswa tamu (tambah/hapus manual)\n"
        "- Toggle izin tamu per matakuliah\n"
        "- Jadwal pengganti per pertemuan\n"
        "- Perbaikan endpoint peserta sesi (is_tamu, kelas_asal)"
    ),
    version     = "3.0.0",
    lifespan    = lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins     = ["*"],
    allow_credentials = True,
    allow_methods     = ["*"],
    allow_headers     = ["*"],
)

# ─── Router ───────────────────────────────────────────────────
app.include_router(auth.router)
app.include_router(face.router)
app.include_router(sesi.router)
app.include_router(presensi.router)
app.include_router(matakuliah.router)
app.include_router(mahasiswa.router)
app.include_router(jadwal.router)
app.include_router(dosen.router)   # ← BARU Fase 3


@app.get("/", tags=["Health Check"])
def root():
    return {
        "message": "Backend Presensi v3.0 berjalan!",
        "status" : "ok",
        "fase"   : "Fase 3 — Endpoint Dosen & Manajemen Tamu",
    }


@app.get("/health", tags=["Health Check"])
def health():
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