"""
Low-level AI client via OpenRouter.

Single provider for all one-shot and streaming requests.
OpenRouter is OpenAI-compatible — same JSON format, different base URL.
"""
import json
import logging
import os

import httpx
from sqlalchemy.orm import Session

from app.models.knowledge import NodeExplanation

logger = logging.getLogger(__name__)

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
_OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
_MODEL = os.getenv("OPENROUTER_MODEL", "meta-llama/llama-3.3-70b-instruct")

_HEADERS = {
    "Content-Type": "application/json",
    "HTTP-Referer": "https://lms.vyud.online",
    "X-Title": "VYUD LMS",
}


def _auth_headers() -> dict:
    """Return auth header if key is configured, empty dict otherwise."""
    if OPENROUTER_API_KEY:
        return {"Authorization": f"Bearer {OPENROUTER_API_KEY}"}
    return {}


async def call_ai(prompt: str, system: str, json_mode: bool = True) -> str:
    """Send a prompt to OpenRouter and return the response text.

    Args:
        prompt: User message.
        system: System prompt.
        json_mode: Request JSON-object response format when True.

    Returns:
        AI response text.

    Raises:
        RuntimeError: If the request fails or key is not configured.
    """
    if not OPENROUTER_API_KEY:
        raise RuntimeError("OPENROUTER_API_KEY is not set")

    messages = [
        {"role": "system", "content": system},
        {"role": "user", "content": prompt},
    ]
    payload: dict = {
        "model": _MODEL,
        "messages": messages,
        "temperature": 0.4,
    }
    if json_mode:
        payload["response_format"] = {"type": "json_object"}

    async with httpx.AsyncClient() as client:
        response = await client.post(
            _OPENROUTER_URL,
            headers={**_HEADERS, **_auth_headers()},
            json=payload,
            timeout=90.0,
        )

    if response.status_code != 200:
        logger.error("OpenRouter error %s: %s", response.status_code, response.text[:300])
        raise RuntimeError(f"OpenRouter returned {response.status_code}")

    return response.json()["choices"][0]["message"]["content"]


_TUTOR_SYSTEM = (
    "Ты AI-тьютор платформы VYUD. Правила: "
    "начни с ключевой идеи (1-2 предложения), "
    "приведи конкретный пример из жизни, "
    "объясни почему это важно знать. "
    "Максимум 120 слов. "
    "Не используй слова 'данный', 'следует отметить'. "
    "Отвечай сразу — без вводных фраз типа 'Конечно!' или 'Отличный вопрос!'."
)


async def _stream_explanation(node_id: int, label: str, description: str | None, db: Session):
    """Async generator: streams OpenRouter SSE chunks, caches full text on finish."""
    if not OPENROUTER_API_KEY:
        yield f"data: {json.dumps({'error': 'AI not configured'})}\n\n"
        yield f"data: {json.dumps({'done': True})}\n\n"
        return

    description_part = f"\nКонтекст: {description}" if description else ""
    prompt = f"Объясни концепт '{label}' простым языком для новичка.{description_part}"
    messages = [
        {"role": "system", "content": _TUTOR_SYSTEM},
        {"role": "user", "content": prompt},
    ]
    payload = {
        "model": _MODEL,
        "messages": messages,
        "temperature": 0.4,
        "stream": True,
    }

    full_text_parts: list[str] = []

    try:
        async with httpx.AsyncClient() as client:
            async with client.stream(
                "POST",
                _OPENROUTER_URL,
                headers={**_HEADERS, **_auth_headers()},
                json=payload,
                timeout=90.0,
            ) as resp:
                async for line in resp.aiter_lines():
                    if not line.startswith("data: "):
                        continue
                    raw = line[6:]
                    if raw == "[DONE]":
                        break
                    try:
                        delta = json.loads(raw)["choices"][0]["delta"].get("content", "")
                    except (KeyError, json.JSONDecodeError):
                        continue
                    if delta:
                        full_text_parts.append(delta)
                        yield f"data: {json.dumps({'text': delta})}\n\n"
    except Exception as e:
        logger.error("OpenRouter streaming failed: %s", e)
        yield f"data: {json.dumps({'error': 'AI stream error'})}\n\n"
        yield f"data: {json.dumps({'done': True})}\n\n"
        return

    # Cache full explanation
    full_text = "".join(full_text_parts)
    if full_text:
        existing = db.query(NodeExplanation).filter(NodeExplanation.node_id == node_id).first()
        if existing:
            existing.explanation = full_text
        else:
            db.add(NodeExplanation(node_id=node_id, explanation=full_text))
        db.commit()

    yield f"data: {json.dumps({'done': True})}\n\n"
