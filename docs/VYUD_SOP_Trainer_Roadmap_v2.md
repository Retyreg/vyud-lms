# VYUD SOP Trainer — Roadmap v2

> Обновлено: апрель 2026 после пивота с Knowledge Graph LMS на SOP Trainer.
> Источники: текущий код в `vyud-lms` + инсайты из конкурентного анализа (Docebo/TalentLMS/iSpring).

---

## Северная звезда

**Продукт в одном предложении:** Telegram Mini App, в котором менеджер за 5 минут превращает PDF с регламентом (SOP) в интерактивное обучение с квизом, отправляет команде и видит в дашборде кто прошёл и с каким результатом.

**Позиционирование:** AI-native Telegram-first тренажёр регламентов для фронтлайн-команд в HoReCa, Retail и FMCG. Не LMS, не курсы, не Docebo — простой инструмент для "новый сотрудник вышел во вторник, к четвергу знает наш регламент открытия смены".

**Anti-positioning:** мы не iSpring (слишком сложно, нет AI), не Docebo ($60K ACV убивает рынок), не классический LMS с модулями и SCORM.

---

## Фаза 1 — B2B MVP ✅ ГОТОВО

- Backend FastAPI с моделями `sops`, `sop_steps`, `sop_completions`
- 5 API endpoints: list, get, complete, upload PDF с AI генерацией, manager dashboard
- AI pipeline: PyMuPDF → OpenRouter (Llama 3.3) → структурированный SOP + quiz
- Organizations + invite codes + SM-2 + streaks + feedback widget
- VPS deploy на `38.180.229.254:8000`
- Legacy knowledge graph таблицы сохранены, не удалены

---

## Фаза 2 — Текущий спринт (Day 2 + инфра)

**Цель:** закрыть MVP и отдать пилоту.

| Задача | Описание | Статус |
|---|---|---|
| Day 2 Frontend | `SOPListPage`, `SOPPlayerPage`, `ManagerDashboard` | В работе |
| CLAUDE.md v2 | Сокращение до ~120 строк, убрать Knowledge Graph framing | В работе |
| GitHub Actions CI/CD | `ci.yml` (lint + migrations + pytest), `deploy.yml` (SSH на VPS) | Не начато |
| Первый пилотный клиент | HoReCa или Retail, бесплатные 2 недели | Поиск |

**Definition of done:** менеджер в Telegram загружает PDF → через 2 минуты даёт ссылку сотруднику → видит completion в дашборде.

---

## Фаза 3 — Рост и монетизация (месяцы 1-3 после пилота)

**Цель:** 3 платящих клиента по 5,000₽/мес = 15,000₽ MRR. Инсайты из TalentLMS/iSpring.

### Приоритет 1 — Маркетинг и онбординг (low-code работа)

- **Публичная страница с ценой.** 5,000₽/мес открыто на лендинге. iSpring и TalentLMS делают так — в СНГ это ускоряет сделку. Убирает round-trip "сколько стоит".
- **Free tier навсегда.** 1 активный SOP + до 5 сотрудников бесплатно. TalentLMS доказал: freemium + SEO = 12К клиентов без VC.
- **Library of ready-made SOP templates.** 5-10 готовых шаблонов под ЦА: открытие смены в кафе, санитария HACCP, приёмка товара, правила кассира, работа с жалобами. При регистрации клиент сразу видит — "так выглядит готовый продукт".
- **"PDF → обучение за 5 минут" как главный message.** Видео-демо 60 секунд на лендинге. Это тот же приём, что iSpring использует с PowerPoint — мгновенный результат продаёт.

### Приоритет 2 — Удержание (чтобы пилоты конвертились)

- **Assignments + deadlines.** Менеджер назначает SOP сотруднику с дедлайном → пуш в Telegram за 24 часа до и в день дедлайна. Главный аргумент "я хочу видеть кто НЕ прошёл".
- **Public certificate verification.** `lms.vyud.online/cert/XYZ123` с QR-кодом на сертификате. Для ресторана — бумажка на стенку для Роспотребнадзора. Маленькая фича, большой вес в продаже.
- **Email weekly digest менеджеру.** Каждую пятницу письмо: "Прогресс команды на этой неделе: 12 сотрудников прошли SOP, 3 не начали". Держит клиента залогиненным.

### Приоритет 3 — Чего НЕ делать в этой фазе

- ❌ Не добавлять Modules/Lessons иерархию — SOP flat список steps пока хватает
- ❌ Не делать казахский/узбекский UI — дождаться первого клиента из КЗ/УЗ
- ❌ Не писать SCORM/xAPI — это enterprise-feature, не для ЦА
- ❌ Не делать VYUD-HIRE интеграцию — проекта нет, это другая вселенная

---

## Фаза 4 — Масштаб (месяцы 4-9)

**Цель:** 10-15 клиентов, 50-75K₽ MRR, биллинг на автомате.

### AI-фичи (дифференциация от iSpring)

