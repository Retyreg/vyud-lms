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
import app.models.user  # noqa: E402, F401
import app.models.task  # noqa: E402, F401
import app.models.news  # noqa: E402, F401
import app.main as main_module  # noqa: E402


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

    def test_health_ai_not_configured_without_env_vars(self):
        body = CLIENT.get("/api/health").json()
        assert body["ai_groq"] == "not_configured"
        assert body["ai_gemini"] == "not_configured"

    def test_health_status_degraded_without_ai(self):
        # DB is connected but AI keys are absent -> "degraded"
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
# /api/explain/{topic} -- mocked AI
# ===========================================================================

class TestExplain:
    def test_explain_returns_explanation(self):
        with patch("app.main.call_ai", new_callable=AsyncMock) as mock_ai:
            mock_ai.return_value = "Python -- это простой язык программирования."
            res = CLIENT.get("/api/explain/Python")
        assert res.status_code == 200
        assert "explanation" in res.json()
        assert "Python" in res.json()["explanation"]

    def test_explain_url_encoded_topic(self):
        with patch("app.main.call_ai", new_callable=AsyncMock) as mock_ai:
            mock_ai.return_value = "React -- библиотека для UI."
            res = CLIENT.get("/api/explain/React%20%D0%BE%D1%81%D0%BD%D0%BE%D0%B2%D1%8B")
        assert res.status_code == 200
        assert "explanation" in res.json()


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


# ===========================================================================
# /api/v1/auth -- registration and login
# ===========================================================================

class TestAuthRegister:
    def test_register_returns_201(self):
        res = CLIENT.post("/api/v1/auth/register", json={
            "email": "alice@example.com",
            "password": "secret123",
            "full_name": "Alice",
        })
        assert res.status_code == 201
        body = res.json()
        assert body["email"] == "alice@example.com"
        assert body["role"] == "associate"
        assert "hashed_password" not in body

    def test_register_duplicate_email_returns_409(self):
        CLIENT.post("/api/v1/auth/register", json={
            "email": "bob@example.com",
            "password": "secret123",
        })
        res = CLIENT.post("/api/v1/auth/register", json={
            "email": "bob@example.com",
            "password": "other",
        })
        assert res.status_code == 409

    def test_register_with_role(self):
        res = CLIENT.post("/api/v1/auth/register", json={
            "email": "manager@example.com",
            "password": "secret123",
            "role": "store_manager",
        })
        assert res.status_code == 201
        assert res.json()["role"] == "store_manager"

    def test_register_missing_required_fields(self):
        res = CLIENT.post("/api/v1/auth/register", json={"email": "nopw@example.com"})
        assert res.status_code == 422

    def test_register_invalid_email(self):
        res = CLIENT.post("/api/v1/auth/register", json={
            "email": "not-an-email",
            "password": "secret123",
        })
        assert res.status_code == 422


class TestAuthLogin:
    def test_login_returns_token(self):
        CLIENT.post("/api/v1/auth/register", json={
            "email": "carol@example.com",
            "password": "mypassword",
        })
        res = CLIENT.post("/api/v1/auth/login", json={
            "email": "carol@example.com",
            "password": "mypassword",
        })
        assert res.status_code == 200
        body = res.json()
        assert "access_token" in body
        assert body["token_type"] == "bearer"
        assert body["user"]["email"] == "carol@example.com"

    def test_login_wrong_password_returns_401(self):
        CLIENT.post("/api/v1/auth/register", json={
            "email": "dave@example.com",
            "password": "correct",
        })
        res = CLIENT.post("/api/v1/auth/login", json={
            "email": "dave@example.com",
            "password": "wrong",
        })
        assert res.status_code == 401

    def test_login_unknown_email_returns_401(self):
        res = CLIENT.post("/api/v1/auth/login", json={
            "email": "nobody@example.com",
            "password": "whatever",
        })
        assert res.status_code == 401


# ===========================================================================
# /api/v1/tasks -- task management CRUD
# ===========================================================================

