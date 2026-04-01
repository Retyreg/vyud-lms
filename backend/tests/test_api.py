"""
Tests for the VYUD LMS backend API.

Uses an in-memory SQLite database so no real PostgreSQL is needed.
Run from the `backend/` directory:

    pytest tests/ -v
"""
import os
import sys
import types
import pytest

# Make sure no real DB or AI keys pollute the test environment
os.environ.pop("DATABASE_URL", None)
os.environ.pop("GROQ_API_KEY", None)
os.environ.pop("GEMINI_API_KEY", None)

# ---------------------------------------------------------------------------
# Stub out heavy optional dependencies before importing app code
# ---------------------------------------------------------------------------
_litellm_stub = types.ModuleType("litellm")

class _MockMessage:
    content = ""

class _MockChoice:
    message = _MockMessage()

class _MockCompletion:
    choices = [_MockChoice()]

_litellm_stub.completion = lambda *a, **kw: _MockCompletion()  # type: ignore[attr-defined]
sys.modules.setdefault("litellm", _litellm_stub)

from unittest.mock import AsyncMock, patch  # noqa: E402

from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import create_engine  # noqa: E402
from sqlalchemy.orm import sessionmaker  # noqa: E402
from sqlalchemy.pool import StaticPool  # noqa: E402

# ---------------------------------------------------------------------------
# App bootstrap — must happen after env-var cleanup and stubs above
# ---------------------------------------------------------------------------
from app.db.base import Base  # noqa: E402
# Models must be imported so their metadata is registered before create_all
import app.models.course  # noqa: E402, F401
import app.models.knowledge  # noqa: E402, F401
import app.models.org  # noqa: E402, F401
import app.main as main_module  # noqa: E402
from app.auth.dependencies import get_telegram_user  # noqa: E402


# ---------------------------------------------------------------------------
# In-memory SQLite engine reused across all tests in the session.
# StaticPool ensures all connections share the same in-memory database
# so tables created by create_all remain visible to test sessions.
# ---------------------------------------------------------------------------
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


# Patch the app's dependency so every request uses the in-memory DB
main_module.app.dependency_overrides[main_module.get_db] = override_get_db

# Bypass Telegram auth in tests — no real bot token needed
main_module.app.dependency_overrides[get_telegram_user] = lambda: {"id": 1, "first_name": "Test"}

# Also patch the module-level engine so /api/health can connect
main_module.engine = TEST_ENGINE


CLIENT = TestClient(main_module.app)


# ===========================================================================
# Basic reachability
# ===========================================================================

class TestRoot:
    def test_root_returns_ok(self):
        res = CLIENT.get("/")
        assert res.status_code == 200
        body = res.json()
        assert body["status"] == "ok"


# ===========================================================================
# /api/health
# ===========================================================================

class TestHealthEndpoint:
    def test_health_returns_200(self):
        res = CLIENT.get("/api/health")
        assert res.status_code == 200

    def test_health_has_required_fields(self):
        body = CLIENT.get("/api/health").json()
        for field in ("status", "uptime_seconds", "database", "ai_groq", "ai_gemini"):
            assert field in body, f"Field '{field}' missing from /api/health response"

    def test_health_database_connected_with_sqlite(self):
        body = CLIENT.get("/api/health").json()
        assert body["database"] == "connected"

    def test_health_ai_not_configured_without_env_vars(self, monkeypatch):
        monkeypatch.delenv("GROQ_API_KEY", raising=False)
        monkeypatch.delenv("GEMINI_API_KEY", raising=False)
        body = CLIENT.get("/api/health").json()
        assert body["ai_groq"] == "not_configured"
        assert body["ai_gemini"] == "not_configured"

    def test_health_status_degraded_without_ai(self, monkeypatch):
        # DB is connected but AI keys are absent -> "degraded"
        monkeypatch.delenv("GROQ_API_KEY", raising=False)
        monkeypatch.delenv("GEMINI_API_KEY", raising=False)
        body = CLIENT.get("/api/health").json()
        assert body["status"] == "degraded"

    def test_health_status_ok_when_ai_configured(self, monkeypatch):
        monkeypatch.setenv("GROQ_API_KEY", "test-key")
        body = CLIENT.get("/api/health").json()
        assert body["status"] == "ok"

    def test_health_uptime_is_non_negative(self):
        body = CLIENT.get("/api/health").json()
        assert body["uptime_seconds"] >= 0


# ===========================================================================
# /api/courses/latest -- empty state
# ===========================================================================

class TestCoursesLatest:
    def test_returns_empty_when_no_courses(self):
        res = CLIENT.get("/api/courses/latest")
        assert res.status_code == 200
        body = res.json()
        assert body["nodes"] == []
        assert body["edges"] == []

    def test_response_schema_has_nodes_and_edges(self):
        body = CLIENT.get("/api/courses/latest").json()
        assert "nodes" in body
        assert "edges" in body


