# CLAUDE.md — VYUD SOP Trainer

> Контекст для Claude Code. Читать в начале каждой сессии.
> Maintainer: @Retyreg · Обновлено: апрель 2026 · Pivot: Knowledge Graph LMS → SOP Trainer

## Что это за продукт

**VYUD SOP Trainer** — Telegram Mini App: менеджер загружает PDF с регламентом (SOP), AI извлекает шаги и генерирует квиз, сотрудник проходит обучение в Telegram, менеджер видит completion в дашборде. ЦА: HoReCa, Retail, FMCG. Цена: 5,000₽/мес после 2-недельного пилота. Это **не LMS** — нет модулей, курсов, видео. **Северная звезда:** за 5 минут от PDF к первому сотруднику, прошедшему квиз.

**GTM:** ручные продажи → бесплатный пилот 2 нед → invoice от 5000₽/мес → автоматизация после 3 клиентов.

**Репозитории:** Backend: `github.com/Retyreg/vyud-lms` · Frontend TMA: `github.com/Retyreg/vyud-tma`

## Session Start Checklist

```bash
git log --oneline -10      # что было последним
git status                 # есть ли незакоммиченное
gh issue list              # что в работе
gh pr list                 # что на ревью
```
Если что-то непонятно — **спроси у Димы**, не предполагай.

## Tech Stack (реальный)

| Слой | Технология |
|---|---|
| Backend | FastAPI (Python 3.13), SQLAlchemy **sync**, Alembic |
| Frontend (web) | Next.js 16, ReactFlow 12 (legacy graph UI пока живёт) |
| Frontend (TMA) | Отдельный репо `vyud-tma` — Vite + React 19 + TypeScript + `@twa-dev/sdk` |
| Database | PostgreSQL через Supabase (eu-west-1), pgvector для Phase 4 |
| AI | LiteLLM → OpenRouter (Llama 3.3) + Groq + Gemini fallback |
| Auth | Telegram `initData` HMAC-SHA256 (`app/auth/telegram.py`) |
| Deploy | VPS `38.180.229.254:8000` (systemd) + Vercel (frontend) |
| Package mgr | `pip + requirements.txt` (не uv, не poetry) |

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
│   ├── tests/ · supabase/ (RLS) · requirements.txt
├── frontend/              # Next.js — legacy graph UI, минимум app/
│   └── components/graph/ (legacy 29K) · panels/ (12 модалок)
├── render.yaml            # Render config (phasing out)
└── CLAUDE.md

vyud-tma/src/              # Отдельный репо
├── api/lms.ts             # API client (VITE_LMS_URL)
├── components/
│   ├── BottomNav.tsx       # Навигация
│   ├── Layout.tsx          # Shell с header
│   ├── ProtectedRoute.tsx  # Auth guard
│   ├── QuestionCard.tsx    # Quiz UI
│   └── FileUploader.tsx    # PDF upload
├── contexts/AuthContext.tsx
├── lib/telegram.ts · supabase.ts
└── pages/
    ├── SOPListPage.tsx     # Список СОП сотрудника
    ├── SOPPlayerPage.tsx   # Карточки + тест
    ├── ManagerDashboard.tsx
    ├── UploadPage.tsx
    └── AuthPage.tsx · ProfilePage.tsx · HelpPage.tsx
