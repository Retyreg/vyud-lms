"""
E2E Smoke Test: PDF upload → AI quiz generation → employee completion → manager dashboard.

This test covers the full VYUD Frontline happy path without hitting real AI or PDF libs.
All external calls (PyMuPDF, LiteLLM/OpenRouter) are patched.

Flow under test:
  1. Manager creates org
  2. Employee joins org via invite code
  3. Manager uploads PDF → AI generates steps + quiz → SOP published
  4. Employee fetches SOP list → SOP appears
  5. Employee fetches SOP detail → steps and quiz_json present
  6. Employee posts completion (score 4/5)
  7. Manager checks dashboard → employee completion visible
"""
import io
import json
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

import app.main as main_module

CLIENT = TestClient(main_module.app)

# ---------------------------------------------------------------------------
# Fake AI responses
# ---------------------------------------------------------------------------

FAKE_STEPS = json.dumps([
    {"step_number": 1, "title": "Приветствие гостя", "content": "Встречайте гостя у входа с улыбкой."},
    {"step_number": 2, "title": "Принятие заказа", "content": "Запишите заказ и уточните пожелания."},
    {"step_number": 3, "title": "Подача блюд", "content": "Подавайте блюда строго по стандарту."},
])

FAKE_QUIZ = json.dumps([
    {
        "question": "Как нужно встречать гостя?",
        "options": ["С улыбкой", "Молча", "Отворачиваясь", "Сидя"],
        "correct_answer": "А",
        "explanation": "Приветствие с улыбкой создаёт позитивный первый контакт.",
    },
    {
        "question": "Что делают при принятии заказа?",
        "options": ["Записывают и уточняют", "Угадывают", "Молчат", "Жестикулируют"],
        "correct_answer": "А",
        "explanation": "Точная запись заказа исключает ошибки.",
    },
])

# Minimal 1-byte fake PDF (extract_text_from_pdf is mocked)
FAKE_PDF_BYTES = b"%PDF-1.0\n1 0 obj<</Type/Catalog>>endobj\n"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _create_org(manager_key: str = "mgr_smoke") -> dict:
    res = CLIENT.post("/api/orgs", json={"name": "Ресторан Тест", "manager_key": manager_key})
    assert res.status_code == 200, res.text
    return res.json()


def _upload_sop(org_id: int, manager_key: str = "mgr_smoke") -> dict:
    """Upload a fake PDF with mocked AI, return upload response."""
    with (
        patch("app.api.v1.sops.extract_text_from_pdf", return_value="Текст регламента для кафе."),
        patch("app.api.v1.sops.call_ai", new_callable=AsyncMock) as mock_ai,
    ):
        # First call → steps, second call → quiz
        mock_ai.side_effect = [FAKE_STEPS, FAKE_QUIZ]

        fake_file = io.BytesIO(FAKE_PDF_BYTES)
        res = CLIENT.post(
            f"/api/orgs/{org_id}/sops/upload-pdf",
            data={"user_key": manager_key, "title": "Стандарт обслуживания"},
            files={"file": ("standard.pdf", fake_file, "application/pdf")},
        )
    return res


# ---------------------------------------------------------------------------
# Smoke test — single end-to-end scenario
# ---------------------------------------------------------------------------

class TestSOPSmoke:
    """Full PDF → completion → dashboard smoke test."""

    def test_full_sop_flow(self):
        mgr_key = "mgr_e2e_smoke"
        emp_key = "emp_e2e_smoke"

        # ── Step 1: Manager creates org ──────────────────────────────────────
        org = _create_org(mgr_key)
        org_id = org["org_id"]
        invite_code = org["invite_code"]

        assert org_id > 0
        assert invite_code

        # ── Step 2: Employee joins org ───────────────────────────────────────
        join_res = CLIENT.post(
            "/api/orgs/join",
            params={"invite_code": invite_code},
            json={"user_key": emp_key},
        )
        assert join_res.status_code == 200, join_res.text

        # ── Step 3: Manager uploads PDF ──────────────────────────────────────
        upload_res = _upload_sop(org_id, mgr_key)
        assert upload_res.status_code == 200, upload_res.text

        upload_body = upload_res.json()
        assert upload_body["status"] == "ok"
        assert upload_body["steps_count"] == 3
        sop_id = upload_body["sop_id"]

        # ── Step 4: Employee fetches SOP list ────────────────────────────────
        list_res = CLIENT.get(f"/api/orgs/{org_id}/sops", params={"user_key": emp_key})
        assert list_res.status_code == 200, list_res.text

        sop_list = list_res.json()
        assert len(sop_list) >= 1

        matching = next((s for s in sop_list if s["id"] == sop_id), None)
        assert matching is not None, "Uploaded SOP not visible to employee"
        assert matching["status"] == "published"
        assert matching["is_completed"] is False  # not yet completed

        # ── Step 5: Employee fetches SOP detail ──────────────────────────────
        detail_res = CLIENT.get(f"/api/sops/{sop_id}")
        assert detail_res.status_code == 200, detail_res.text

        detail = detail_res.json()
        assert detail["title"] == "Стандарт обслуживания"
        assert len(detail["steps"]) == 3
        assert detail["steps"][0]["step_number"] == 1
        assert detail["steps"][0]["title"] == "Приветствие гостя"
        assert detail["quiz_json"] is not None
        assert len(detail["quiz_json"]) == 2  # 2 quiz questions from fake AI

        # ── Step 6: Employee completes SOP ───────────────────────────────────
        complete_res = CLIENT.post(
            f"/api/sops/{sop_id}/complete",
            params={"user_key": emp_key, "score": 4, "max_score": 5, "time_spent_sec": 90},
        )
        assert complete_res.status_code == 200, complete_res.text

        complete_body = complete_res.json()
        assert complete_body["status"] == "ok"
        assert complete_body["score"] == 4

        # ── Step 7: SOP list shows completed ────────────────────────────────
        list_after = CLIENT.get(f"/api/orgs/{org_id}/sops", params={"user_key": emp_key})
        assert list_after.status_code == 200, list_after.text

        updated = next((s for s in list_after.json() if s["id"] == sop_id), None)
        assert updated is not None
        assert updated["is_completed"] is True

        # ── Step 8: Manager sees completion in dashboard ─────────────────────
        dash_res = CLIENT.get(f"/api/orgs/{org_id}/sop-progress", params={"user_key": mgr_key})
        assert dash_res.status_code == 200, dash_res.text

        dash = dash_res.json()
        assert dash["org_name"] == "Ресторан Тест"

        emp_row = next((m for m in dash["members"] if m["user_key"] == emp_key), None)
        assert emp_row is not None, "Employee not in dashboard"

        sop_entry = next((s for s in emp_row["sops"] if s["sop_id"] == sop_id), None)
        assert sop_entry is not None
        assert sop_entry["completed"] is True
        assert sop_entry["score"] == 4
        assert sop_entry["max_score"] == 5


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------