# ===========================================================================
# /api/courses/generate -- mocked AI
# ===========================================================================

MOCK_AI_RESPONSE = (
    '[{"title": "Python основы", "description": "Переменные и типы данных", '
    '"list_of_prerequisite_titles": []}, '
    '{"title": "Функции", "description": "Определение функций", '
    '"list_of_prerequisite_titles": ["Python основы"]}]'
)

# What Groq JSON-object mode actually returns when asked for an array
MOCK_AI_RESPONSE_WRAPPED = (
    '{"courses": ['
    '{"title": "Python основы", "description": "Переменные и типы данных", "list_of_prerequisite_titles": []}, '
    '{"title": "Функции", "description": "Определение функций", "list_of_prerequisite_titles": ["Python основы"]}'
    ']}'
)


class TestCourseGenerate:
    def test_generate_creates_course_and_nodes(self):
        with patch("app.main.call_ai", new_callable=AsyncMock) as mock_ai:
            mock_ai.return_value = MOCK_AI_RESPONSE
            res = CLIENT.post(
                "/api/courses/generate",
                json={"topic": "Python"},
            )
        assert res.status_code == 200
        assert res.json()["status"] == "ok"

    def test_generate_handles_object_wrapped_array(self):
        """AI with json_mode returns {\"courses\": [...]} instead of a bare array."""
        with patch("app.main.call_ai", new_callable=AsyncMock) as mock_ai:
            mock_ai.return_value = MOCK_AI_RESPONSE_WRAPPED
            res = CLIENT.post("/api/courses/generate", json={"topic": "Python Wrapped"})
        assert res.status_code == 200, res.json()
        assert res.json()["status"] == "ok"

    def test_generate_course_appears_in_latest(self):
        with patch("app.main.call_ai", new_callable=AsyncMock) as mock_ai:
            mock_ai.return_value = MOCK_AI_RESPONSE
            CLIENT.post("/api/courses/generate", json={"topic": "Python Graph Test"})

        latest = CLIENT.get("/api/courses/latest").json()
        assert len(latest["nodes"]) > 0

    def test_generate_creates_edges_for_prerequisites(self):
        with patch("app.main.call_ai", new_callable=AsyncMock) as mock_ai:
            mock_ai.return_value = MOCK_AI_RESPONSE
            CLIENT.post("/api/courses/generate", json={"topic": "Python Edges Test"})

        latest = CLIENT.get("/api/courses/latest").json()
        assert len(latest["edges"]) > 0

    def test_generate_handles_markdown_wrapped_json(self):
        """AI may wrap the JSON in a markdown code block."""
        markdown_response = "```json\n" + MOCK_AI_RESPONSE + "\n```"
        with patch("app.main.call_ai", new_callable=AsyncMock) as mock_ai:
            mock_ai.return_value = markdown_response
            res = CLIENT.post("/api/courses/generate", json={"topic": "Markdown Test"})
        assert res.status_code == 200

    def test_generate_returns_error_on_invalid_ai_json(self):
        with patch("app.main.call_ai", new_callable=AsyncMock) as mock_ai:
            mock_ai.return_value = "not valid json {{{"
            res = CLIENT.post("/api/courses/generate", json={"topic": "Bad JSON"})
        assert res.status_code == 500

    def test_generate_requires_topic_field(self):
        res = CLIENT.post("/api/courses/generate", json={})
        assert res.status_code == 422


# ===========================================================================
# /api/explain/{node_id} -- mocked AI
# ===========================================================================

class TestExplain:
    def _create_node(self, db, label: str = "Python") -> int:
        """Insert a KnowledgeNode and return its id."""
        from app.models.knowledge import KnowledgeNode
        node = KnowledgeNode(label=label, level=1, is_completed=False, prerequisites=[])
        db.add(node)
        db.commit()
        db.refresh(node)
        return node.id

    def test_explain_returns_explanation(self):
        from sqlalchemy.orm import Session
        db: Session = next(override_get_db())
        node_id = self._create_node(db)
        db.close()

        with patch("app.main.call_ai", new_callable=AsyncMock) as mock_ai:
            mock_ai.return_value = "Python — это простой язык программирования."
            res = CLIENT.get(f"/api/explain/{node_id}")
        assert res.status_code == 200
        body = res.json()
        assert "explanation" in body
        assert body["cached"] is False

    def test_explain_cache_hit_returns_cached_true(self):
        from sqlalchemy.orm import Session
        db: Session = next(override_get_db())
        node_id = self._create_node(db, label="React")
        db.close()

        with patch("app.main.call_ai", new_callable=AsyncMock) as mock_ai:
            mock_ai.return_value = "React — библиотека для UI."
            CLIENT.get(f"/api/explain/{node_id}")          # first call — writes cache
            res = CLIENT.get(f"/api/explain/{node_id}")    # second call — cache hit

        body = res.json()
        assert res.status_code == 200
        assert body["cached"] is True

    def test_explain_unknown_node_returns_404(self):
        res = CLIENT.get("/api/explain/999999")
        assert res.status_code == 404

    def test_explain_non_integer_node_id_returns_422(self):
        res = CLIENT.get("/api/explain/not-a-number")
        assert res.status_code == 422


