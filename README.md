# VYUD LMS

Адаптивная система обучения с фокусом на ИИ.

## Структура
- `backend/`: FastAPI + PostgreSQL + LiteLLM
- `frontend/`: Next.js + Tailwind (TBD)

## Запуск бэкенда
1. `cd backend`
2. `pip install -r requirements.txt`
3. `uvicorn app.main:app --reload`
   * Сервер запустится на http://127.0.0.1:8000
   * Документация API: http://127.0.0.1:8000/docs

## Конфигурация
По умолчанию используется SQLite (`vyud_lms.db`). Для использования PostgreSQL установите переменную окружения `DATABASE_URL`.

## API
- `GET /api/knowledge-graph`: Получение дерева навыков.
