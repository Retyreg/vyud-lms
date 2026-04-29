# 🧠 VYUD — две платформы на одном бэкенде

> Два B2B-продукта поверх общего FastAPI-бэкенда:
> - **VYUD Frontline** — корпоративные регламенты в Telegram, AI генерирует шаги и квиз из PDF (лидирующий продукт, 3 мес фокус)
> - **VYUD LMS** — self-learning через граф знаний с AI-объяснениями и SM-2 повторением

---

## 🎯 Два продукта

| Продукт | Кому | Интерфейс | Бот | Endpoints |
|---|---|---|---|---|
| **VYUD Frontline** | HoReCa, Retail, FMCG (5–50 чел.) | TMA в репо [vyud-tma](https://github.com/Retyreg/vyud-tma) | [@VyudFrontlineBot](https://t.me/VyudFrontlineBot) | `/api/sops/*`, `/api/orgs/*` |
| **VYUD LMS** | IT-команды и стартапы СНГ | `vyud-lms/frontend` (Next.js) | [@VyudAiBot](https://t.me/VyudAiBot) | `/api/courses/*`, `/api/nodes/*`, `/api/explain/*` |

Северная звезда Frontline: за 5 минут от PDF до прохождения квиза первым сотрудником.

---

## 📦 Репозитории и инфраструктура

| Компонент | Репозиторий | URL | Хостинг |
|---|---|---|---|
| Backend (FastAPI) | [Retyreg/vyud-lms](https://github.com/Retyreg/vyud-lms) `/backend` | `38.180.229.254:8000` | VPS (systemd) |
| LMS Frontend (Next.js + граф) | [Retyreg/vyud-lms](https://github.com/Retyreg/vyud-lms) `/frontend` | `lms.vyud.online` | Vercel |
| Frontline TMA | [Retyreg/vyud-tma](https://github.com/Retyreg/vyud-tma) | открывается через @VyudFrontlineBot | Vercel |
| База данных | — | Supabase (eu-west-1) | Supabase |

---

## 🛠 Технологический стек

```
Backend: FastAPI (Python 3.13) · SQLAlchemy · Alembic · LiteLLM
Frontend: Next.js · ReactFlow · TypeScript
TMA: Vite · React · TypeScript · @twa-dev/sdk
Database: PostgreSQL (Supabase) · pgvector (планируется)
AI: LiteLLM → Groq (llama-3.3-70b) · Gemini (fallback)
Deploy: VPS (systemd) · Vercel · Render (auto-deploy)
```

---

## 🚀 Быстрый старт

```bash
# Backend
cd backend
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
cp .env.example .env # заполни DATABASE_URL, GROQ_API_KEY, TELEGRAM_BOT_TOKEN
.venv/bin/alembic upgrade head
.venv/bin/uvicorn app.main:app --reload

# Frontend
cd frontend
npm install
npm run dev # http://localhost:3000
```

### Переменные окружения

```env
DATABASE_URL=postgresql://... # Supabase connection string (Transaction Pooler, порт 6543)
GROQ_API_KEY=gsk_... # Groq API
GEMINI_API_KEY=... # Google Gemini (опционально, fallback)
ANTHROPIC_API_KEY=sk-ant-... # Claude API (опционально, premium модель)

# Frontline-бот (TMA + push сотрудникам)
FRONTLINE_BOT_TOKEN=... # @VyudFrontlineBot из @BotFather
FRONTLINE_BOT_USERNAME=VyudFrontlineBot
TELEGRAM_BOT_TOKEN=... # legacy fallback для FRONTLINE_BOT_TOKEN
```

### Команды Makefile

```bash
make migrate # alembic upgrade head
make migration msg= # alembic revision --autogenerate -m "..."
make rollback # alembic downgrade -1
```

---

## 🗄 Схема базы данных

```
courses — курсы, привязаны к организации (org_id)
knowledge_nodes — узлы графа (label, description, level, is_completed)
knowledge_edges — рёбра графа (source_id → target_id, weight)
node_explanations — кэш AI-объяснений (node_id, explanation, model)
node_sr_progress — SM-2 прогресс (node_id, user_key, ef, interval, repetitions)
organizations — организации (name, invite_code)
org_members — участники org (org_id, user_key, is_manager)
```

---

## 📡 API эндпоинты

### Граф и курсы
```
GET /api/health — статус системы
GET /api/courses/latest — последний курс (глобальный)
POST /api/courses/generate — генерация курса по теме (AI)
```

### AI-объяснение узла
```
GET /api/explain/{node_id} — объяснение узла (с кэшем)
GET /api/explain/{node_id}?regenerate=true — новое объяснение (сброс кэша)
POST /api/nodes/{node_id}/complete — пометить узел завершённым
```

### SM-2 интервальное повторение
```
POST /api/nodes/{node_id}/review — оценить узел (quality 0–5)
GET /api/nodes/{node_id}/sr-status — SR-статус узла для пользователя
GET /api/orgs/{org_id}/due-nodes — узлы к повторению сегодня
```

### Организации (B2B)
```
POST /api/orgs — создать организацию
POST /api/orgs/join?invite_code=XYZ — вступить по инвайт-коду
GET /api/orgs/{org_id}/courses/latest — граф курса организации
GET /api/orgs/{org_id}/progress — прогресс команды (для менеджера)
POST /api/orgs/{org_id}/courses/generate — генерация курса для org
```

---

## 🗺 Дорожная карта

### ✅ Фаза 0 — Технический долг (выполнено)

- Alembic миграции вместо ручных скриптов (`migrate_db.py` → `legacy/`)
- Фикс LiteLLM / Gemini 404 (v1alpha → v1, настроен fallback-chain)
- Telegram initData валидация (HMAC-SHA256)
- Supabase RLS политики (пользователь видит только свои данные)
- Удаление секретов из репозитория (`.env` в `.gitignore`)
- `CLAUDE.md` в корне проекта — контекст для Claude Code

---

### ✅ Фаза 1 — B2B MVP (выполнено)

**Цель:** первый платящий B2B-клиент через ручные продажи.

| Фича | Статус | Описание |
|---|---|---|
| AI-объяснение узла | ✅ | Клик на узел → LLM объясняет концепт, SSE-стриминг, кэш в БД |
| Командный доступ | ✅ | `org_id` + инвайт-ссылка, менеджер видит прогресс команды |
| SM-2 повторение | ✅ | Алгоритм SuperMemo-2 на узлах графа, перенесён из Mari Lingo Bot |
| Systemd сервис | ✅ | Бэкенд живёт на VPS, автоперезапуск при падении |

**Ключевые архитектурные решения:**
- `node_explanations` — кэш по `node_id`, уменьшает LLM-запросы в 10–100x
- `NodeSRProgress` — прогресс на пересечении `node_id × user_key` (индивидуальный SM-2)
- `localStorage` для `org_id` — намеренное упрощение для пилота, JWT-auth после валидации

---

### 🔄 Фаза 2 — Продуктовый рост (в работе, месяцы 2–4)

**Цель:** self-serve онбординг — клиент сам создаёт граф без помощи основателя.

| Фича | Приоритет | Описание |
|---|---|---|
| Генерация графа из PDF | Критично | PDF → chunking → pgvector → AI строит граф концептов |
| Streaks и геймификация | Высокий | Ежедневные серии, бейджи, тепловая карта активности |
| Self-serve онбординг | Высокий | Новый клиент регистрируется сам, in-app подсказки |
| Прогресс-визуализация | Средний | % мастерства на узле, история повторений |

**Технически для PDF-генерации:**
```
PyMuPDF → chunks (800 токенов, overlap 100) → text-embedding-3-small
→ pgvector (HNSW индекс) → cosine search → Claude prompt → граф JSON
```

---

### 📅 Фаза 3 — Монетизация (месяцы 5–9)

**Цель:** $3k MRR, автоматизация платежей.

| Фича | Описание |
|---|---|
| Stripe / ЮКасса | Автоплатежи после 3 ручных клиентов. Тарифы: Team $199/мес, Growth $399/мес |
| ROI-дашборд | Время онбординга до/после, completion rate — главный аргумент для CXO |
| White label TMA | Компания получает Telegram Mini App со своим брендингом |
| API для интеграций | REST API: создание графа, трекинг прогресса → путь к enterprise |

---

### 🔮 Фаза 4 — Enterprise и масштаб (месяцы 10–18)

| Фича | Описание |
|---|---|
| Командные графы знаний | Org создаёт граф → сотрудники проходят → менеджер видит completion |
| RAG на pgvector | База знаний компании → AI-тьютор отвечает только из неё |
| SCORM / xAPI импорт | Импорт курсов из Articulate, iSpring — снижает барьер переключения |
| SOC2 / GDPR подготовка | Для работы с enterprise и государственными клиентами |

---

## 💰 Go-to-Market стратегия

**ICP (Ideal Customer Profile):** IT-команды и стартапы СНГ, 5–50 человек, задача онбординга новых сотрудников.

**Путь к первым деньгам (Путь Б):**

```
1. Найди 5 тёплых контактов (IT-команды, знакомые компании)
2. Проблемное интервью: как онбордите? где хранятся знания?
3. Бесплатный 2-недельный пилот (основатель создаёт граф вручную)
4. Оффер $200–500/мес → счёт на email → договор офертой
5. После 3 клиентов → автоматизируй онбординг и биллинг
```

**Целевые метрики:**

| Метрика | Неделя 6 | Месяц 3 | Месяц 6 |
|---|---|---|---|
| Платящие клиенты | 1 | 3 | 10 |
| MRR | $300 | $900 | $3 000 |
| Retention 30d | — | >50% | >70% |

---

## 🤖 AI-пайплайн разработки

```
claude.ai → планирование, архитектура, PRD, ревью
Claude Code → реализация по готовому промпту
Aider / Copilot → рутинные правки
```

**Правило:** claude.ai думает → Claude Code делает. Claude Code не планирует — он реализует по точному промпту.

**Коммиты:** атомарные, один коммит = одна задача.
```
feat: add SM-2 spaced repetition to knowledge nodes
fix: litellm gemini 404 fallback chain
chore: add alembic migration for node_sr_progress
```

---

## 🔗 Связанные проекты

| Проект | URL | Описание |
|---|---|---|
| vyud-tma | через @VyudFrontlineBot | Telegram Mini App для VYUD Frontline (СОПы, прогресс сотрудников, дашборд менеджера) |
| vyud-saas-agent | sales.vyud.tech | AI Sales агент для SaaS-компаний |
| mari-lingo-bot | — | Telegram бот изучения марийского языка (SM-2 алгоритм) |

---

## 📝 Правила разработки (см. CLAUDE.md)

- Все миграции только через Alembic (`make migration`)
- Auth: всегда через `get_telegram_user` dependency
- Секреты: только из `os.getenv()`, никогда хардкод
- Тесты: pytest, минимум smoke test на новый эндпоинт
- Не трогать без явного указания: существующие миграции, ReactFlow core, Supabase RLS