class TestSOPEdgeCases:
    """Targeted edge-case checks for SOP endpoints."""

    def test_upload_pdf_empty_text_returns_400(self):
        org = _create_org("mgr_empty_pdf")
        org_id = org["org_id"]

        with patch("app.api.v1.sops.extract_text_from_pdf", return_value="   "):
            fake_file = io.BytesIO(FAKE_PDF_BYTES)
            res = CLIENT.post(
                f"/api/orgs/{org_id}/sops/upload-pdf",
                data={"user_key": "mgr_empty_pdf"},
                files={"file": ("empty.pdf", fake_file, "application/pdf")},
            )
        assert res.status_code == 400
        assert "empty" in res.json()["detail"].lower()

    def test_upload_pdf_ai_failure_returns_503(self):
        org = _create_org("mgr_ai_fail")
        org_id = org["org_id"]

        with (
            patch("app.api.v1.sops.extract_text_from_pdf", return_value="Some text."),
            patch("app.api.v1.sops.call_ai", new_callable=AsyncMock) as mock_ai,
        ):
            mock_ai.side_effect = RuntimeError("OpenRouter timeout")
            fake_file = io.BytesIO(FAKE_PDF_BYTES)
            res = CLIENT.post(
                f"/api/orgs/{org_id}/sops/upload-pdf",
                data={"user_key": "mgr_ai_fail"},
                files={"file": ("fail.pdf", fake_file, "application/pdf")},
            )
        assert res.status_code == 503

    def test_get_sop_not_found_returns_404(self):
        assert CLIENT.get("/api/sops/999999").status_code == 404

    def test_complete_sop_not_found_returns_404(self):
        res = CLIENT.post(
            "/api/sops/999999/complete",
            params={"user_key": "anyone", "score": 0, "max_score": 0, "time_spent_sec": 0},
        )
        assert res.status_code == 404

    def test_complete_sop_idempotent_updates_score(self):
        """Re-completing a SOP updates score, not duplicates."""
        org = _create_org("mgr_idem")
        org_id = org["org_id"]

        CLIENT.post("/api/orgs/join",
                    params={"invite_code": org["invite_code"]},
                    json={"user_key": "emp_idem"})

        upload_res = _upload_sop(org_id, "mgr_idem")
        assert upload_res.status_code == 200
        sop_id = upload_res.json()["sop_id"]

        CLIENT.post(f"/api/sops/{sop_id}/complete",
                    params={"user_key": "emp_idem", "score": 2, "max_score": 5, "time_spent_sec": 60})
        CLIENT.post(f"/api/sops/{sop_id}/complete",
                    params={"user_key": "emp_idem", "score": 5, "max_score": 5, "time_spent_sec": 45})

        dash = CLIENT.get(f"/api/orgs/{org_id}/sop-progress",
                          params={"user_key": "mgr_idem"}).json()
        emp_row = next((m for m in dash["members"] if m["user_key"] == "emp_idem"), None)
        sop_entry = next((s for s in emp_row["sops"] if s["sop_id"] == sop_id), None)

        assert sop_entry["score"] == 5  # updated, not duplicated

    def test_dashboard_non_manager_returns_403(self):
        org = _create_org("mgr_403_dash")
        CLIENT.post("/api/orgs/join",
                    params={"invite_code": org["invite_code"]},
                    json={"user_key": "emp_403_dash"})
        res = CLIENT.get(f"/api/orgs/{org['org_id']}/sop-progress",
                         params={"user_key": "emp_403_dash"})
        assert res.status_code == 403

    def test_sop_list_empty_when_no_sops(self):
        org = _create_org("mgr_nosops")
        res = CLIENT.get(f"/api/orgs/{org['org_id']}/sops",
                         params={"user_key": "mgr_nosops"})
        assert res.status_code == 200
        assert res.json() == []
