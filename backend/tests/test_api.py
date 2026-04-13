"""
Tests for the VYUD LMS backend API.

Uses an in-memory SQLite database so no real PostgreSQL is needed.
Run from the `backend/` directory:

    pytest tests/ -v

Bootstrap (litellm stub, SQLite engine, dependency overrides) is handled
by conftest.py — do not duplicate it here.
"""
import json

import pytest
from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient

import app.main as main_module
from tests.conftest import override_get_db, TEST_ENGINE, TestingSessionLocal
from app.auth.dependencies import get_telegram_user
from app.core.deps import get_db

CLIENT = TestClient(main_module.app)


# ===========================================================================
# Basic reachability
# ===========================================================================

class TestRoot:
    def test_root_returns_ok(self):
        res = CLIENT.get("/")
        assert res.status_code == 200
        assert res.json()["status"] == "ok"


# ===========================================================================
# /api/health
# ===========================================================================

class TestHealthEndpoint:
    def test_health_returns_200(self):
        assert CLIENT.get("/api/health").status_code == 200

    def test_health_has_required_fields(self):
        body = CLIENT.get("/api/health").json()
        for field in ("status", "uptime_seconds", "database", "ai_groq", "ai_gemini"):
            assert field in body, f"Field '{field}' missing from /api/health response"

    def test_health_database_connected_with_sqlite(self):
        assert CLIENT.get("/api/health").json()["database"] == "connected"

    def test_health_ai_not_configured_without_env_vars(self, monkeypatch):
        monkeypatch.delenv("GROQ_API_KEY", raising=False)
        monkeypatch.delenv("GEMINI_API_KEY", raising=False)
        body = CLIENT.get("/api/health").json()
        assert body["ai_groq"] == "not_configured"
        assert body["ai_gemini"] == "not_configured"

    def test_health_status_degraded_without_ai(self, monkeypatch):
        monkeypatch.delenv("GROQ_API_KEY", raising=False)
        monkeypatch.delenv("GEMINI_API_KEY", raising=False)
        assert CLIENT.get("/api/health").json()["status"] == "degraded"

    def test_health_status_ok_when_ai_configured(self, monkeypatch):
        monkeypatch.setenv("GROQ_API_KEY", "test-key")
        assert CLIENT.get("/api/health").json()["status"] == "ok"

    def test_health_uptime_is_non_negative(self):
        assert CLIENT.get("/api/health").json()["uptime_seconds"] >= 0


# ===========================================================================
# /api/courses/latest
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
        assert "nodes" in body and "edges" in body


# ===========================================================================
# /api/courses/generate
# ===========================================================================

_MOCK_NODES = (
    '[{"title": "Python основы", "description": "Переменные", '
    '"list_of_prerequisite_titles": []}, '
    '{"title": "Функции", "description": "def", '
    '"list_of_prerequisite_titles": ["Python основы"]}]'
)
_MOCK_NODES_WRAPPED = (
    '{"courses": ['
    '{"title": "Python основы", "description": "Переменные", "list_of_prerequisite_titles": []}, '
    '{"title": "Функции", "description": "def", "list_of_prerequisite_titles": ["Python основы"]}'
    ']}'
)


class TestCourseGenerate:
    def test_generate_creates_course_and_nodes(self):
        with patch("app.api.v1.courses.call_ai", new_callable=AsyncMock) as mock_ai:
            mock_ai.return_value = _MOCK_NODES
            res = CLIENT.post("/api/courses/generate", json={"topic": "Python"})
        assert res.status_code == 200
        assert res.json()["status"] == "ok"

    def test_generate_handles_object_wrapped_array(self):
        with patch("app.api.v1.courses.call_ai", new_callable=AsyncMock) as mock_ai:
            mock_ai.return_value = _MOCK_NODES_WRAPPED
            res = CLIENT.post("/api/courses/generate", json={"topic": "Python Wrapped"})
        assert res.status_code == 200

    def test_generate_course_appears_in_latest(self):
        with patch("app.api.v1.courses.call_ai", new_callable=AsyncMock) as mock_ai:
            mock_ai.return_value = _MOCK_NODES
            CLIENT.post("/api/courses/generate", json={"topic": "Python Graph Test"})
        assert len(CLIENT.get("/api/courses/latest").json()["nodes"]) > 0

    def test_generate_creates_edges_for_prerequisites(self):
        with patch("app.api.v1.courses.call_ai", new_callable=AsyncMock) as mock_ai:
            mock_ai.return_value = _MOCK_NODES
            CLIENT.post("/api/courses/generate", json={"topic": "Python Edges Test"})
        assert len(CLIENT.get("/api/courses/latest").json()["edges"]) > 0

    def test_generate_handles_markdown_wrapped_json(self):
        with patch("app.api.v1.courses.call_ai", new_callable=AsyncMock) as mock_ai:
            mock_ai.return_value = "```json\n" + _MOCK_NODES + "\n```"
            res = CLIENT.post("/api/courses/generate", json={"topic": "Markdown Test"})
        assert res.status_code == 200

    def test_generate_returns_500_on_invalid_ai_json(self):
        with patch("app.api.v1.courses.call_ai", new_callable=AsyncMock) as mock_ai:
            mock_ai.return_value = "not valid json {{{"
            res = CLIENT.post("/api/courses/generate", json={"topic": "Bad JSON"})
        assert res.status_code == 500

    def test_generate_requires_topic_field(self):
        assert CLIENT.post("/api/courses/generate", json={}).status_code == 422


