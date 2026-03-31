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

    Returns the user dict on success.
    Raises 401 if validation fails.
    Raises 503 if TELEGRAM_BOT_TOKEN is not configured server-side.
    """
    if not _BOT_TOKEN:
        logger.error("TELEGRAM_BOT_TOKEN is not set — cannot validate Telegram auth")
        raise HTTPException(status_code=503, detail="Telegram auth not configured on server")

    try:
        return verify_telegram_init_data(x_init_data, _BOT_TOKEN)
    except ValueError as e:
        raise HTTPException(status_code=401, detail=f"Invalid Telegram initData: {e}")
