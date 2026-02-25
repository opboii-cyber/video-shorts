"""
main.py — FastAPI Application Entry Point
==========================================

Boots the API, configures CORS, registers routers, and inits the DB.
Run with:  uvicorn main:app --reload --port 8000
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from routers import upload, process
from config import OUTPUT_DIR
from database import init_db

# ── Create the FastAPI application ───────────────────────────
app = FastAPI(
    title="Video Shorts SaaS",
    description="Convert long-form landscape video into viral vertical shorts",
    version="0.2.0",
)

# ── CORS — allow the Next.js frontend to call us ────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Serve processed videos as static files ───────────────────
app.mount("/outputs", StaticFiles(directory=str(OUTPUT_DIR)), name="outputs")

# ── Register API routers ─────────────────────────────────────
app.include_router(upload.router, prefix="/api", tags=["upload"])
app.include_router(process.router, prefix="/api", tags=["process"])

# Import payment & job routers if available
try:
    from routers import payments, jobs
    app.include_router(payments.router, prefix="/api", tags=["payments"])
    app.include_router(jobs.router, prefix="/api", tags=["jobs"])
except ImportError:
    pass


# ── Startup event — create DB tables ─────────────────────────
@app.on_event("startup")
async def on_startup():
    init_db()


@app.get("/api/health")
async def health_check():
    return {"status": "ok", "service": "video-shorts-saas", "version": "0.2.0"}
