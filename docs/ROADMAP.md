# VYUD Platform Roadmap

> Два продукта на одном backend. VYUD Frontline — лидирующий продукт (фокус 3 месяца).
> VYUD LMS (Web) поддерживается параллельно и используется как demo-инструмент продаж.
> Обновлено: апрель 2026 · Конкурент: YOOBIC (реверс-инжиниринг, см. Discovery/)

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

## Конкурентное позиционирование

**Главный конкурент для изучения: YOOBIC** (Series C, $97M, 200+ чел, выход в прибыль 2021).
YOOBIC создал категорию «Frontline OS» — объединение WFM + LMS + Employee Experience.
Их moat — 200+ интеграций с ERP/POS и 100M+ накопленных миссий для обучения ML-моделей.

**Наша позиция (на старте):** глубокая вертикальная специализация, а не горизонтальная платформа.
YOOBIC слишком сложен для малого и среднего HoReCa/Retail. Мы — «YOOBIC для тех, кому YOOBIC не по карману и не нужен».

| Измерение | YOOBIC | VYUD Frontline |
|---|---|---|
| Целевой клиент | Enterprise (Lacoste, Carrefour) | SMB HoReCa/Retail (5–200 сотрудников) |
| Time-to-value | Недели (внедрение, обучение) | **5 минут** (PDF → квиз → первый сотрудник) |
| Ценообразование | Закрытое, enterprise-контракты | Открытое, self-serve, 5,000₽/мес |
| Интеграции | 200+ (ERP, POS, SAP) | Telegram (уже там, где сотрудники) |
| AI | NEO Assistant, предиктивная аналитика | PDF → SOP + квиз, SM-2 повторения |

**Ключевой инсайт из анализа YOOBIC:**
> Willingness to pay у директора магазина — крайне высокая, потому что продукт напрямую влияет на его бонусы через KPI.

Продаём не «обучение», а **«выполнение стандартов, которое видно в цифрах»**.

---

## Фаза 1 — B2B MVP ✅ ГОТОВО

**Backend**
- [x] FastAPI, SQLAlchemy sync, Alembic, Supabase PostgreSQL
- [x] AI pipeline: PyMuPDF → OpenRouter (Llama 3.3) → структурированный SOP + квиз
- [x] Модели: `sops`, `sop_steps`, `sop_completions`
- [x] Organizations + invite codes + white-label (`brand_color`, `logo_url`, `bot_username`)
- [x] SM-2 spaced repetition + streaks + feedback widget
- [x] Telegram initData HMAC-SHA256 auth
- [x] SOP template library backend
- [x] VPS deploy на `38.180.229.254:8000`

**VYUD LMS (Web)**
- [x] Knowledge graph + ReactFlow визуализация
- [x] AI-объяснения с кейс-стади
- [x] ROI dashboard, leaderboard, weekly chart
- [x] Course templates + onboarding checklist, welcome tour

**Инфра**
- [x] GitHub Actions CI: lint + migrations + pytest (ci.yml)
- [x] GitHub Actions Deploy: SSH → git pull → alembic → systemctl restart
- [x] E2E smoke test в CI pipeline

---

## Фаза 2 — Sales Enablement ✅ ГОТОВО (апрель 2026)

**Цель:** инструменты для поиска первого платящего клиента.

| Задача | Статус |
|---|---|
| Demo Mode (lms.vyud.online/demo) | ✅ Готово |
| SOP-библиотека: 15 SOP × 2 языка × 5 сегментов | ✅ Готово |
| Demo seed: граф + AI объяснения + SM-2 per user | ✅ Готово |
| Magic-link auth (без пароля) | ✅ Готово |
| Demo feedback modal + "Хочу пилот" checkbox | ✅ Готово |
| Admin dashboard /admin/demo | ✅ Готово |
| Favicon VYUD LMS | ✅ Готово |
| Day 2 Frontend TMA (SOPListPage, SOPPlayerPage, ManagerDashboard) | ⏳ В работе |
| Первый пилот (HoReCa или Retail, 2 недели бесплатно) | 🔍 Поиск |

**Definition of done Фазы 2:** менеджер загружает PDF → через 5 минут даёт ссылку сотруднику → видит completion в дашборде.

---

## Фаза 3 — Первые 3 платящих клиента (мес 1–3 после пилота)

**Цель:** 3 клиента × 5,000₽/мес = 15,000₽ MRR.
**Фокус только VYUD Frontline.** Новые Web-фичи не трогаем до 1 платящего клиента.

### GTM: Land & Expand (инсайт из YOOBIC)

**Land:** бесплатный пилот на 1 локацию/смену → 2 недели → видимый результат → чек.
**Expand:** начинаем с "Обучение по SOP" → продаём "Задачи + дедлайны" → продаём "Аналитика".
**C2B Loop:** менеджер, который использовал VYUD, уходит в другую компанию и приносит нас с собой. Инвестируем в опыт менеджера = долгосрочный growth loop.

### Продуктовые задачи

- [ ] **Assignments + deadlines:** менеджер назначает SOP с дедлайном → Telegram-пуш за 24ч
- [ ] **Certificate verification URL:** `lms.vyud.online/cert/XYZ` с QR для распечатки
- [ ] **Еженедельный дайджест:** отчёт менеджеру в Telegram — кто прошёл, кто нет, кто застрял
- [ ] **Free tier:** 1 активный SOP + до 5 сотрудников навсегда (инсайт TalentLMS: 12K клиентов без VC)
- [ ] **Открытый прайс** на лендинге: 5,000₽/мес Starter / 15,000₽/мес Team (убирает round-trip)

### Маркетинг