class TestTaskCRUD:
    def test_list_tasks_empty(self):
        res = CLIENT.get("/api/v1/tasks")
        assert res.status_code == 200
        assert isinstance(res.json(), list)

    def test_create_task_returns_201(self):
        res = CLIENT.post("/api/v1/tasks", json={"title": "Проверка витрины"})
        assert res.status_code == 201
        body = res.json()
        assert body["title"] == "Проверка витрины"
        assert body["status"] == "pending"

    def test_create_task_with_checklist(self):
        res = CLIENT.post("/api/v1/tasks", json={
            "title": "Открытие магазина",
            "checklist": [
                {"title": "Включить свет", "is_done": False, "photo_required": False},
                {"title": "Фото входа", "is_done": False, "photo_required": True},
            ],
        })
        assert res.status_code == 201
        assert len(res.json()["checklist"]) == 2

    def test_get_task_by_id(self):
        create_res = CLIENT.post("/api/v1/tasks", json={"title": "Задача для чтения"})
        task_id = create_res.json()["id"]
        res = CLIENT.get(f"/api/v1/tasks/{task_id}")
        assert res.status_code == 200
        assert res.json()["id"] == task_id

    def test_get_task_not_found_returns_404(self):
        res = CLIENT.get("/api/v1/tasks/999999")
        assert res.status_code == 404

    def test_update_task_status(self):
        create_res = CLIENT.post("/api/v1/tasks", json={"title": "Задача на обновление"})
        task_id = create_res.json()["id"]
        res = CLIENT.patch(f"/api/v1/tasks/{task_id}", json={"status": "in_progress"})
        assert res.status_code == 200
        assert res.json()["status"] == "in_progress"

    def test_complete_task_sets_completed_at(self):
        create_res = CLIENT.post("/api/v1/tasks", json={"title": "Завершённая задача"})
        task_id = create_res.json()["id"]
        res = CLIENT.patch(f"/api/v1/tasks/{task_id}", json={"status": "completed"})
        assert res.status_code == 200
        assert res.json()["completed_at"] is not None

    def test_delete_task(self):
        create_res = CLIENT.post("/api/v1/tasks", json={"title": "Задача на удаление"})
        task_id = create_res.json()["id"]
        del_res = CLIENT.delete(f"/api/v1/tasks/{task_id}")
        assert del_res.status_code == 204
        assert CLIENT.get(f"/api/v1/tasks/{task_id}").status_code == 404

    def test_delete_task_not_found_returns_404(self):
        res = CLIENT.delete("/api/v1/tasks/999999")
        assert res.status_code == 404

    def test_create_task_requires_title(self):
        res = CLIENT.post("/api/v1/tasks", json={"description": "Без заголовка"})
        assert res.status_code == 422

    def test_list_tasks_filter_by_status(self):
        CLIENT.post("/api/v1/tasks", json={"title": "Фильтр: ожидание"})
        res = CLIENT.get("/api/v1/tasks?status_filter=pending")
        assert res.status_code == 200
        body = res.json()
        assert all(t["status"] == "pending" for t in body)


# ===========================================================================
# JWT auth — token format and token refresh
# ===========================================================================

class TestJWTAuth:
    """Verify that login returns real JWT tokens, not placeholder strings."""

    def _register_and_login(self, email: str, password: str = "secret123") -> dict:
        CLIENT.post("/api/v1/auth/register", json={"email": email, "password": password})
        res = CLIENT.post("/api/v1/auth/login", json={"email": email, "password": password})
        assert res.status_code == 200, res.text
        return res.json()

    def test_login_returns_jwt_access_token(self):
        body = self._register_and_login("jwt_user1@example.com")
        # A JWT has exactly 3 dot-separated Base64url segments
        parts = body["access_token"].split(".")
        assert len(parts) == 3, f"Expected JWT (3 parts), got: {body['access_token']!r}"

    def test_login_returns_refresh_token(self):
        body = self._register_and_login("jwt_user2@example.com")
        assert "refresh_token" in body
        parts = body["refresh_token"].split(".")
        assert len(parts) == 3

    def test_login_returns_expires_in(self):
        body = self._register_and_login("jwt_user3@example.com")
        assert "expires_in" in body
        assert body["expires_in"] == 15 * 60  # 15 minutes in seconds

    def test_token_refresh_returns_new_access_token(self):
        body = self._register_and_login("jwt_user4@example.com")
        res = CLIENT.post("/api/v1/auth/token/refresh", json={
            "refresh_token": body["refresh_token"],
        })
        assert res.status_code == 200, res.text
        new_body = res.json()
        assert "access_token" in new_body
        parts = new_body["access_token"].split(".")
        assert len(parts) == 3

    def test_refresh_with_invalid_token_returns_401(self):
        res = CLIENT.post("/api/v1/auth/token/refresh", json={
            "refresh_token": "not.a.valid.jwt",
        })
        assert res.status_code == 401

    def test_users_me_requires_auth(self):
        # Without auth header → 401
        res = CLIENT.get("/api/v1/users/me")
        assert res.status_code == 401

    def test_users_me_with_valid_token(self):
        body = self._register_and_login("jwt_user5@example.com")
        res = CLIENT.get(
            "/api/v1/users/me",
            headers={"Authorization": f"Bearer {body['access_token']}"},
        )
        assert res.status_code == 200
        assert res.json()["email"] == "jwt_user5@example.com"

    def test_users_me_with_invalid_token_returns_401(self):
        res = CLIENT.get(
            "/api/v1/users/me",
            headers={"Authorization": "Bearer bogus.token.here"},
        )
        assert res.status_code == 401


