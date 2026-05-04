"""
app/main.py — Update Fase 11
"""
from contextlib import asynccontextmanager
import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routers import (
    auth, face, sesi, presensi,
    matakuliah, mahasiswa, jadwal, dosen, admin, admin_import, admin_laporan, admin_audit,admin_ruangan, admin_kelas, admin_import_jadwal
)
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
    description = "Backend aplikasi presensi mahasiswa berbasis wajah. Fase 11.",
    version     = "3.2.0",
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
app.include_router(dosen.router)
app.include_router(admin.router)
app.include_router(admin_import.router)
app.include_router(admin_laporan.router)
app.include_router(admin_audit.router)
app.include_router(admin_ruangan.router)
app.include_router(admin_kelas.router)
app.include_router(admin_import_jadwal.router)

@app.get("/", tags=["Health Check"])
def root():
    return {
        "message": "Backend Presensi v3.2 berjalan!",
        "status" : "ok",
    }


@app.get("/health", tags=["Health Check"])
def health():
    from app.scheduler import get_scheduler
    scheduler = get_scheduler()
    jobs = [
        {
            "id"           : j.id,
            "name"         : j.name,
            "next_run_time": str(j.next_run_time),
            "trigger"      : str(j.trigger),
        }
        for j in scheduler.get_jobs()
    ] if scheduler.running else []
    return {
        "status"   : "ok",
        "scheduler": "running" if scheduler.running else "stopped",
        "jobs"     : jobs,
    }