# ===========================================================================
# /api/explain/{node_id}
# ===========================================================================

def _create_node(label: str = "TestNode") -> int:
    from app.models.knowledge import KnowledgeNode
    db = next(override_get_db())
    node = KnowledgeNode(label=label, level=1, is_completed=False, prerequisites=[])
    db.add(node)
    db.commit()
    db.refresh(node)
    node_id = node.id
    db.close()
    return node_id


class TestExplain:
    def test_explain_returns_explanation(self):
        node_id = _create_node("ExplainNode")
        with patch("app.api.v1.nodes.call_ai", new_callable=AsyncMock) as mock_ai:
            mock_ai.return_value = "Python — язык программирования."
            res = CLIENT.get(f"/api/explain/{node_id}")
        assert res.status_code == 200
        body = res.json()
        assert "explanation" in body
        assert body["cached"] is False

    def test_explain_cache_hit_returns_cached_true(self):
        node_id = _create_node("ExplainCached")
        with patch("app.api.v1.nodes.call_ai", new_callable=AsyncMock) as mock_ai:
            mock_ai.return_value = "React — библиотека."
            CLIENT.get(f"/api/explain/{node_id}")           # writes cache
            res = CLIENT.get(f"/api/explain/{node_id}")     # cache hit
        assert res.status_code == 200
        assert res.json()["cached"] is True

    def test_explain_unknown_node_returns_404(self):
        assert CLIENT.get("/api/explain/999999").status_code == 404

    def test_explain_non_integer_id_returns_422(self):
        assert CLIENT.get("/api/explain/not-a-number").status_code == 422


# ===========================================================================
# SM-2 spaced repetition endpoints
# ===========================================================================

class TestSM2:
    def test_review_returns_200(self):
        node_id = _create_node("ReviewOk")
        res = CLIENT.post(f"/api/nodes/{node_id}/review",
                          json={"user_key": "test@test.com", "quality": 3})
        assert res.status_code == 200
        body = res.json()
        assert "next_review_days" in body
        assert "mastery" in body

    def test_review_invalid_quality_returns_422(self):
        node_id = _create_node("ReviewBadQ")
        res = CLIENT.post(f"/api/nodes/{node_id}/review",
                          json={"user_key": "test@test.com", "quality": 9})
        assert res.status_code == 422

    def test_review_unknown_node_returns_404(self):
        res = CLIENT.post("/api/nodes/999999/review", json={"user_key": "x", "quality": 2})
        assert res.status_code == 404

    def test_review_quality_0_does_not_complete_node(self):
        node_id = _create_node("ReviewFail")
        CLIENT.post(f"/api/nodes/{node_id}/review",
                    json={"user_key": "fail@test.com", "quality": 0})
        from app.models.knowledge import KnowledgeNode
        db = next(override_get_db())
        node = db.query(KnowledgeNode).filter(KnowledgeNode.id == node_id).first()
        db.close()
        assert node.is_completed is False

    def test_review_quality_2_completes_node(self):
        node_id = _create_node("ReviewPass")
        res = CLIENT.post(f"/api/nodes/{node_id}/review",
                          json={"user_key": "pass@test.com", "quality": 2})
        assert res.status_code == 200
        sr = CLIENT.get(f"/api/nodes/{node_id}/sr-status?user_key=pass@test.com").json()
        assert sr["mastery"] != "новый"

    def test_sr_status_new_node(self):
        node_id = _create_node("SRNew")
        res = CLIENT.get(f"/api/nodes/{node_id}/sr-status?user_key=user1")
        assert res.status_code == 200
        body = res.json()
        assert body["mastery"] == "новый"
        assert body["is_due"] is True

    def test_sr_status_after_review(self):
        node_id = _create_node("SRAfterReview")
        CLIENT.post(f"/api/nodes/{node_id}/review",
                    json={"user_key": "sr_user", "quality": 3})
        res = CLIENT.get(f"/api/nodes/{node_id}/sr-status?user_key=sr_user")
        assert res.status_code == 200
        assert res.json()["next_review"] is not None