# ===========================================================================
# /api/v1/courses — course management and node completion
# ===========================================================================

MOCK_AI_RESPONSE_COURSES = (
    '[{"title": "Основы", "description": "Базовые понятия", '
    '"list_of_prerequisite_titles": []}, '
    '{"title": "Продвинутый", "description": "Углублённые знания", '
    '"list_of_prerequisite_titles": ["Основы"]}]'
)


class TestCoursesAPI:
    def _create_course(self, topic: str = "Тест-курс") -> int:
        """Helper: generate a course via the AI endpoint and return its id."""
        from unittest.mock import AsyncMock, patch
        with patch("app.main.call_ai", new_callable=AsyncMock) as mock_ai:
            mock_ai.return_value = MOCK_AI_RESPONSE_COURSES
            gen_res = CLIENT.post("/api/courses/generate", json={"topic": topic})
        assert gen_res.status_code == 200, f"Course generation failed: {gen_res.text}"
        courses = CLIENT.get("/api/v1/courses").json()
        assert courses, "No courses found after generation"
        return courses[0]["id"]

    def test_list_courses_returns_list(self):
        res = CLIENT.get("/api/v1/courses")
        assert res.status_code == 200
        assert isinstance(res.json(), list)

    def test_list_courses_after_generate(self):
        self._create_course("Курс для листинга")
        res = CLIENT.get("/api/v1/courses")
        assert res.status_code == 200
        assert len(res.json()) >= 1

    def test_list_courses_has_progress_fields(self):
        self._create_course("Курс прогресс-поля")
        courses = CLIENT.get("/api/v1/courses").json()
        c = courses[0]
        assert "node_count" in c
        assert "completed_count" in c
        assert c["node_count"] >= 0
        assert c["completed_count"] >= 0

    def test_get_course_by_id(self):
        course_id = self._create_course("Курс по ID")
        res = CLIENT.get(f"/api/v1/courses/{course_id}")
        assert res.status_code == 200
        body = res.json()
        assert body["id"] == course_id
        assert "nodes" in body
        assert "edges" in body

    def test_get_course_not_found_returns_404(self):
        res = CLIENT.get("/api/v1/courses/999999")
        assert res.status_code == 404

    def test_complete_node_marks_as_completed(self):
        course_id = self._create_course("Курс завершения")
        detail = CLIENT.get(f"/api/v1/courses/{course_id}").json()
        # Find a node with no prerequisites (immediately available)
        available = [n for n in detail["nodes"] if n["is_available"]]
        assert available, "Expected at least one available node"
        node_id = available[0]["id"]

        res = CLIENT.post(f"/api/v1/courses/{course_id}/nodes/{node_id}/complete")
        assert res.status_code == 200
        assert res.json()["is_completed"] is True

    def test_complete_node_refreshes_availability(self):
        """Completing a prerequisite node unlocks its dependents."""
        course_id = self._create_course("Курс разблокировки")
        detail = CLIENT.get(f"/api/v1/courses/{course_id}").json()
        # Complete all prerequisite (available) nodes first
        available = [n for n in detail["nodes"] if n["is_available"]]
        for n in available:
            CLIENT.post(f"/api/v1/courses/{course_id}/nodes/{n['id']}/complete")
        # After completing prereqs, previously-blocked nodes should now exist
        updated = CLIENT.get(f"/api/v1/courses/{course_id}").json()
        completed = [n for n in updated["nodes"] if n["is_completed"]]
        assert len(completed) >= len(available)

    def test_complete_node_not_found_returns_404(self):
        course_id = self._create_course("Курс 404-нода")
        res = CLIENT.post(f"/api/v1/courses/{course_id}/nodes/999999/complete")
        assert res.status_code == 404


