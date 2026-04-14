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

    openrouter_configured = bool(os.getenv("OPENROUTER_API_KEY"))

    overall = "ok" if (db_status == "connected" and openrouter_configured) else "degraded"

    return {
        "status": overall,
        "uptime_seconds": uptime_seconds,
        "database": db_status,
        "database_error": db_error,
        "ai_openrouter": "configured" if openrouter_configured else "not_configured",
    }
