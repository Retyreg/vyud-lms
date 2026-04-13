"""
Tests for Telegram initData verification and FastAPI auth dependency.

Run from `backend/` directory:
    pytest tests/test_auth.py -v
"""
import hashlib
import hmac
import json
import os
import time
from urllib.parse import urlencode

import pytest

from app.auth.telegram import verify_telegram_init_data


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

BOT_TOKEN = "1234567890:ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghi"


def _make_init_data(user: dict, bot_token: str = BOT_TOKEN, tamper: bool = False) -> str:
    """Build a valid (or intentionally invalid) Telegram initData string."""
    params = {
        "user": json.dumps(user),
        "auth_date": str(int(time.time())),
        "query_id": "AAHdF6IQAAAAAN0XohDhrOrc",
    }
    data_check_string = "\n".join(f"{k}={v}" for k, v in sorted(params.items()))
    secret_key = hmac.new(b"WebAppData", bot_token.encode(), hashlib.sha256).digest()
    hash_value = hmac.new(secret_key, data_check_string.encode(), hashlib.sha256).hexdigest()
    if tamper:
        hash_value = hash_value[:-1] + ("0" if hash_value[-1] != "0" else "1")
    params["hash"] = hash_value
    return urlencode(params)


_TEST_USER = {"id": 42, "first_name": "Test", "username": "testuser"}


# ---------------------------------------------------------------------------
# verify_telegram_init_data unit tests
# ---------------------------------------------------------------------------

class TestVerifyTelegramInitData:
    def test_valid_init_data_returns_user(self):
        init_data = _make_init_data(_TEST_USER)
        user = verify_telegram_init_data(init_data, BOT_TOKEN)
        assert user["id"] == 42
        assert user["first_name"] == "Test"

    def test_tampered_hash_raises_value_error(self):
        init_data = _make_init_data(_TEST_USER, tamper=True)
        with pytest.raises(ValueError, match="Invalid initData signature"):
            verify_telegram_init_data(init_data, BOT_TOKEN)

    def test_wrong_bot_token_raises_value_error(self):
        init_data = _make_init_data(_TEST_USER, bot_token=BOT_TOKEN)
        with pytest.raises(ValueError):
            verify_telegram_init_data(init_data, "wrong_token")

    def test_missing_hash_raises_value_error(self):
        with pytest.raises(ValueError, match="Missing hash"):
            verify_telegram_init_data("auth_date=1234567890&user=%7B%22id%22%3A1%7D", BOT_TOKEN)

    def test_empty_init_data_raises_value_error(self):
        with pytest.raises(ValueError, match="Empty initData"):
            verify_telegram_init_data("", BOT_TOKEN)


# ---------------------------------------------------------------------------
# FastAPI dependency integration tests
# ---------------------------------------------------------------------------

from fastapi.testclient import TestClient  # noqa: E402
import app.main as main_module  # noqa: E402
from app.auth.dependencies import get_telegram_user  # noqa: E402

# Client WITHOUT Telegram auth bypass — tests real auth behaviour
# DB override is already wired by conftest.py (shared TEST_ENGINE)
_AUTH_CLIENT = TestClient(main_module.app, raise_server_exceptions=False)


class TestTelegramAuthDependency:
    def setup_method(self):
        # Remove the bypass override so real auth runs
        main_module.app.dependency_overrides.pop(get_telegram_user, None)

    def teardown_method(self):
        # Restore bypass so other test modules are unaffected
        main_module.app.dependency_overrides[get_telegram_user] = lambda: _TEST_USER

    def test_missing_init_data_header_allows_browser_access(self):
        """Without X-Init-Data header, browser users are allowed as anonymous."""
        os.environ.pop("TELEGRAM_BOT_TOKEN", None)
        res = _AUTH_CLIENT.post("/api/courses/generate", json={"topic": "x"})
        # Auth passes (anonymous); endpoint may fail for other reasons (AI unavailable)
        # but must NOT return 401 or 503 from auth layer
        assert res.status_code not in (401, 503)

    def test_invalid_init_data_returns_401(self, monkeypatch):
        """With bot token set but invalid initData → 401."""
        monkeypatch.setenv("TELEGRAM_BOT_TOKEN", BOT_TOKEN)
        # Re-import to pick up new env var (patch the module-level _BOT_TOKEN)
        import app.auth.dependencies as deps
        monkeypatch.setattr(deps, "_BOT_TOKEN", BOT_TOKEN)
        res = _AUTH_CLIENT.post(
            "/api/courses/generate",
            json={"topic": "x"},
            headers={"X-Init-Data": "bad_data"},
        )
        assert res.status_code == 401

    def test_valid_init_data_passes_auth(self, monkeypatch):
        """With valid initData the endpoint processes the request (may fail AI, not auth)."""
        import app.auth.dependencies as deps
        monkeypatch.setattr(deps, "_BOT_TOKEN", BOT_TOKEN)
        init_data = _make_init_data(_TEST_USER, bot_token=BOT_TOKEN)
        from unittest.mock import AsyncMock, patch
        with patch("app.api.v1.courses.call_ai", new_callable=AsyncMock) as mock_ai:
            mock_ai.return_value = '[{"title": "A", "description": "desc", "list_of_prerequisite_titles": []}]'
            res = _AUTH_CLIENT.post(
                "/api/courses/generate",
                json={"topic": "test"},
                headers={"X-Init-Data": init_data},
            )
        assert res.status_code == 200
