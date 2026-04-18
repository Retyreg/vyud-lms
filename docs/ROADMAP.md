# VYUD Platform Roadmap

> Два продукта на одном backend. VYUD Frontline — лидирующий продукт (фокус 3 месяца).
> VYUD LMS (Web) поддерживается параллельно, развивается медленнее.
> Обновлено: апрель 2026

---

## Архитектура

```
vyud-lms (this repo)
├── backend/        → shared FastAPI (обслуживает оба продукта)
├── frontend/       → VYUD LMS Web UI (lms.vyud.online)
└── docs/

vyud-tma (separate repo)
└── Telegram Mini App — VYUD Frontline
```

---

## Фаза 1 — B2B MVP ✅ ГОТОВО

**Backend**
- [x] FastAPI, SQLAlchemy sync, Alembic
- [x] Supabase Auth + RLS
- [x] AI pipeline: PyMuPDF → OpenRouter (Llama 3.3) → структурированный SOP + quiz
- [x] Модели: `sops`, `sop_steps`, `sop_completions`
- [x] Organizations + invite codes + white-label (`brand_color`, `logo_url`, `bot_username`)
- [x] SM-2 spaced repetition + streaks + feedback widget
- [x] Telegram initData HMAC-SHA256 auth
- [x] VPS deploy на `38.180.229.254:8000`

**VYUD LMS (Web)**
- [x] Knowledge graph (`knowledge_nodes`, adjacency tables) — ядро второго продукта
- [x] ReactFlow визуализация, mastery на нодах
- [x] AI-объяснения с кейс-стади
- [x] ROI dashboard, leaderboard, weekly chart
- [x] Course templates + onboarding checklist, welcome tour

---

## Фаза 2 — Текущий спринт (Day 2 + инфра)

**Цель:** VYUD Frontline полностью готов к пилоту.

| Задача | Описание | Статус |
|---|---|---|
| Day 2 Frontend TMA | `SOPListPage`, `SOPPlayerPage`, `ManagerDashboard` финализация | В работе |
| GitHub Actions CI | `ci.yml` (lint + migrations + pytest) | Не начато |
| GitHub Actions Deploy | `deploy.yml` (SSH → git pull → alembic → systemctl restart) | Не начато |
| E2E smoke test | PDF upload → quiz gen → TMA completion | Не начато |
| Первый пилот | HoReCa или Retail, 2 недели бесплатно | Поиск |

**Definition of done:** менеджер загружает PDF → через 2 минуты даёт ссылку сотруднику → видит completion в дашборде.

---

## Фаза 3 — Рост и монетизация (мес 1–3 после пилота)

**Цель:** 3 платящих клиента по 5,000₽/мес = 15,000₽ MRR.

**Только VYUD Frontline. Новые Web-фичи не добавляем до первого платящего клиента.**

### Маркетинг и онбординг
- [ ] Лендинг с открытой ценой (5,000₽/мес) — убирает round-trip "сколько стоит"
- [ ] Free tier навсегда: 1 активный SOP + до 5 сотрудников
- [ ] Библиотека 5–10 шаблонов SOP (открытие смены, HACCP, приёмка товара, правила кассира)
- [ ] Видео-демо 60 сек: "PDF → обучение за 5 минут"

### Удержание
- [ ] Assignments + deadlines: менеджер назначает SOP с дедлайном → пуш за 24ч
- [ ] Certificate verification URL: `lms.vyud.online/cert/XYZ` с QR
- [ ] Еженедельный email-дайджест менеджеру: кто прошёл, кто нет

### Биллинг
- [ ] ЮКасса: Starter 5,000₽/мес (1 SOP, до 20 чел) / Team 15,000₽/мес

---

## Фаза 4 — AI-фичи + Масштаб (мес 4–9)

**Цель:** 10–15 клиентов, 50–75K₽ MRR.

**VYUD Frontline**
- [ ] AI-перевод SOP на другие языки (русский → узбекский, и т.д.)
- [ ] NEO Assistant чатбот: сотрудник спрашивает по SOP → AI отвечает со ссылкой на step (pgvector + RAG)
- [ ] Photo automoderation: фото → AI проверяет соответствие SOP (для FMCG/Retail)
- [ ] SM-2 Daily Telegram push: каждое утро "повторите step #3"
- [ ] Invoice автогенерация, чурн-письма (14 дней неактивности)

**VYUD LMS** (разблокируется после 3 платящих SOP-клиентов)
- [ ] Спринт на топ-2-3 запроса от beta-пользователей
- [ ] Self-enrollment с оплатой (Stripe)

---

## Фаза 5 — Расширение (мес 10–18)

| Продукт | Фича | Обоснование |
|---|---|---|
| VYUD Frontline | REST API + Webhooks | Интеграции с 1С, Bitrix24, amoCRM → enterprise |
| VYUD Frontline | Frontline Performance Score | Predictive алерты за 48ч до провала |
| VYUD Frontline | Modules/Lessons иерархия | Только если клиенты просят разбить длинный SOP |
| VYUD LMS | Instructor-created courses | Content editor для авторов курсов |
| VYUD LMS | Public course catalog | Self-enrollment с оплатой |
| Оба | Казахский/узбекский UI | Только при выходе на рынок КЗ/УЗ |

---

## Web UI — что делаем параллельно

VYUD LMS Web — живой продукт для демо и self-learning.

**Делаем:**
- Критические баги чиним (краши, auth failures, потеря данных)
- Держим зависимости в безопасном состоянии

**Не делаем (до первого платящего SOP-клиента):**
- Новые Web-фичи
- UX-редизайн Web
- Новые Web-интеграции

**После 3 платящих SOP-клиентов:** 1 спринт в месяц на VYUD LMS по обратной связи от пользователей.

---

## Что взяли из анализа конкурентов

| Инсайт | Источник | Где используем |
|---|---|---|
| "PDF → курс за 5 минут" как главный message | iSpring | Лендинг Фазы 3 |
| Transparent pricing на сайте | iSpring, TalentLMS | Фаза 3 |
| Free tier навсегда | TalentLMS (12K клиентов без VC) | Фаза 3 |
| Certificate verification URL | — | Фаза 3 |
| Daily push + micro-learning | — | Фаза 4 |
| AI-перевод между языками | Docebo | Фаза 4 |

---

## Что отвергли и почему

| Идея | Причина отказа |
|---|---|
| VYUD-HIRE integration | Проекта не существует |
| Monorepo с 3 сервисами | Один backend + отдельный TMA репо — проще для соло-фаундера |
| MongoDB + ElasticSearch + Qdrant + Celery + Redis | PostgreSQL + BackgroundTasks закрывает всё до 10+ клиентов |
| uv + Docker Compose | pip + systemd на VPS + Vercel работает |
| SCORM/xAPI | Enterprise-feature, не для ЦА |
| Казахский/узбекский UI Day 1 | Preemptive — сначала клиенты, потом локализация |

---

## Ключевые метрики

| Метрика | Мес 3 | Мес 6 | Мес 12 |
|---|---|---|---|
| Платящих клиентов | 3 | 10 | 30 |
| MRR (₽) | 15,000 | 75,000 | 300,000 |
| Completion rate SOP | 60% | 70% | 75% |
| Time to first SOP published | 15 мин | 10 мин | 5 мин |
| Free → paid conversion | — | 5% | 10% |
