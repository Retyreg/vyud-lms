# CLAUDE.md — vyud-lms

## Стек
- Backend: FastAPI (Python 3.13), SQLAlchemy, Alembic, LiteLLM
- Frontend: Next.js, ReactFlow
- TMA: Vite + React + TypeScript (@twa-dev/sdk)
- DB: Supabase PostgreSQL (asyncpg)
- AI: LiteLLM → Groq (default) / Gemini / Claude (premium)
- Deploy: Vercel (TMA), VPS (backend)

## Правила кода
- Все миграции только через Alembic (`make migration`)
- Auth: всегда через `get_telegram_user` dependency
- Секреты: только из `os.getenv()`, никогда хардкод
- Коммиты: атомарные, один коммит = одна задача, максимум 72 символа
  - Формат: `feat/fix/chore: описание`
  - Пример: `feat: add SM-2 spaced repetition to knowledge nodes`
- Тесты: pytest, минимум smoke test на новый эндпоинт

## Структура
- `backend/app/routers/` — эндпоинты
- `backend/app/services/` — бизнес-логика
- `backend/app/models/` — SQLAlchemy модели
- `frontend/components/` — React компоненты
- `vyud-tma/src/` — Telegram Mini App

## Что не трогать без явного указания
- Существующие Alembic миграции
- ReactFlow core в `frontend/`
- Supabase RLS политики

## Текущий статус
- Фаза 1: завершена (Alembic, auth, RLS, секреты)
- Фаза 2: в работе (AI-объяснение узлов)