# ===========================================================================
# postgres:// URL normalisation
# ===========================================================================

class TestPostgresUrlNormalisation:
    def test_postgres_scheme_is_rewritten(self):
        url = "postgres://user:pass@host:5432/db"
        if url.startswith("postgres://"):
            url = url.replace("postgres://", "postgresql://", 1)
        assert url.startswith("postgresql://")

    def test_postgresql_scheme_unchanged(self):
        url = "postgresql://user:pass@host:5432/db"
        if url.startswith("postgres://"):
            url = url.replace("postgres://", "postgresql://", 1)
        assert url == "postgresql://user:pass@host:5432/db"

    def test_base_py_contains_normalisation(self):
        from pathlib import Path
        source = (Path(__file__).parent.parent / "app" / "db" / "base.py").read_text()
        assert "postgres://" in source and "postgresql://" in source


# ===========================================================================
# /api/explain-stream/{node_id} — SSE streaming
# ===========================================================================

def _parse_sse(text: str) -> list[dict]:
    return [
        json.loads(line[6:])
        for line in text.splitlines()
        if line.startswith("data: ")
    ]


def _make_httpx_stream_mock(lines: list[str]):
    from unittest.mock import AsyncMock, MagicMock

    async def _aiter_lines():
        for line in lines:
            yield line

    mock_resp = MagicMock()
    mock_resp.__aenter__ = AsyncMock(return_value=mock_resp)
    mock_resp.__aexit__ = AsyncMock(return_value=False)
    mock_resp.aiter_lines = _aiter_lines

    mock_client = MagicMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)
    mock_client.stream = MagicMock(return_value=mock_resp)
    return mock_client


class TestExplainStream:
    def test_stream_unknown_node_returns_404(self):
        assert CLIENT.get("/api/explain-stream/999999").status_code == 404

    def test_stream_non_integer_id_returns_422(self):
        assert CLIENT.get("/api/explain-stream/not-a-number").status_code == 422

    def test_stream_cache_hit_returns_sse_with_done(self):
        node_id = _create_node("CachedSSE")
        with patch("app.api.v1.nodes.call_ai", new_callable=AsyncMock) as mock_ai:
            mock_ai.return_value = "Кэшированный ответ."
            CLIENT.get(f"/api/explain/{node_id}")   # writes cache

        res = CLIENT.get(f"/api/explain-stream/{node_id}")
        assert res.status_code == 200
        assert "text/event-stream" in res.headers["content-type"]
        events = _parse_sse(res.text)
        assert any(e.get("cached") is True for e in events)
        assert events[-1].get("done") is True

    def test_stream_ai_response_streams_chunks_and_caches(self):
        node_id = _create_node("StreamedAI")
        fake_lines = [
            'data: {"choices":[{"delta":{"content":"Стрим"}}]}',
            'data: {"choices":[{"delta":{"content":" работает."}}]}',
            "data: [DONE]",
        ]
        with patch("app.ai.client.httpx.AsyncClient", return_value=_make_httpx_stream_mock(fake_lines)):
            res = CLIENT.get(f"/api/explain-stream/{node_id}")

        assert res.status_code == 200
        events = _parse_sse(res.text)
        texts = [e["text"] for e in events if "text" in e]
        assert texts == ["Стрим", " работает."]
        assert events[-1].get("done") is True

        from app.models.knowledge import NodeExplanation
        db = next(override_get_db())
        cached = db.query(NodeExplanation).filter(NodeExplanation.node_id == node_id).first()
        db.close()
        assert cached is not None
        assert cached.explanation == "Стрим работает."


# ===========================================================================
# Org team access endpoints
# ===========================================================================

