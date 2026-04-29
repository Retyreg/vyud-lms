# CLAUDE.md — VYUD LMS / VYUD Frontline

> Контекст для Claude Code. Читать в начале каждой сессии.
> Maintainer: @Retyreg · Обновлено: апрель 2026 (split bots, реальные VPS-пути)

---

## Два продукта, один backend

Один FastAPI backend обслуживает оба продукта. Это не пивот — это split into two products on a shared backend.

| Продукт | Интерфейс | Endpoints | Статус |
|---|---|---|---|
| VYUD Frontline | `vyud-tma` (отдельный репо) | `/api/sops/*`, `/api/orgs/*/sops` | Лидирующий, 3 мес фокус |
| VYUD LMS | `vyud-lms/frontend`, lms.vyud.online | `/api/courses/*`, `/api/nodes/*`, `/api/explain/*` | Второй продукт, поддерживается |

**VYUD Frontline** — B2B инструмент: менеджер загружает PDF с регламентом (SOP), AI извлекает шаги и генерирует квиз, сотрудник проходит в Telegram, менеджер видит completion в дашборде. ЦА: HoReCa, Retail, FMCG. **Северная звезда:** за 5 минут от PDF к первому сотруднику, прошедшему квиз. Все новые фичи идут сюда первыми.

**VYUD LMS** — self-learning через knowledge graph с AI-объяснениями. Web UI активно используется для демо и self-learning. Граф живёт и развивается, но медленнее — новые фичи добавляем только после первого платящего SOP-клиента.

**Репозитории:** Backend: `github.com/Retyreg/vyud-lms` · Frontend TMA: `github.com/Retyreg/vyud-tma`

---

## Session Start Checklist

```bash
git log --oneline -10      # что было последним
git status                 # есть ли незакоммиченное
gh issue list              # что в работе
gh pr list                 # что на ревью
```
Если что-то непонятно — **спроси у Димы**, не предполагай.

---

## Tech Stack (реальный)

| Слой | Технология |
|---|---|
| Backend | FastAPI (Python 3.13), SQLAlchemy **sync**, Alembic |
| Frontend (web) | Next.js 16, ReactFlow 12 (Web UI активно используется для демо) |
| Frontend (TMA) | Отдельный репо `vyud-tma` — Vite + React 19 + TypeScript + `@twa-dev/sdk` |
| Database | PostgreSQL через Supabase (eu-west-1), pgvector для Phase 4 |
| AI | LiteLLM → OpenRouter (Llama 3.3) + Groq + Gemini fallback |
| Auth | Telegram `initData` HMAC-SHA256 (`app/auth/telegram.py`) |
| Deploy | VPS `38.180.229.254:8000` (systemd) + Vercel (frontend) |
| Package mgr | `pip + requirements.txt` (не uv, не poetry) |

---

## Project Structure (как есть на диске)

```
vyud-lms/
├── backend/
│   ├── app/
│   │   ├── api/v1/        # courses, feedback, health, nodes, orgs, quiz, sops, streaks
│   │   ├── ai/            # client.py (OpenRouter SSE), agent.py
│   │   ├── auth/          # telegram.py (initData), dependencies.py
│   │   ├── core/deps.py   # DB session
│   │   ├── db/base.py     # Base + engine
│   │   ├── models/        # sop, course, knowledge, org, user, document, feedback, streak
│   │   ├── schemas/       # graph, org, sop, sr
│   │   ├── services/      # pdf.py, sm2.py, streak.py
│   │   └── main.py
│   ├── alembic/versions/  # 11 миграций, последняя — sops/sop_steps/sop_completions
│   └── tests/ · supabase/ (RLS) · requirements.txt
├── frontend/              # Next.js — Web UI для VYUD LMS
│   └── components/graph/ · panels/
├── docs/                  # ROADMAP.md, ADRs
└── CLAUDE.md

vyud-tma/src/              # Отдельный репо
├── api/lms.ts             # API client (VITE_LMS_URL)
├── components/            # BottomNav, Layout, QuestionCard, FileUploader...
├── contexts/AuthContext.tsx
└── pages/                 # SOPListPage, SOPPlayerPage, ManagerDashboard, UploadPage...
```