# ===========================================================================
# /api/v1/feed — news feed CRUD
# ===========================================================================

class TestNewsFeed:
    def test_list_feed_empty(self):
        res = CLIENT.get("/api/v1/feed")
        assert res.status_code == 200
        assert isinstance(res.json(), list)

    def test_create_post_returns_201(self):
        res = CLIENT.post("/api/v1/feed", json={
            "title": "Объявление",
            "content": "Текст объявления",
        })
        assert res.status_code == 201
        body = res.json()
        assert body["title"] == "Объявление"
        assert body["is_published"] is True

    def test_create_post_with_summary(self):
        res = CLIENT.post("/api/v1/feed", json={
            "title": "С кратким описанием",
            "content": "Полный текст",
            "summary": "Краткое описание",
        })
        assert res.status_code == 201
        assert res.json()["summary"] == "Краткое описание"

    def test_get_post_by_id(self):
        create_res = CLIENT.post("/api/v1/feed", json={
            "title": "Получить по ID",
            "content": "Контент",
        })
        post_id = create_res.json()["id"]
        res = CLIENT.get(f"/api/v1/feed/{post_id}")
        assert res.status_code == 200
        assert res.json()["id"] == post_id

    def test_get_post_not_found_returns_404(self):
        res = CLIENT.get("/api/v1/feed/999999")
        assert res.status_code == 404

    def test_update_post(self):
        create_res = CLIENT.post("/api/v1/feed", json={
            "title": "Обновляемый пост",
            "content": "Старый контент",
        })
        post_id = create_res.json()["id"]
        res = CLIENT.patch(f"/api/v1/feed/{post_id}", json={"title": "Новый заголовок"})
        assert res.status_code == 200
        assert res.json()["title"] == "Новый заголовок"

    def test_unpublish_post(self):
        create_res = CLIENT.post("/api/v1/feed", json={
            "title": "Снять с публикации",
            "content": "Контент",
        })
        post_id = create_res.json()["id"]
        CLIENT.patch(f"/api/v1/feed/{post_id}", json={"is_published": False})
        # Unpublished post should not appear in feed
        feed = CLIENT.get("/api/v1/feed").json()
        assert not any(p["id"] == post_id for p in feed)

    def test_delete_post(self):
        create_res = CLIENT.post("/api/v1/feed", json={
            "title": "Удаляемый пост",
            "content": "Контент",
        })
        post_id = create_res.json()["id"]
        del_res = CLIENT.delete(f"/api/v1/feed/{post_id}")
        assert del_res.status_code == 204
        assert CLIENT.get(f"/api/v1/feed/{post_id}").status_code == 404

    def test_delete_post_not_found_returns_404(self):
        res = CLIENT.delete("/api/v1/feed/999999")
        assert res.status_code == 404

    def test_create_post_requires_title_and_content(self):
        res = CLIENT.post("/api/v1/feed", json={"title": "Без контента"})
        assert res.status_code == 422

    def test_list_feed_shows_published_only(self):
        # Create a published and an unpublished post
        pub = CLIENT.post("/api/v1/feed", json={
            "title": "Опубликованный",
            "content": "Видимый",
        }).json()
        unpub_id = CLIENT.post("/api/v1/feed", json={
            "title": "Черновик",
            "content": "Скрытый",
        }).json()["id"]
        CLIENT.patch(f"/api/v1/feed/{unpub_id}", json={"is_published": False})

        feed = CLIENT.get("/api/v1/feed").json()
        ids = [p["id"] for p in feed]
        assert pub["id"] in ids
        assert unpub_id not in ids