- **AI-перевод SOP на другие языки.** Менеджер загрузил на русском, AI сгенерировал узбекскую версию. iSpring этого не умеет.
- **NEO Assistant чатбот.** Сотрудник в Telegram задаёт вопрос по SOP → AI отвечает, ссылается на конкретный step. Основано на pgvector + RAG.
- **Photo automoderation.** Сотрудник прикладывает фото "как я разложил товар" → AI проверяет соответствие SOP. Для FMCG/Retail это киллер.
- **Quiz из свободного текста.** Не только из PDF — менеджер пишет "сделай квиз про правила кассира" → AI генерит 10 вопросов.

### Monetization автоматизация

- ЮКасса подписка: Starter 5,000₽/мес (1 SOP, до 20 чел) / Team 15,000₽/мес (unlimited SOP, до 100 чел) / Growth 30,000₽/мес (unlimited + API)
- Invoice генерация автоматическая
- Чурн-письма: если клиент не заходил 14 дней

### SM-2 + Daily Telegram push

- Твой готовый код SM-2 из mari-lingo-bot перенести на SOP steps
- Каждое утро 9:00 сотрудник получает "повторите step #3" — система гонит учиться, а не ждёт
- Это не модули Docebo, это **поведенческая** фича, которой ни у кого нет

---

## Фаза 5 — Расширение (месяцы 10-18)

**Цель:** 50+ клиентов, 250K₽+ MRR, подготовка к enterprise.

| Фича | Обоснование |
|---|---|
| REST API + Webhook SDK | Интеграции с 1С, Bitrix24, amoCRM — путь к enterprise |
| Team-wide analytics (Frontline Performance Score) | Из твоего memory: predictive алерты за 48ч до провала |
| White-label TMA | Компания получает свой Telegram Mini App со своим брендингом (у тебя уже есть `bot_username`, `brand_color`, `logo_url` в модели Organization!) |
| Modules/Lessons иерархия | Только если клиенты начнут просить разбить длинный SOP на разделы |
| Казахский/узбекский UI | Только при выходе на рынок КЗ/УЗ (сейчас РФ фокус) |

---

## Что взяли из конкурентов

| Инсайт | Источник | Где используем |
|---|---|---|
| Мгновенный результат ("курс за 5 минут") | iSpring | Главный message на лендинге Phase 3 |
| Transparent pricing на сайте | iSpring, TalentLMS | Phase 3 priority 1 |
| Free tier навсегда | TalentLMS | Phase 3 priority 1 |
| Certificate verification URL | CLAUDE_LMS.md security section | Phase 3 priority 2 |
| Daily push + micro-learning UX | CLAUDE_LMS Telegram UX | Phase 4 (после биллинга) |
| AI-перевод между языками | Docebo + CLAUDE_LMS AI tasks | Phase 4 |
| Skills intelligence связка | Docebo 365Talents acquisition | Future — Phase 5+ (через VYUD API) |

---

## Что отвергли и почему

| Идея из предложения | Причина отказа |
|---|---|
| VYUD-HIRE integration + shared JWT auth | Проекта VYUD-HIRE не существует. Параллельная вселенная. |
| Monorepo с 3 сервисами (api/ai/bot) | Усложняет структуру. Соло-фаундер, один backend + отдельный TMA репо проще. |
| MongoDB + ElasticSearch + MinIO + Qdrant | 7 компонентов инфры = 7 способов сломаться. PostgreSQL + pgvector закрывает всё. |
| Celery + Redis task queue | FastAPI BackgroundTasks хватит до 10+ клиентов. |
| uv + Docker Compose + Hetzner | Текущий pip + systemd на VPS + Render auto-deploy проще и работает. |
| SCORM/xAPI import | Enterprise-feature, не нужна HoReCa/Retail. |
| Готовый compliance-контент КЗ/УЗ | Это параллельный бизнес (создание курсов), не часть SaaS. |
| Казахский/узбекский Day 1 | Preemptive — сначала клиенты, потом локализация. |

---

## Ключевые метрики (пересмотренные под РФ реальность)

| Метрика | Месяц 3 | Месяц 6 | Месяц 12 |
|---|---|---|---|
| Платящие клиенты | 3 | 10 | 30 |
| MRR (₽) | 15,000 | 75,000 | 300,000 |
| Completion rate на SOP | 60% | 70% | 75% |
| Time to first SOP published | 15 мин | 10 мин | 5 мин |
| Free → paid conversion | — | 5% | 10% |

---

## Что я (Дима) делаю прямо сейчас

1. Закрываю Day 2 frontend (SOPListPage, SOPPlayerPage, ManagerDashboard)
2. Переписываю CLAUDE.md на ~120 строк под текущую реальность
3. Собираю GitHub Actions CI/CD
4. Ищу первого пилотного клиента из HoReCa/Retail

**После этого** — двигаюсь в Фазу 3 по приоритетам выше (лендинг + templates + assignments).
