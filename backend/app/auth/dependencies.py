"""
FastAPI dependencies for Telegram WebApp authentication.

Usage:
    @app.get("/api/protected")
    def protected(user: dict = Depends(get_telegram_user)):
        return {"telegram_id": user["id"]}
"""
import os
import logging
from fastapi import Header, HTTPException, Depends
from .telegram import verify_telegram_init_data

logger = logging.getLogger(__name__)

_BOT_TOKEN: str | None = os.getenv("TELEGRAM_BOT_TOKEN")


async def get_telegram_user(x_init_data: str = Header(default="")) -> dict:
    """
    Dependency that validates X-Init-Data header and returns the Telegram user dict.

    If initData is absent (browser access), returns an anonymous user instead of raising.
    Raises 401 only if initData is present but invalid.
    Raises 503 if TELEGRAM_BOT_TOKEN is not configured server-side.
    """
    # Browser mode: no initData provided — allow as anonymous user
    if not x_init_data:
        return {"id": 0, "first_name": "anonymous", "source": "browser"}

    if not _BOT_TOKEN:
        logger.error("TELEGRAM_BOT_TOKEN is not set — cannot validate Telegram auth")
        raise HTTPException(status_code=503, detail="Telegram auth not configured on server")

    try:
        return verify_telegram_init_data(x_init_data, _BOT_TOKEN)
    except ValueError as e:
        raise HTTPException(status_code=401, detail=f"Invalid Telegram initData: {e}")