**TMA в отдельном репо `vyud-tma`.** Таблицы `knowledge_nodes`/`knowledge_edges`/`node_sr_progress` **сохранены намеренно** — ядро VYUD LMS (второй продукт), не удалять.

---

## Схема базы данных

### Активные таблицы
```
organizations        — команды менеджеров
org_members          — участники (user_key = telegram_id)
sops                 — СОП (привязан к org_id)
sop_steps            — шаги СОП
sop_completions      — прохождение СОП сотрудником
user_streaks         — серии дней активности
```

### Таблицы VYUD LMS (не удалять — это ядро второго продукта)
```
courses, lessons, knowledge_nodes, knowledge_edges,
node_explanations, node_sr_progress, document_chunks
```

---

## Что уже работает (не ломать)

SOP CRUD + PDF upload + AI quiz generation · Manager dashboard · Organizations + invite codes + white-label (`brand_color`, `logo_url`, `bot_username`) · SM-2 spaced repetition · Streaks · Feedback widget · Telegram initData auth через `Depends(get_telegram_user)`.

**VYUD LMS:** knowledge graph, AI-объяснения, SM-2, ReactFlow visualization.

**Demo Mode (апрель 2026):** публичный демо-доступ для B2B клиентов (инструмент продаж).

---

## Telegram-боты

Каждый продукт = свой бот. Это нужно чтобы пользователь сразу понимал, какой продукт решает его задачу.

| Бот | Продукт | Назначение в коде |
|---|---|---|
| `@VyudFrontlineBot` | VYUD Frontline | TMA-контейнер + push-уведомления сотрудникам (assignment, reminder, completion). Webhook-команды `/start`, `/mysops`, `/stats`, `/cert`, `/help` живут на нём. |
| `@VyudAiBot` | VYUD AI / VYUD LMS | Заготовка под будущую AI-генерацию курсов и квизов в @BotFather. В коде backend сейчас не используется. |

### Env vars
```
FRONTLINE_BOT_TOKEN=<токен от @VyudFrontlineBot>     # читается в services/telegram.py
FRONTLINE_BOT_USERNAME=VyudFrontlineBot              # для invite-ссылок и push-текстов
TELEGRAM_BOT_TOKEN=<legacy fallback>                  # читается если FRONTLINE_BOT_TOKEN не задан
```
Frontend (`vyud-tma`) читает `VITE_TMA_BOT_USERNAME` (default: `VyudFrontlineBot`) для invite-ссылок и support-handle.

### Где не должно быть хардкодов
`'VyudAiBot'` / `'VyudFrontlineBot'` нигде в коде явно не пишем — берём из `BOT_USERNAME` (backend, `app/services/telegram.py`) или из `import { BOT_USERNAME } from '../lib/bot'` (TMA).

---

## Demo Mode

### Архитектура
Параллельная auth, не затрагивает основной Telegram flow.

| Слой | Реализация |
|---|---|
| Модели | `app/models/demo.py` → `demo_users`, `demo_feedback` |
| Миграция | `alembic/versions/g1h2i3j4k5l6_add_demo_tables.py` |
| Seed | `app/demo/seed.py` — читает `app/demo/sops/index.json`, создаёт Course + KnowledgeNodes |
| Auth | `app/auth/demo.py` → `get_demo_user(X-Demo-Token)` |
| API | `app/api/v1/demo.py` + `app/api/v1/admin.py` |
| Frontend | `app/demo/page.tsx`, `app/demo/magic/[token]/page.tsx`, `app/admin/demo/page.tsx` |
| Components | `DemoBanner`, `DemoFeedbackModal` в `components/panels/` |
| Session lib | `lib/demo.ts` → localStorage key `demo_session` |

### Маршруты
```
POST  /api/v1/demo/register         → создать demo_user, вернуть magic link
GET   /api/v1/demo/auth/{token}     → валидация токена, обновить session_expires_at
POST  /api/v1/demo/feedback         → сохранить отзыв (требует X-Demo-Token)
GET   /api/v1/demo/ai-check         → остаток AI вызовов за сегодня
POST  /api/v1/demo/ai-increment     → счётчик AI вызовов +1 (лимит 10/день)
GET   /api/v1/admin/demo/users      → список demo users (X-Admin-Email)
GET   /api/v1/admin/demo/feedback   → список отзывов (X-Admin-Email)

/demo                               → регистрационный лендинг
/demo/magic/{token}                 → magic-link callback → /?demo=1
/admin/demo                         → admin read-only dashboard
```