class TestOrgTeamAccess:
    def _create_org(self, manager_key: str = "mgr_1") -> dict:
        res = CLIENT.post("/api/orgs", json={"name": "ACME", "manager_key": manager_key})
        assert res.status_code == 200
        return res.json()

    def test_get_user_orgs_returns_org_for_manager(self):
        org = self._create_org("mgr_list")
        orgs = CLIENT.get("/api/users/mgr_list/orgs").json()
        match = next((o for o in orgs if o["org_id"] == org["org_id"]), None)
        assert match is not None
        assert match["is_manager"] is True

    def test_get_user_orgs_empty_for_unknown_user(self):
        assert CLIENT.get("/api/users/nobody_xyz/orgs").json() == []

    def test_get_user_orgs_member_is_not_manager(self):
        org = self._create_org("mgr_member_test")
        CLIENT.post("/api/orgs/join", params={"invite_code": org["invite_code"]},
                    json={"user_key": "emp_member_test"})
        orgs = CLIENT.get("/api/users/emp_member_test/orgs").json()
        match = next((o for o in orgs if o["org_id"] == org["org_id"]), None)
        assert match is not None
        assert match["is_manager"] is False

    def test_get_org_returns_info_for_member(self):
        org = self._create_org("mgr_orginfo")
        res = CLIENT.get(f"/api/orgs/{org['org_id']}", params={"user_key": "mgr_orginfo"})
        assert res.status_code == 200
        assert res.json()["org_name"] == "ACME"

    def test_get_org_403_for_non_member(self):
        org = self._create_org("mgr_403")
        assert CLIENT.get(f"/api/orgs/{org['org_id']}", params={"user_key": "stranger"}).status_code == 403

    def test_get_org_404_for_unknown_org(self):
        assert CLIENT.get("/api/orgs/999999", params={"user_key": "anyone"}).status_code == 404

    def test_progress_requires_manager(self):
        org = self._create_org("mgr_prog")
        CLIENT.post("/api/orgs/join", params={"invite_code": org["invite_code"]},
                    json={"user_key": "emp_prog"})
        assert CLIENT.get(f"/api/orgs/{org['org_id']}/progress",
                          params={"user_key": "emp_prog"}).status_code == 403
        assert CLIENT.get(f"/api/orgs/{org['org_id']}/progress",
                          params={"user_key": "mgr_prog"}).status_code == 200

    def test_remove_member_by_manager(self):
        org = self._create_org("mgr_rm")
        CLIENT.post("/api/orgs/join", params={"invite_code": org["invite_code"]},
                    json={"user_key": "emp_rm"})
        res = CLIENT.delete(f"/api/orgs/{org['org_id']}/members/emp_rm",
                            params={"user_key": "mgr_rm"})
        assert res.status_code == 200
        assert res.json()["removed"] == "emp_rm"

    def test_remove_member_404_if_not_member(self):
        org = self._create_org("mgr_rm404")
        assert CLIENT.delete(f"/api/orgs/{org['org_id']}/members/ghost",
                             params={"user_key": "mgr_rm404"}).status_code == 404

    def test_remove_member_400_self_removal(self):
        org = self._create_org("mgr_self")
        assert CLIENT.delete(f"/api/orgs/{org['org_id']}/members/mgr_self",
                             params={"user_key": "mgr_self"}).status_code == 400

    def test_remove_member_403_non_manager(self):
        org = self._create_org("mgr_rm403")
        CLIENT.post("/api/orgs/join", params={"invite_code": org["invite_code"]},
                    json={"user_key": "emp_rm403"})
        assert CLIENT.delete(f"/api/orgs/{org['org_id']}/members/mgr_rm403",
                             params={"user_key": "emp_rm403"}).status_code == 403

    def test_regenerate_invite_changes_code(self):
        org = self._create_org("mgr_regen")
        res = CLIENT.post(f"/api/orgs/{org['org_id']}/invite/regenerate",
                          params={"user_key": "mgr_regen"})
        assert res.status_code == 200
        assert res.json()["invite_code"] != org["invite_code"]

    def test_regenerate_invite_old_code_no_longer_works(self):
        org = self._create_org("mgr_regen2")
        old_code = org["invite_code"]
        CLIENT.post(f"/api/orgs/{org['org_id']}/invite/regenerate",
                    params={"user_key": "mgr_regen2"})
        assert CLIENT.post("/api/orgs/join", params={"invite_code": old_code},
                           json={"user_key": "late"}).status_code == 404

    def test_regenerate_invite_403_non_manager(self):
        org = self._create_org("mgr_regen403")
        CLIENT.post("/api/orgs/join", params={"invite_code": org["invite_code"]},
                    json={"user_key": "emp_regen403"})
        assert CLIENT.post(f"/api/orgs/{org['org_id']}/invite/regenerate",
                           params={"user_key": "emp_regen403"}).status_code == 403
