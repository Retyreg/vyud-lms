# 📋 NEXT_STEPS — Дорожная карта VYUD LMS

> **Назначение этого файла:**  
> Здесь всегда актуальный список того, что уже сделано и что делаем дальше.  
> Обновляется после каждой сессии разработки.

---

## ⚡ Срочно (проблема «Сервер недоступен»)

**Симптом:** Vercel-сайт открывается, но внизу красная плашка «Сервер недоступен».  
**Причина:** Render.com free-plan засыпает через 15 минут без запросов.

### Быстрый фикс (уже в репо, заработает сам) ✅
- `keep-alive.yml` — GitHub Actions пингует `/api/health` **каждые 14 минут**. После мёрджа в `main` бэкенд перестанет засыпать.

### Правильное решение — переезд на Fly.io 🛩️
Fly.io бесплатно и **никогда не засыпает**. Конфиг уже в репо (`fly.toml`).

**Три шага для переезда (делается один раз):**
```bash
# 1. Зарегистрироваться на https://fly.io (нужна карта, но деньги не списываются)
# 2. Установить flyctl: https://fly.io/docs/hands-on/install-flyctl/
fly auth login

# 3. Создать приложение и задать секреты
fly apps create vyud-lms-backend
fly secrets set \
  DATABASE_URL="postgresql://..." \
  SECRET_KEY="your-secret-key" \
  GROQ_API_KEY="gsk_..." \
  GEMINI_API_KEY="..."

# 4. Первый деплой
fly deploy
```
После деплоя бэкенд будет на `https://vyud-lms-backend.fly.dev`.  
Обновить переменную на Vercel: `NEXT_PUBLIC_API_URL` → `https://vyud-lms-backend.fly.dev`

Все последующие деплои — автоматически при пуше в `main` (через `deploy-fly.yml`).

---

## ✅ Уже сделано

### Сессия 1 — Фундамент платформы
- [x] **Структура проекта** — монорепозиторий: `backend/` (FastAPI) + `frontend/` (Next.js)
- [x] **База данных** — PostgreSQL через Supabase; SQLAlchemy ORM; исправлена совместимость `postgres://` → `postgresql://` для SQLAlchemy 2.x
- [x] **Граф знаний** — модели `KnowledgeNode` / `KnowledgeEdge`, AI-генерация курса по теме (`POST /api/courses/generate`), визуализация через ReactFlow
- [x] **CI/CD** — GitHub Actions: lint → тесты → сборка Docker → security-scan
- [x] **Docker** — `Dockerfile` + `docker-compose.yml` (PostgreSQL + backend + frontend)
- [x] **Деплой** — `render.yaml` для Render.com (backend), Vercel (frontend)
- [x] **Здоровье системы** — `GET /api/health` возвращает статус БД, AI, аптайм; виджет в UI
- [x] **RBAC-роли** — `super_admin`, `regional_manager`, `store_manager`, `associate`

### Сессия 3 — Деплой: фикс «Сервер недоступен»
- [x] **Диагностика** — Render free plan засыпает через 15 мин → фикс через keep-alive пинги
- [x] **`keep-alive.yml`** — GitHub Actions cron каждые 14 мин пингует `/api/health` на Render
- [x] **`fly.toml`** — конфиг для Fly.io (не засыпает, бесплатно, Amsterdam)
- [x] **`deploy-fly.yml`** — auto-deploy при пуше в `main` через `FLY_API_TOKEN`
- [ ] **Выполнить миграцию на Fly.io** (нужен flyctl + секреты, 3 команды выше)

- [x] **JWT аутентификация** — `POST /api/v1/auth/register`, `POST /api/v1/auth/login`
  - Возвращает `access_token` (15 мин) + `refresh_token` (24 ч) по спеку 6.1
  - `POST /api/v1/auth/token/refresh` — обновление токена
  - `GET /api/v1/users/me` — текущий пользователь по токену
- [x] **Управление задачами** — полный CRUD (`GET/POST/PATCH/DELETE /api/v1/tasks`)
  - Статусы: `pending` → `in_progress` → `completed` / `overdue`
  - Чек-листы (JSON), фото-ссылки, приоритеты, назначение исполнителя
  - `completed_at` выставляется автоматически при завершении
- [x] **API курсов** — `GET /api/v1/courses`, `GET /api/v1/courses/{id}` с графом
- [x] **Прогресс обучения** — `POST /api/v1/courses/{id}/nodes/{node_id}/complete`
  - Проверяет выполнение пресквизитов перед отметкой
