import json
import logging
import os
import re
import uuid

import httpx
from fastapi import APIRouter, File, Form, Header, HTTPException, UploadFile

from app.ai.client import call_ai
from app.services.pdf import extract_text_from_pdf

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["quiz"])


@router.post("/generate-file")
async def generate_file_quiz(
    file: UploadFile = File(...),
    num_questions: str = Form("10"),
    difficulty: str = Form("medium"),
    language: str = Form("Russian"),
    email: str = Form(...),
    telegram_id: str = Form(None),
    username: str = Form(None),
    x_api_key: str = Header(None, alias="x-api-key"),
):
    expected_key = os.getenv("API_KEY")
    if expected_key and x_api_key != expected_key:
        raise HTTPException(status_code=401, detail="Invalid API key")

    file_bytes = await file.read()
    try:
        text = extract_text_from_pdf(file_bytes)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Cannot read file: {e}")

    if not text.strip():
        raise HTTPException(status_code=400, detail="File is empty or unreadable")

    text = text[:12000]
    n = int(num_questions)

    diff_map = {
        "easy": "лёгкие вопросы на базовое понимание",
        "medium": "вопросы среднего уровня на применение знаний",
        "hard": "сложные вопросы на глубокий анализ",
    }
    diff_desc = diff_map.get(difficulty, diff_map["medium"])

    prompt = (
        f"На основе текста создай ровно {n} тестовых вопросов на {language} языке. "
        f"Сложность: {diff_desc}.\n\nТекст:\n{text}\n\n"
        f"Верни ТОЛЬКО валидный JSON-массив без текста вне массива:\n"
        f'[{{"id":"uuid","type":"single_choice","question":"...",'
        f'"options":["A","B","C","D"],"correct_answer":"A","explanation":"..."}}]'
    )

    raw = await call_ai(
        prompt,
        "Ты эксперт по образовательным тестам. Отвечай ТОЛЬКО валидным JSON-массивом.",
        json_mode=False,
    )

    if "```json" in raw:
        raw = raw.split("```json")[1].split("```")[0]
    elif "```" in raw:
        raw = raw.split("```")[1].split("```")[0]
    else:
        m = re.search(r"(\[[\s\S]*\])", raw)
        if m:
            raw = m.group(1)

    questions = json.loads(raw.strip())
    for q in questions:
        q["id"] = str(uuid.uuid4())

    quiz_id = str(uuid.uuid4())
    title = (file.filename or "Тест").rsplit(".", 1)[0]

    supabase_url = os.getenv("SUPABASE_URL")
    supabase_key = os.getenv("SUPABASE_SERVICE_KEY")
    sb_headers = {
        "apikey": supabase_key,
        "Authorization": f"Bearer {supabase_key}",
        "Content-Type": "application/json",
    }

    async with httpx.AsyncClient() as client:
        r = await client.get(
            f"{supabase_url}/rest/v1/users_credits",
            headers=sb_headers,
            params={"email": f"eq.{email}", "select": "credits"},
        )
        data = r.json()
        if not data:
            raise HTTPException(status_code=404, detail="User not found")
        credits = data[0].get("credits", 0)
        if credits < 1:
            raise HTTPException(status_code=402, detail="Insufficient credits")

        r = await client.post(
            f"{supabase_url}/rest/v1/quizzes",
            headers={**sb_headers, "Prefer": "return=minimal"},
            json={"id": quiz_id, "title": title, "questions": questions, "owner_email": email},
        )
        if r.status_code not in (200, 201):
            raise HTTPException(status_code=500, detail=f"Supabase error: {r.text}")

        await client.patch(
            f"{supabase_url}/rest/v1/users_credits",
            headers={**sb_headers, "Prefer": "return=minimal"},
            params={"email": f"eq.{email}"},
            json={"credits": credits - 1},
        )

    return {"test_id": quiz_id}
