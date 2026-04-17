"""
Telegram WebApp initData verification.

Implements the official HMAC-SHA256 algorithm from:
https://core.telegram.org/bots/webapps#validating-data-received-via-the-mini-app
"""
import hashlib
import hmac
import json
from urllib.parse import unquote, parse_qsl


def verify_telegram_init_data(init_data: str, bot_token: str) -> dict:
    """
    Verify Telegram WebApp initData and return parsed user data.

    Raises ValueError if the signature is invalid or required fields are missing.
    """
    if not init_data:
        raise ValueError("Empty initData")

    params = dict(parse_qsl(init_data, keep_blank_values=True))
    received_hash = params.pop("hash", None)
    if not received_hash:
        raise ValueError("Missing hash in initData")

    # Build data-check string: sorted key=value pairs joined by \n
    data_check_string = "\n".join(
        f"{k}={v}" for k, v in sorted(params.items())
    )

    # secret_key = HMAC-SHA256("WebAppData", bot_token)
    secret_key = hmac.new(
        b"WebAppData", bot_token.encode(), hashlib.sha256
    ).digest()

    expected_hash = hmac.new(
        secret_key, data_check_string.encode(), hashlib.sha256
    ).hexdigest()

    if not hmac.compare_digest(expected_hash, received_hash):
        raise ValueError("Invalid initData signature")

    # Parse user JSON from the verified params
    user_raw = params.get("user")
    if not user_raw:
        raise ValueError("No user field in initData")

    try:
        user = json.loads(unquote(user_raw))
    except (json.JSONDecodeError, ValueError) as e:
        raise ValueError(f"Failed to parse user JSON: {e}") from e

    return user
