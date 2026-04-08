"""
Centralized AI helpers: call_ai (non-streaming) and stream_explanation (SSE).

Uses Groq (direct httpx) as the primary provider and Gemini via LiteLLM as fallback.
"""
import json
import logging
import os

import httpx
from litellm import completion

logger = logging.getLogger(__name__)

GROQ_API_KEY = os.getenv("GROQ_API_KEY")


async def call_ai(prompt: str, system: str, json_mode: bool = True) -> str:
    """Call AI with Groq primary and Gemini fallback. Returns raw text."""
    messages = [
        {"role": "system", "content": system},
        {"role": "user", "content": prompt},
    ]
    try:
        payload = {
            "model": "llama-3.3-70b-versatile",
            "messages": messages,
            "temperature": 0.4,
        }
        if json_mode:
            payload["response_format"] = {"type": "json_object"}

        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://api.groq.com/openai/v1/chat/completions",
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
        logger.error(f"Groq failed: {str(e)}")

    # Fallback to Gemini via LiteLLM
    try:
        response = completion(model="gemini/gemini-2.0-flash", messages=messages)
        return response.choices[0].message.content
    except Exception as e:
        logger.error(f"Gemini fallback failed: {str(e)}")

    raise RuntimeError("All AI providers unavailable")


# ---------------------------------------------------------------------------
# Prompt constants shared by explain and explain-stream
# ---------------------------------------------------------------------------

TUTOR_SYSTEM_PROMPT = (
    "Ты AI-тьютор платформы VYUD. Правила: "
    "начни с ключевой идеи (1-2 предложения), "
    "приведи конкретный пример из жизни, "
    "объясни почему это важно знать. "
    "Максимум 120 слов. "
    "Не используй слова 'данный', 'следует отметить'. "
    "Отвечай сразу — без вводных фраз типа 'Конечно!' или 'Отличный вопрос!'."
)


def build_explain_prompt(label: str, description: str | None) -> str:
    description_part = f"\nКонтекст: {description}" if description else ""
    return f"Объясни концепт '{label}' простым языком для новичка.{description_part}"


async def stream_explanation(node_id: int, label: str, description: str | None, db):
    """Async generator: streams Groq SSE chunks, saves full text to cache on finish."""
    from app.models.knowledge import NodeExplanation

    prompt = build_explain_prompt(label, description)
    messages = [
        {"role": "system", "content": TUTOR_SYSTEM_PROMPT},
        {"role": "user", "content": prompt},
    ]

    full_text_parts: list[str] = []

    try:
        async with httpx.AsyncClient() as client:
            async with client.stream(
                "POST",
                "https://api.groq.com/openai/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {GROQ_API_KEY}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": "llama-3.3-70b-versatile",
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
            from litellm import acompletion as _acompletion

            fallback = await _acompletion(
                model="gemini/gemini-2.0-flash", messages=messages, temperature=0.4
            )
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
