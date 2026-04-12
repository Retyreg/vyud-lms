import logging
import os
import time

from fastapi import APIRouter
from sqlalchemy import text

from app.db.base import engine

logger = logging.getLogger(__name__)

router = APIRouter(tags=["health"])

_start_time = time.time()


@router.get("/")
def read_root():
    return {"status": "ok", "message": "Backend is running!"}


@router.get("/api/health")
def health_check():
    """Return status of all system components."""
    db_status = "not_configured"
    db_error: str | None = None

    if engine is not None:
        try:
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            db_status = "connected"
        except Exception as exc:
            db_status = "error"
            logger.error("Health check DB error: %s", exc)
            db_error = "Database connection failed"

    uptime_seconds = int(time.time() - _start_time)

    groq_configured = bool(os.getenv("GROQ_API_KEY"))
    gemini_configured = bool(os.getenv("GEMINI_API_KEY"))
    ai_configured = groq_configured or gemini_configured

    overall = "ok" if (db_status == "connected" and ai_configured) else "degraded"

    return {
        "status": overall,
        "uptime_seconds": uptime_seconds,
        "database": db_status,
        "database_error": db_error,
        "ai_groq": "configured" if groq_configured else "not_configured",
        "ai_gemini": "configured" if gemini_configured else "not_configured",
    }
