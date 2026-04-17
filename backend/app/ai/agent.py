"""
AI mentor chain for per-lesson explanations.

Uses LiteLLM with Groq as primary provider and Gemini as fallback.
Configure via environment variables:
    GROQ_API_KEY      — Groq API key (primary, fast, free tier available)
    GEMINI_API_KEY    — Google Gemini API key (fallback)
    ANTHROPIC_API_KEY — Anthropic Claude API key (optional premium)
    LITELLM_MODEL     — Override default model (default: groq/llama-3.3-70b-versatile)
"""
import os
import logging
from litellm import acompletion

logger = logging.getLogger(__name__)

_DEFAULT_MODEL = os.getenv("LITELLM_MODEL", "groq/llama-3.3-70b-versatile")
_FALLBACK_MODEL = "gemini/gemini-2.0-flash"

MENTOR_SYSTEM = (
    "Ты — ИИ-ментор на платформе VYUD LMS. "
    "Отвечай кратко, мотивирующе и по существу. "
    "Используй примеры кода, если нужно."
)


async def get_ai_response(lesson_content: str, question: str) -> str:
    prompt = (
        f"Контекст текущего урока: {lesson_content}\n"
        f"Вопрос студента: {question}"
    )
    messages = [
        {"role": "system", "content": MENTOR_SYSTEM},
        {"role": "user", "content": prompt},
    ]

    for model in (_DEFAULT_MODEL, _FALLBACK_MODEL):
        try:
            response = await acompletion(model=model, messages=messages, temperature=0.4)
            return response.choices[0].message.content
        except Exception as e:
            logger.warning("Model %s failed: %s", model, e)

    raise RuntimeError("All AI providers unavailable")