### Env vars (добавить в .env)
```
FRONTEND_URL=https://lms.vyud.online   # для формирования magic link
ADMIN_EMAIL=vatyutovd@gmail.com         # защита /admin/demo
SMTP_HOST=                              # опционально; без него link на экране
SMTP_PORT=587
SMTP_USER=
SMTP_PASSWORD=
SMTP_FROM=
```

### Ограничения demo users
- ❌ Нельзя: создавать графы, приглашать команду, экспортировать
- ✅ Можно: смотреть seed-граф, AI объяснения (10/день), SM-2 повторения, прогресс
- ⏱ Сессия: 24ч с каждого magic-link открытия, архив через 14 дней

### Demo user_key в SM-2
`NodeSRProgress.user_key = "demo:{demo_user.id}"` — изолировано от Telegram users.

---

## Code Conventions

- **Python:** `black` (line 88), `ruff`, type hints на публичных функциях
- **Sync vs async:** код **sync SQLAlchemy** — держимся, не переписывать без причины
- **Auth:** всегда `Depends(get_telegram_user)`, никакого хардкода user_id
- **Секреты:** только `os.getenv()`, никогда в коде
- **Миграции:** только Alembic. Никаких `ALTER TABLE` в коде
- **Multi-tenant:** любой query по данным клиента фильтровать по `org_id`
- **Git:** Conventional Commits (`feat:`, `fix:`, `chore:`, `docs:`), атомарные коммиты, ветки `feature/<n>` или `fix/<n>`

---

## Что НЕ делать (guardrails)

1. ❌ Не удалять `knowledge_nodes`, `knowledge_edges`, `node_sr_progress` — ядро VYUD LMS
2. ❌ Не добавлять новые фичи Web UI до первого платящего SOP-клиента
3. ❌ Не подключать MongoDB, ElasticSearch, Celery, Redis — PostgreSQL + BackgroundTasks хватит
4. ❌ Не переписывать sync SQLAlchemy на async "ради чистоты"
5. ❌ Не менять структуру `/api/v1/` роутеров без согласования
6. ❌ Не добавлять зависимости в `requirements.txt` без спроса
7. ❌ Не принимать архитектурные решения — это Дима в claude.ai, сюда приходит готовый промпт
8. ❌ Не использовать `any`/`dict[str, Any]` в новых Pydantic схемах

---

## Agent Roles

**Claude Code — исполнитель по точному промпту.** Реализует то, что Дима решил в claude.ai. Не планирует архитектуру. Пишет код, коммитит атомарно, отвечает по-русски в саммари.

**GitHub Copilot — CI/deploy/tests/release.** Дебаг, тесты, GitHub Actions, PR descriptions. Не меняет архитектуру.

---

## Quick Commands

```bash
# Backend
cd backend && .venv/bin/uvicorn app.main:app --reload
.venv/bin/alembic upgrade head
.venv/bin/alembic revision --autogenerate -m "..."
.venv/bin/pytest && .venv/bin/ruff check app/

# Frontend (VYUD LMS Web UI)
cd frontend && npm run dev

# Deploy (VPS) — реальные путь, юзер и сервис
ssh root@38.180.229.254 'cd /var/www/vyud-lms && git pull && systemctl restart vyud-backend'
```

---

## Troubleshooting

| Симптом | Причина | Фикс |
|---|---|---|
| `ImportError` на старте | Venv не активирован | `source .venv/bin/activate` |
| `alembic upgrade` падает | Конфликт миграций | `alembic history`, разрешить heads |
| CORS ошибка во фронте | Неверный API URL | Проверить `NEXT_PUBLIC_API_URL` |
| AI call 429 | LiteLLM rate limit | Fallback chain: Groq → Gemini |
| Render cold start | Render убирается | Фронт и API указывают на VPS |
| Supabase pooler | Неверный порт | Порт 6543 (Transaction Pooler) |

---

## Roadmap Pointer

Актуальный roadmap — `docs/ROADMAP.md`. Текущая фаза: **Phase 2** (Day 2 frontend TMA + CI/CD + первый пилот).