- [ ] Видео-демо 60 сек: «PDF → обучение за 5 минут» — главный message (инсайт iSpring)
- [ ] 5–10 шаблонов SOP публично: открытие смены, HACCP, приёмка товара, правила кассира
- [ ] Лендинг vyud.online/frontline с ценой и CTA «Начать бесплатно»

### Биллинг

- [ ] ЮКасса: Starter 5,000₽/мес (1 SOP, до 20 чел) / Team 15,000₽/мес (5 SOP, до 100 чел)

---

## Фаза 4 — AI-фичи + Масштаб (мес 4–9)

**Цель:** 10–15 клиентов, 50–75K₽ MRR.

### VYUD Frontline

- [ ] **NEO Assistant** (инсайт YOOBIC): сотрудник пишет вопрос → AI отвечает со ссылкой на шаг SOP (pgvector + RAG)
- [ ] **SM-2 Daily Push:** каждое утро в Telegram «Повторите шаг #3» — снижает текучку через вовлечённость
- [ ] **AI-перевод SOP** (инсайт Docebo): русский → узбекский/казахский/таджикский — ключевое для HoReCa
- [ ] **Photo automoderation** (инсайт YOOBIC): фото витрины → AI проверяет соответствие планограмме
- [ ] **Frontline Performance Score** (инсайт YOOBIC): предиктивный алерт за 48ч до «провала» сотрудника
- [ ] Invoice автогенерация, чурн-письма (14 дней неактивности)

### VYUD LMS (разблокируется после 3 платящих SOP-клиентов)

- [ ] Спринт на топ-2-3 запроса от demo/beta-пользователей (собираем через /admin/demo)
- [ ] Self-enrollment с оплатой (ЮКасса/Stripe)

---

## Фаза 5 — API + Enterprise (мес 10–18)

**Цель:** 30+ клиентов, выход на 300K₽ MRR. Начало enterprise-сделок.

| Продукт | Фича | Обоснование |
|---|---|---|
| VYUD Frontline | REST API + Webhooks | Интеграции с 1С, Bitrix24, amoCRM → enterprise (инсайт YOOBIC) |
| VYUD Frontline | Модули/уроки иерархия | Только если клиенты просят разбить длинный SOP |
| VYUD LMS | Instructor-created courses | Content editor для авторов курсов |
| VYUD LMS | Public course catalog | Self-enrollment с оплатой |
| Оба | Казахский/узбекский UI | Только при выходе на рынок КЗ/УЗ |

**Что брать из YOOBIC-плейбука на этом этапе:**
- Маркетплейс интеграций снижает churn → строим после 10+ клиентов
- NDR > 110% = цель (допродажи внутри текущей базы важнее новых клиентов)
- Customer Success как отдельная функция — при 10+ клиентах

---

## Web UI — политика параллельной разработки

- ✅ Критические баги чиним
- ✅ Demo Mode поддерживаем (sales tool)
- ❌ Новые Web-фичи — до первого платящего SOP-клиента
- После 3 платящих SOP-клиентов: 1 спринт в месяц на VYUD LMS по отзывам из /admin/demo

---

## Что отвергли и почему

| Идея | Причина отказа |
|---|---|
| Горизонтальная платформа (как YOOBIC) сразу | Нет ресурсов, нет данных. Сначала глубина в одной вертикали |
| Enterprise с самого начала | CAC слишком высокий, цикл сделки 3–6 мес — не выживем |
| MongoDB + ElasticSearch + Celery + Redis | PostgreSQL + BackgroundTasks хватит до 10+ клиентов |
| SCORM/xAPI | Enterprise-feature, не для нашей ЦА |
| Казахский/узбекский UI Day 1 | Preemptive — сначала клиенты, потом локализация |
| uv + Docker Compose | pip + systemd на VPS + Vercel работает |
| Monorepo с 3 сервисами | Один backend + отдельный TMA репо — проще для соло-фаундера |

---

## Ключевые метрики

| Метрика | Сейчас (апр 2026) | Мес 3 | Мес 6 | Мес 12 |
|---|---|---|---|---|
| Платящих клиентов | 0 | 3 | 10 | 30 |
| MRR (₽) | 0 | 15,000 | 75,000 | 300,000 |
| Demo-регистраций | — | 50 | — | — |
| Pilot requests из demo | — | 5 | — | — |
| SOP Completion rate | — | 60% | 70% | 75% |
| Time to first SOP published | ~15 мин | 10 мин | 7 мин | 5 мин |
| NDR (цель с Фазы 4) | — | — | — | >110% |

---

## Что взяли из анализа конкурентов

| Инсайт | Источник | Где используем |
|---|---|---|
| "PDF → курс за 5 минут" как главный message | iSpring | Лендинг Фазы 3 |
| Transparent pricing на сайте | iSpring, TalentLMS | Фаза 3 |
| Free tier навсегда | TalentLMS (12K клиентов без VC) | Фаза 3 |
| Certificate verification URL | — | Фаза 3 |
| Land & Expand GTM | YOOBIC | Фаза 3 — продаём по модулю, расширяем |
| C2B viral loop (менеджер меняет компанию) | YOOBIC | Фаза 3 — инвестируем в опыт менеджера |
| Daily push + micro-learning | YOOBIC | Фаза 4 — SM-2 Daily Push |
| NEO Assistant чатбот по SOP | YOOBIC | Фаза 4 — pgvector + RAG |
| Photo automoderation | YOOBIC | Фаза 4 — для FMCG/Retail |
| Frontline Performance Score | YOOBIC | Фаза 4 — предиктивные алерты |
| AI-перевод между языками | Docebo | Фаза 4 — русский → узбекский |
| Маркетплейс интеграций снижает churn | YOOBIC (200+ интеграций) | Фаза 5 — REST API + Webhooks |
| NDR > 110% через допродажи | YOOBIC | Фаза 5 — Customer Success функция |
