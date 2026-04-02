- # CLAUDE.md — VYUD LMS Project Instruction

> Этот файл описывает контекст, стек и соглашения проекта VYUD LMS.
> Читается Claude Code при старте каждой сессии.

---

## 1. Что это за проект

**VYUD LMS** — B2B LMS-платформа на базе графа знаний с интерфейсом через Telegram Mini App.

**Ключевая концепция:** вместо классического конструктора курсов — интерактивный граф знаний на ReactFlow. Пользователь движется по узлам графа, получает AI-объяснения, проходит квизы.

**Целевой рынок:** IT-команды и стартапы СНГ, 5–200 человек.  
**GTM-стратегия:** ручные продажи → бесплатный пилот → invoice → автоматизация после 3 клиентов.

**Репозитории:**
- Backend: `github.com/Retyreg/vyud-lms`
- Frontend TMA: `github.com/Retyreg/vyud-tma`

---

## 2. Технический стек

### Backend
| Компонент | Технология |
|-----------|-----------|
| Framework | FastAPI (Python 3.13) |
| ORM | SQLAlchemy + Alembic (миграции) |
| Database | Supabase PostgreSQL + pgvector |
| AI abstraction | LiteLLM |
| AI providers | Groq/Llama 3.1, Gemini |
| Auth | Telegram initData validation + Supabase RLS |

### Frontend
| Компонент | Технология |
|-----------|-----------|
| Framework | Next.js |
| Graph UI | ReactFlow |
| Editor | TipTap |
| Drag & drop | dnd-kit |
| Deploy | Vercel |

## Структура
- `backend/app/routers/` — эндпоинты
- `backend/app/services/` — бизнес-логика
- `backend/app/models/` — SQLAlchemy модели
- `frontend/components/` — React компоненты
- `vyud-tma/src/` — Telegram Mini App
---
## Правила кода
- Все миграции только через Alembic (`make migration`)
- Auth: всегда через `get_telegram_user` dependency
- Секреты: только из `os.getenv()`, никогда хардкод
- Коммиты: атомарные, один коммит = одна задача, максимум 72 символа
  - Формат: `feat/fix/chore: описание`
  - Пример: `feat: add SM-2 spaced repetition to knowledge nodes`
- Тесты: pytest, минимум smoke test на новый эндпоинт

## Что не трогать без явного указания
- Существующие Alembic миграции
- ReactFlow core в `frontend/`
- Supabase RLS политики
  
## 3. Схема базы данных

Четыре основные таблицы (миграция: `cc96d0acc729_initial_schema.py`):

```
courses          — курсы
lessons          — уроки внутри курса
knowledge_nodes  — узлы графа знаний
knowledge_edges  — связи между узлами
node_explanations — кэш AI-объяснений узлов (SSE-стриминг)
---
## 4. Архитектурные решения

### Выполнено (Фаза 1 — технический долг)
- [x] Alembic миграции вместо ручных скриптов
- [x] Фикс LiteLLM/Gemini интеграции
- [x] Telegram initData валидация
- [x] Supabase RLS включён
- [x] Секреты удалены из репозитория
- [x] Убран дублирующий endpoint для mark_node_complete

### В работе (Фаза 2)
- [ ] AI-объяснение узла графа с SSE-стримингом
- [ ] Кэширование объяснений в `node_explanations`

### Следующие фичи (приоритет)
1. **Командный доступ** — `org_id` + инвайт-система
2. **Дашборд прогресса** — аналитика для менеджера команды
3. SM-2 алгоритм повторений на узлах
4. Генерация графа знаний из PDF

---

## 5. Соглашения по коду

### API-ключи и конфиги
- Все секреты — только через `.env` файл
- GROQ_API_KEY читается **один раз** через `settings` объект
- Никаких хардкодных ключей в коде

### AI-запросы
- Всегда через LiteLLM (не прямые httpx вызовы)
- Провайдеры: `groq/llama-3.1-70b-versatile` (основной), Gemini (fallback)
- SSE-стриминг для длинных ответов

### Миграции
```bash
# Создать новую миграцию
alembic revision --autogenerate -m "description"

# Применить
alembic upgrade head

# Откатить
alembic downgrade -1
```

### Паттерн прогресса пользователя
- Прогресс привязан к `user_id` (Telegram ID), не глобальный
- RLS Supabase обеспечивает изоляцию данных между пользователями

---

## 6. Известные проблемы и решения

| Проблема | Решение |
|----------|---------|
| Cold start backend (free tier) | Настроить keep-alive ping на cron-job.org |
| Aider переключается на Anthropic API | `unset ANTHROPIC_API_KEY` перед запуском или `~/.aider.conf.yml` |
| Supabase email confirmation | Отключено: Auth → Sign In / Providers → Email → Confirm email = OFF |

---

## 7. Рабочий процесс с AI-инструментами

```
claude.ai (планирование)  →  Claude Code / Gemini CLI (реализация) - GitHub Copilot (CI/CD)
```

**claude.ai** используется для:
- Архитектурных решений и data model
- Разбора новых фич перед реализацией
- Стратегических решений по продукту

**Claude Code / Gemini CLI / GitHub Copilot ** используется для:
- Прямой реализации по готовому плану
- Git операций, установки пакетов
- Дебаггинга конкретных файлов

### Как начать новую сессию в claude.ai
Claude имеет доступ к истории этого проекта через `recent_chats`. При необходимости восстановить контекст — достаточно сказать "загрузи историю проекта".

---

## 8. Структура проекта (backend)

```
vyud-lms/
├── alembic/              # Миграции
│   └── versions/
├── app/
│   ├── api/              # FastAPI роуты
│   ├── core/             # settings, config
│   ├── models/           # SQLAlchemy модели
│   ├── schemas/          # Pydantic схемы
│   └── services/         # Бизнес-логика, AI-сервисы
├── .env                  # Не коммитить!
├── alembic.ini
└── main.py
```

---

## 9. Переменные окружения (`.env`)

```env
DATABASE_URL=postgresql+asyncpg://...
SUPABASE_URL=...
SUPABASE_ANON_KEY=...
SUPABASE_SERVICE_KEY=...
GROQ_API_KEY=...
GEMINI_API_KEY=...
TELEGRAM_BOT_TOKEN=...
```

---

## 10. Роадмап

| Фаза | Статус | Фичи |
|------|--------|------|
| 1. Технический долг | ✅ Готово | Alembic, RLS, валидация |
| 2. B2B-основание | 🔄 В работе | SSE AI, org_id, команды |
| 3. Learning | ⏳ Следующая | SM-2, PDF→граф |
| 4. AI-фичи | 📅 Мес. 4–6 | Квизы из PDF, NEO Assistant |
| 5. Интеграции | 📅 Мес. 7–12 | Teams, Slack, Marketplace |
| 6. Аналитика | 📅 Мес. 13–18 | Предиктивные алёрты, Revenue Intelligence |
