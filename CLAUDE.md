# CLAUDE.md — VYUD SOP Trainer

> Этот файл описывает контекст, стек и соглашения проекта.
> Читается Claude Code при старте каждой сессии.

---

## 1. Что это за проект

**VYUD SOP Trainer** — B2B-платформа для быстрого онбординга и контроля знаний СОП (стандартных операционных процедур) через Telegram Mini App.

**Целевой сегмент:** HoReCa, Retail, FMCG, дистрибуция — компании 5–200 человек без собственной LMS.

**Ключевой flow:**
1. Менеджер загружает PDF с инструкцией/СОП
2. AI разбивает на 5–7 шагов + генерирует 5 вопросов
3. Сотрудник открывает Telegram → проходит карточки по шагам → мини-тест
4. Менеджер видит дашборд: кто что прошёл

**GTM:** ручные продажи → бесплатный пилот 2 нед → invoice от 5000₽/мес → автоматизация после 3 клиентов.

**Репозитории:**
- Backend: `github.com/Retyreg/vyud-lms`
- Frontend TMA: `github.com/Retyreg/vyud-tma`

---

## 2. Технический стек

### Backend
| Компонент | Технология |
|-----------|------------|
| Framework | FastAPI (Python 3.13) |
| ORM | SQLAlchemy + Alembic |
| Database | Supabase PostgreSQL + pgvector (eu-west-1) |
| AI | LiteLLM — Groq/Llama 3.3 (primary), Gemini (fallback) |
| Auth | Telegram initData HMAC validation |
| Deploy | VPS (38.180.229.254:8000) + systemd |

### Frontend (TMA)
| Компонент | Технология |
|-----------|------------|
| Framework | Vite + React 19 + TypeScript |
| UI | Inline styles + CSS variables (Telegram theme) |
| Routing | react-router-dom v7 |
| Deploy | Vercel (lms.vyud.online) |

---

## 3. Реальная структура проекта

```
vyud-lms/backend/
├── alembic/versions/        # Миграции (head: e5f6a7b8c9d0)
├── app/
│   ├── auth/
│   │   ├── dependencies.py  # get_telegram_user dependency
│   │   └── telegram.py      # HMAC verification
│   ├── db/
│   │   └── base.py          # Engine, SessionLocal, Base
│   ├── models/
│   │   ├── course.py        # Course, Lesson (legacy)
│   │   ├── knowledge.py     # KnowledgeNode/Edge/Explanation/SRProgress (legacy)
│   │   ├── org.py           # Organization, OrgMember (ACTIVE)
│   │   ├── document.py      # DocumentChunk (legacy)
│   │   ├── streak.py        # UserStreak (ACTIVE)
│   │   ├── sop.py           # SOP, SOPStep, SOPCompletion (NEW)
│   │   └── user.py          # User (DEAD CODE — не используется)
│   ├── services/
│   │   ├── pdf.py           # extract_text_from_pdf, chunk_text
│   │   ├── sm2.py           # SM-2 algorithm (legacy, not used in SOP)
│   │   └── streak.py        # update_streak, get_streak
│   └── main.py              # ВСЕ эндпоинты (1225 строк — TODO: разбить на роутеры)
├── requirements.txt
└── .env                     # Не коммитить!

vyud-tma/src/
├── api/lms.ts               # API client (VITE_LMS_URL)
├── components/
│   ├── BottomNav.tsx         # Навигация
│   ├── Layout.tsx            # Shell с header
│   ├── ProtectedRoute.tsx    # Auth guard
│   ├── QuestionCard.tsx      # Quiz UI (REUSE для SOP)
│   └── FileUploader.tsx      # PDF upload
├── contexts/AuthContext.tsx   # Telegram + Supabase auth
├── lib/
│   ├── telegram.ts           # TG WebApp helpers
│   └── supabase.ts           # Supabase client
└── pages/
    ├── SOPListPage.tsx        # Список СОП сотрудника (NEW)
    ├── SOPPlayerPage.tsx      # Карточки + тест (NEW)
    ├── ManagerDashboard.tsx   # Прогресс команды (NEW)
    ├── UploadPage.tsx         # Загрузка PDF (KEEP, adapt for SOP)
    ├── AuthPage.tsx           # Email auth (KEEP)
    ├── ProfilePage.tsx        # Профиль (KEEP)
    ├── TestPlayerPage.tsx     # Quiz player (REUSE pattern)
    ├── GraphPage.tsx          # Граф знаний (DEPRECATED — убрать из nav)
    ├── LeaderboardPage.tsx    # Лидерборд (DEPRECATED)
    ├── TestsPage.tsx          # Список тестов (DEPRECATED)
    └── HelpPage.tsx           # Помощь (KEEP)
```

---

## 4. Схема базы данных

### Активные таблицы
```
organizations        — команды менеджеров
org_members          — участники команды (user_key = telegram_id)
sops                 — СОП (привязан к org_id)
sop_steps            — шаги СОП (1, 2, 3...)
sop_completions      — прохождение СОП конкретным сотрудником
user_streaks         — серии дней активности
users_credits        — Supabase таблица (auth, credits — legacy)
```

### Legacy таблицы (не удалять, не использовать в новом коде)
```
courses, lessons, knowledge_nodes, knowledge_edges,
node_explanations, node_sr_progress, document_chunks
```

---

## 5. Правила кода

- Миграции только через Alembic (`alembic revision --autogenerate -m "..."`)
- Auth: `get_telegram_user` dependency для защищённых эндпоинтов
- Секреты: только `os.getenv()`, никогда хардкод
- Коммиты: атомарные, `feat/fix/chore: описание`, макс 72 символа
- AI вызовы: через `call_ai()` в main.py (TODO: вынести в services/ai.py)
- Новые эндпоинты: в main.py (TODO: разбить на роутеры после MVP)

## 6. Что НЕ трогать
- Существующие Alembic миграции
- Supabase RLS политики
- Organization/OrgMember модели (работают, используются)
- Legacy таблицы — не удалять, просто не использовать

---

## 7. Переменные окружения (.env)

```
DATABASE_URL=postgresql://...
SUPABASE_URL=...
SUPABASE_ANON_KEY=...
SUPABASE_SERVICE_KEY=...
GROQ_API_KEY=...
GEMINI_API_KEY=...
TELEGRAM_BOT_TOKEN=...
```

---

## 8. Текущий спринт: VYUD SOP MVP (10 дней)

### День 1-2: Backend — модели + API
- [ ] Модель SOP, SOPStep, SOPCompletion
- [ ] Alembic миграция (down_revision = 'e5f6a7b8c9d0')
- [ ] CRUD: создать SOP, получить SOP, список SOP для org
- [ ] POST /api/orgs/{id}/sops/upload-pdf → AI → шаги + вопросы
- [ ] POST /api/sops/{id}/complete → per-user completion

### День 3-5: Frontend — 3 экрана
- [ ] SOPListPage — сотрудник видит свои СОП
- [ ] SOPPlayerPage — карточки пошагово + тест
- [ ] ManagerDashboard — матрица сотрудники × СОП

### День 6-7: Интеграция
- [ ] Единый VITE_LMS_URL → VPS
- [ ] SOPList как главная страница (вместо UploadPage)
- [ ] E2E тест руками

### День 8-10: Демо
- [ ] Демо-СОП предзагружен
- [ ] QR-код генерация
- [ ] Loom-видео / живое демо