- [x] **Новостная лента** — полный CRUD (`GET/POST/PATCH/DELETE /api/v1/feed`)
  - Черновики (`is_published=False`) скрыты из ленты
- [x] **Тесты** — 68 тестов, 100% прохождение, покрытие: health, auth, курсы, задачи, лента

---

## 🚧 Делаем сейчас (Sprint 3)

### 1. RBAC — защита эндпоинтов по ролям 🔒
> Роли в модели уже есть. Нужно добавить проверку в эндпоинты.

- [ ] Добавить `require_role(*roles)` dependency в `main.py`
- [ ] Защитить `POST /api/v1/tasks` — только `store_manager` и выше
- [ ] Защитить `POST /api/v1/feed` — только `regional_manager` и выше
- [ ] Защитить `DELETE` эндпоинты — только `super_admin`
- [ ] Тесты на 403 при недостаточной роли

### 2. Загрузка фото к задачам 📸
> Сейчас `photo_url` — просто строка. Нужен реальный upload.

- [ ] Эндпоинт `POST /api/v1/tasks/{id}/photo` — принимает файл
- [ ] Сохранение в облако (AWS S3 или Supabase Storage)
- [ ] Возвращать публичный URL в `photo_url`

### 3. Frontend — страница задач 📱
> ReactFlow-граф есть. Нужна страница для работы с задачами.

- [ ] Компонент `TaskCard` — отображение задачи с чек-листом
- [ ] Страница `/tasks` — список задач с фильтрами по статусу
- [ ] Форма создания/редактирования задачи
- [ ] Интеграция с `GET/POST/PATCH /api/v1/tasks`

### 4. Frontend — лента новостей 📰
- [ ] Компонент `FeedCard` — карточка новости
- [ ] Страница `/feed` — скролл-лента с пагинацией
- [ ] Интеграция с `GET /api/v1/feed`

---

## 🔜 Следующие спринты (Backlog)

### Sprint 4 — Push-уведомления
- [ ] Интеграция Firebase Cloud Messaging (FCM)
- [ ] Модель `Notification` (тип, текст, user_id, прочитано/нет)
- [ ] `GET /api/v1/notifications` — список уведомлений
- [ ] `PATCH /api/v1/notifications/{id}/read` — отметить прочитанным
- [ ] Frontend: бейдж с количеством непрочитанных

### Sprint 5 — Отчётность и аналитика
- [ ] `GET /api/v1/analytics/tasks` — статистика выполнения задач по локации/роли
- [ ] `GET /api/v1/analytics/courses` — прогресс обучения по пользователям
- [ ] Дашборд для `regional_manager` — сводка по всем магазинам региона

### Sprint 6 — Мобильное приложение (PWA)
- [ ] Настройка Next.js как PWA (manifest.json, service worker)
- [ ] Офлайн-режим для просмотра курсов
- [ ] Установка на домашний экран (Add to Home Screen)

### Sprint 7 — SSO / Enterprise Auth
- [ ] Интеграция Auth0 или Cognito (SAML2 для корпоративных клиентов)
- [ ] Заменить self-issued JWT на Auth0-токены
- [ ] Provisioning пользователей через SCIM

---

## 🗂 Текущая архитектура

```
VYUD LMS
├── backend/
│   ├── app/
│   │   ├── main.py          ← Все API эндпоинты (FastAPI)
│   │   ├── db/base.py       ← SQLAlchemy engine + SessionLocal
│   │   └── models/
│   │       ├── user.py      ← User, UserRole (RBAC)
│   │       ├── task.py      ← Task, TaskStatus, TaskPriority
│   │       ├── course.py    ← Course, Lesson
│   │       ├── knowledge.py ← KnowledgeNode, KnowledgeEdge
│   │       └── news.py      ← NewsPost
│   └── tests/test_api.py    ← 68 тестов (pytest, SQLite in-memory)
├── frontend/
│   └── app/
│       └── page.tsx         ← Главная: ReactFlow-граф + HealthPanel
├── docker-compose.yml
├── render.yaml              ← IaC для Render.com
└── NEXT_STEPS.md            ← Этот файл 👈
```

---

## 📊 Метрики качества (на март 2026)

| Метрика | Значение |
|---|---|
| Тестов | 68 / 68 ✅ |
| CodeQL alerts | 0 ✅ |
| API эндпоинтов | 23 |
| Моделей БД | 5 |
| Покрытие спринтов | 2 из 7 |

---

*Последнее обновление: Сессия 2, март 2026*
