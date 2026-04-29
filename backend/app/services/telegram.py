import logging
import os

import httpx

logger = logging.getLogger(__name__)

# Frontline bot (TMA + push notifications to employees).
# FRONTLINE_BOT_TOKEN is preferred; TELEGRAM_BOT_TOKEN kept as fallback during the split.
BOT_TOKEN = os.getenv("FRONTLINE_BOT_TOKEN") or os.getenv("TELEGRAM_BOT_TOKEN", "")
BOT_USERNAME = os.getenv("FRONTLINE_BOT_USERNAME", "VyudFrontlineBot")


def send_telegram_message(chat_id: str, text: str) -> bool:
    if not BOT_TOKEN:
        logger.warning("FRONTLINE_BOT_TOKEN/TELEGRAM_BOT_TOKEN not set — skipping push")
        return False
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    try:
        r = httpx.post(
            url,
            json={"chat_id": chat_id, "text": text, "parse_mode": "HTML"},
            timeout=5,
        )
        if r.status_code != 200:
            logger.warning("Telegram push failed: %s %s", r.status_code, r.text)
        return r.status_code == 200
    except Exception as e:
        logger.error("Telegram push error: %s", e)
        return False