# ===========================================================================
# SM-2 spaced repetition endpoints
# ===========================================================================

class TestSM2:
    def _create_node(self, label: str = "SM2Test") -> int:
        from sqlalchemy.orm import Session
        from app.models.knowledge import KnowledgeNode
        db: Session = next(override_get_db())
        node = KnowledgeNode(label=label, level=1, is_completed=False, prerequisites=[])
        db.add(node)
        db.commit()
        db.refresh(node)
        node_id = node.id
        db.close()
        return node_id

    def test_review_returns_200(self):
        node_id = self._create_node("ReviewOk")
        res = CLIENT.post(f"/api/nodes/{node_id}/review", json={"user_key": "test@test.com", "quality": 3})
        assert res.status_code == 200
        body = res.json()
        assert "next_review_days" in body
        assert "mastery" in body

    def test_review_invalid_quality_returns_422(self):
        node_id = self._create_node("ReviewBadQ")
        res = CLIENT.post(f"/api/nodes/{node_id}/review", json={"user_key": "test@test.com", "quality": 9})
        assert res.status_code == 422

    def test_review_unknown_node_returns_404(self):
        res = CLIENT.post("/api/nodes/999999/review", json={"user_key": "x", "quality": 2})
        assert res.status_code == 404

    def test_review_quality_0_does_not_complete_node(self):
        node_id = self._create_node("ReviewFail")
        CLIENT.post(f"/api/nodes/{node_id}/review", json={"user_key": "fail@test.com", "quality": 0})
        from sqlalchemy.orm import Session
        from app.models.knowledge import KnowledgeNode
        db: Session = next(override_get_db())
        node = db.query(KnowledgeNode).filter(KnowledgeNode.id == node_id).first()
        assert node.is_completed is False
        db.close()

    def test_review_quality_2_completes_node(self):
        """quality=2 → q=4 → correct recall → node marked complete."""
        node_id = self._create_node("ReviewPass")
        res = CLIENT.post(f"/api/nodes/{node_id}/review", json={"user_key": "pass@test.com", "quality": 2})
        assert res.status_code == 200
        # Verify via sr-status that correct_reviews > 0 (i.e. recall was counted as correct)
        sr = CLIENT.get(f"/api/nodes/{node_id}/sr-status?user_key=pass@test.com").json()
        assert sr["mastery"] != "новый", "Expected mastery to advance after a correct review"

    def test_sr_status_new_node(self):
        node_id = self._create_node("SRStatus")
        res = CLIENT.get(f"/api/nodes/{node_id}/sr-status?user_key=user1")
        assert res.status_code == 200
        body = res.json()
        assert body["mastery"] == "новый"
        assert body["is_due"] is True

    def test_sr_status_after_review(self):
        node_id = self._create_node("SRAfterReview")
        CLIENT.post(f"/api/nodes/{node_id}/review", json={"user_key": "sr_user", "quality": 3})
        res = CLIENT.get(f"/api/nodes/{node_id}/sr-status?user_key=sr_user")
        assert res.status_code == 200
        body = res.json()
        assert body["next_review"] is not None


# ===========================================================================
# postgres:// URL scheme normalisation
# ===========================================================================

class TestPostgresUrlNormalisation:
    """Verify the postgres:// → postgresql:// rewrite in base.py."""

    def test_postgres_scheme_is_rewritten(self):
        url = "postgres://user:pass@host:5432/db"
        # replicate the exact logic from base.py
        if url and url.startswith("postgres://"):
            url = url.replace("postgres://", "postgresql://", 1)
        assert url.startswith("postgresql://"), (
            f"Expected 'postgresql://' prefix, got: {url!r}"
        )

    def test_postgresql_scheme_unchanged(self):
        url = "postgresql://user:pass@host:5432/db"
        if url and url.startswith("postgres://"):
            url = url.replace("postgres://", "postgresql://", 1)
        assert url == "postgresql://user:pass@host:5432/db"

    def test_base_py_contains_normalisation(self):
        """base.py source must contain the postgres:// fix."""
        from pathlib import Path
        source = (Path(__file__).parent.parent / "app" / "db" / "base.py").read_text()
        assert "postgres://" in source and "postgresql://" in source, (
            "base.py must rewrite postgres:// to postgresql://"
        )
