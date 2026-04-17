"""
Shared pytest fixtures and bootstrap for VYUD LMS backend tests.

Stubs heavy optional dependencies (litellm) and wires an in-memory SQLite
database so tests never need a real PostgreSQL instance.
"""
import os
import sys
import types

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

# ---------------------------------------------------------------------------
# Remove real service keys from the test environment
# ---------------------------------------------------------------------------
for _key in ("DATABASE_URL", "GROQ_API_KEY", "GEMINI_API_KEY", "OPENROUTER_API_KEY"):
    os.environ.pop(_key, None)

# ---------------------------------------------------------------------------
# Stub litellm before any app code is imported
# ---------------------------------------------------------------------------
_litellm_stub = types.ModuleType("litellm")


class _MockMessage:
    content = ""


class _MockChoice:
    message = _MockMessage()


class _MockCompletion:
    choices = [_MockChoice()]


_litellm_stub.completion = lambda *a, **kw: _MockCompletion()  # type: ignore[attr-defined]


async def _async_mock_completion(*a, **kw):  # noqa: RUF029
    return _MockCompletion()


_litellm_stub.acompletion = _async_mock_completion  # type: ignore[attr-defined]
sys.modules.setdefault("litellm", _litellm_stub)

# ---------------------------------------------------------------------------
# In-memory SQLite engine (session-scoped — shared across all tests)
# ---------------------------------------------------------------------------
from app.db.base import Base  # noqa: E402  (import after stub)

# Register all models so their tables are created
import app.models.course      # noqa: E402, F401
import app.models.document    # noqa: E402, F401
import app.models.knowledge   # noqa: E402, F401
import app.models.org         # noqa: E402, F401
import app.models.sop         # noqa: E402, F401
import app.models.streak      # noqa: E402, F401

TEST_ENGINE = create_engine(
    "sqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=TEST_ENGINE)
Base.metadata.create_all(bind=TEST_ENGINE)


def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


# ---------------------------------------------------------------------------
# Wire the FastAPI app once for the whole test session
# ---------------------------------------------------------------------------
import app.main as _main_module                        # noqa: E402
import app.api.v1.health as _health_module             # noqa: E402
from app.core.deps import get_db                       # noqa: E402
from app.auth.dependencies import get_telegram_user    # noqa: E402

# Inject in-memory DB into every route that uses get_db
_main_module.app.dependency_overrides[get_db] = override_get_db

# Bypass Telegram auth so tests don't need a real bot token
_main_module.app.dependency_overrides[get_telegram_user] = lambda: {
    "id": 1,
    "first_name": "Test",
}

# Make /api/health report "connected" against the SQLite engine
_health_module.engine = TEST_ENGINE
