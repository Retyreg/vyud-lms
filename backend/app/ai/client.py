"""
Low-level AI client: call_ai() for one-shot requests, _stream_explanation() for SSE streaming.

Primary provider: Groq (llama-3.3-70b-versatile).
Fallback provider: Gemini via LiteLLM.
"""
import json
import logging
import os

import httpx
from litellm import completion, acompletion as _acompletion
from sqlalchemy.orm import Session

from app.models.knowledge import NodeExplanation

logger = logging.getLogger(__name__)

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
_GROQ_CHAT_URL = "https://api.groq.com/openai/v1/chat/completions"
_GROQ_MODEL = "llama-3.3-70b-versatile"
_GEMINI_MODEL = "gemini/gemini-2.0-flash"


async def call_ai(prompt: str, system: str, json_mode: bool = True) -> str:
    """Send a prompt to Groq, falling back to Gemini on failure.

    Args:
        prompt: User message.
        system: System prompt.
        json_mode: If True, request JSON-object response format from Groq.

    Returns:
        AI response text.

    Raises:
        RuntimeError: If all providers fail.
    """
    messages = [
        {"role": "system", "content": system},
        {"role": "user", "content": prompt},
    ]
    try:
        payload: dict = {
            "model": _GROQ_MODEL,
            "messages": messages,
            "temperature": 0.4,
        }
        if json_mode:
            payload["response_format"] = {"type": "json_object"}

        async with httpx.AsyncClient() as client:
            response = await client.post(
                _GROQ_CHAT_URL,
                headers={
                    "Authorization": f"Bearer {GROQ_API_KEY}",
                    "Content-Type": "application/json",
                },
                json=payload,
                timeout=60.0,
            )
            if response.status_code == 200:
                return response.json()["choices"][0]["message"]["content"]
    except Exception as e:
        logger.error("Groq failed: %s", e)

    # Fallback to Gemini via LiteLLM
    try:
        response = completion(model=_GEMINI_MODEL, messages=messages)
        return response.choices[0].message.content
    except Exception as e:
        logger.error("Gemini fallback failed: %s", e)

    raise RuntimeError("All AI providers unavailable")


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
    """Async generator: streams Groq SSE chunks, saves full text to cache on finish."""
    description_part = f"\nКонтекст: {description}" if description else ""
    prompt = f"Объясни концепт '{label}' простым языком для новичка.{description_part}"
    messages = [
        {"role": "system", "content": _TUTOR_SYSTEM},
        {"role": "user", "content": prompt},
    ]

    full_text_parts: list[str] = []

    try:
        async with httpx.AsyncClient() as client:
            async with client.stream(
                "POST",
                _GROQ_CHAT_URL,
                headers={
                    "Authorization": f"Bearer {GROQ_API_KEY}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": _GROQ_MODEL,
                    "messages": messages,
                    "temperature": 0.4,
                    "stream": True,
                },
                timeout=60.0,
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
        logger.error("Groq streaming failed: %s", e)
        # Fallback: non-streaming Gemini
        try:
            fallback = await _acompletion(model=_GEMINI_MODEL, messages=messages, temperature=0.4)
            text = fallback.choices[0].message.content
            full_text_parts.append(text)
            yield f"data: {json.dumps({'text': text})}\n\n"
        except Exception as e2:
            logger.error("Gemini fallback failed: %s", e2)
            yield f"data: {json.dumps({'error': 'AI providers unavailable'})}\n\n"
            return

    # Save full explanation to cache
    full_text = "".join(full_text_parts)
    if full_text:
        existing = db.query(NodeExplanation).filter(NodeExplanation.node_id == node_id).first()
        if existing:
            existing.explanation = full_text
        else:
            db.add(NodeExplanation(node_id=node_id, explanation=full_text))
        db.commit()

    yield f"data: {json.dumps({'done': True})}\n\n"