```

**Важно:** TMA в **отдельном репо** `vyud-tma`. Таблицы `knowledge_nodes`/`knowledge_edges`/`node_sr_progress` **сохранены намеренно** — legacy data SM-2, не удалять.

## Схема базы данных

### Активные таблицы
```
organizations        — команды менеджеров
org_members          — участники команды (user_key = telegram_id)
sops                 — СОП (привязан к org_id)
sop_steps            — шаги СОП (1, 2, 3...)
sop_completions      — прохождение СОП конкретным сотрудником
user_streaks         — серии дней активности
```

### Legacy таблицы (не удалять, не использовать в новом коде)
```
courses, lessons, knowledge_nodes, knowledge_edges,
node_explanations, node_sr_progress, document_chunks
```

## Что уже работает (не ломать)

SOP CRUD + PDF upload + AI quiz generation · Manager dashboard (`/api/v1/sops/.../progress`) · Organizations + invite codes + white-label (brand_color, logo_url, bot_username) · SM-2 spaced repetition · Streaks · Feedback widget · Telegram initData auth через `Depends(get_telegram_user)`.

## Code Conventions

- **Python:** `black` (line 88), `ruff`, type hints на публичных функциях
- **Sync vs async:** код **sync SQLAlchemy** — держимся, не переписывать без причины
- **Auth:** всегда `Depends(get_telegram_user)`, никакого хардкода user_id
- **Секреты:** только `os.getenv()`, никогда в коде
- **Миграции:** только Alembic. Никаких `ALTER TABLE` в коде (как в legacy `migrate_db.py`)
- **Multi-tenant:** любой query по данным клиента фильтровать по `org_id`
- **Git:** Conventional Commits (`feat:`, `fix:`, `chore:`), атомарные коммиты, ветки `feature/<n>` или `fix/<n>`

## Что НЕ делать (guardrails)

1. ❌ Не добавлять VYUD-HIRE integration, shared JWT auth, monorepo — проекта не существует
2. ❌ Не подключать MongoDB, ElasticSearch, MinIO, Qdrant, Celery, Redis — хватит PostgreSQL + BackgroundTasks
3. ❌ Не писать SCORM/xAPI импорт — не ЦА
4. ❌ Не делать казахский/узбекский UI preemptively — ждём клиента из региона
5. ❌ Не удалять `knowledge_nodes`, `knowledge_edges`, `node_sr_progress`
6. ❌ Не переписывать sync SQLAlchemy на async "ради чистоты"
7. ❌ Не менять структуру `/api/v1/` роутеров без согласования
8. ❌ Не добавлять зависимости в `requirements.txt` без спроса
9. ❌ Не принимать архитектурные решения — это Дима в claude.ai, сюда приходит готовый промпт
10. ❌ Не использовать `any`/`dict[str, Any]` в новых Pydantic схемах

## Agent Roles

**Claude Code — исполнитель по точному промпту.** Реализует то, что Дима решил в claude.ai. Не планирует архитектуру. Пишет код, коммитит атомарно, отвечает по-русски в саммари. **GitHub Copilot — CI/deploy/tests/release.** Дебаг, тесты, GitHub Actions, PR descriptions. Не меняет архитектуру.

## Who Do I Ask?

| Задача | Кому |
|---|---|
| Новая фича по готовому ТЗ | Claude Code |
| Архитектурное решение | Дима в claude.ai (**НЕ** Claude Code) |
| Дебаг упавшего теста / CI/CD | Copilot |
| Миграция Alembic | Claude Code |
| Рефакторинг без смены поведения | Copilot |
| PR description / changelog | Copilot |
| Обновление CLAUDE.md | Claude Code по промпту от Димы |

## Quick Commands

```bash
# Backend
cd backend && .venv/bin/uvicorn app.main:app --reload
.venv/bin/alembic upgrade head
.venv/bin/alembic revision --autogenerate -m "..."
.venv/bin/pytest && .venv/bin/ruff check app/

# Frontend (legacy web UI)
cd frontend && npm run dev

# Deploy (GitHub Actions в работе)
ssh vyud@38.180.229.254 'cd /srv/vyud-lms && git pull && systemctl restart vyud-lms'
```

## Переменные окружения (.env)

```
DATABASE_URL=postgresql://...
SUPABASE_URL=...
SUPABASE_ANON_KEY=...
SUPABASE_SERVICE_KEY=...
GROQ_API_KEY=...
GEMINI_API_KEY=...
OPENROUTER_API_KEY=...
TELEGRAM_BOT_TOKEN=...
```

## Troubleshooting

- **Claude Code auth issues:** `rm -rf ~/.claude && npm i -g @anthropic-ai/claude-code`
- **LiteLLM Gemini 404:** fallback chain настроен — Groq основной, Gemini второй
- **Render cold start:** фронт и API указывают на VPS, не на Render (phasing out)
- **Supabase pooler:** порт 6543 (Transaction Pooler), не 5432

## Roadmap Pointer

Актуальный roadmap — `docs/VYUD_SOP_Trainer_Roadmap_v2.md`. Текущая фаза: **Phase 2** (Day 2 frontend + CI/CD + первый пилот). Не забегать вперёд в Phase 3/4 без явного промпта.
