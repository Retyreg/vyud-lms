# 🧠 VYUD LMS — Операционная платформа обучения

AI-платформа для обучения фронтлайн-сотрудников (ритейл, HoReCa, логистика).  
Конкурент YOOBIC. Основатель: Retyreg.

## 📋 Текущее состояние (MVP, март 2026)

### Реализовано
- ✅ **Аутентификация** — регистрация, вход, JWT (access 15 мин / refresh 24 ч)
- ✅ **Задачи** — полный CRUD, чек-листы, статусы, фото-ссылки
- ✅ **Курсы** — AI-генерация, граф знаний, отметка прогресса по узлам
- ✅ **Новостная лента** — публикации, черновики, CRUD
- ✅ **CI/CD** — GitHub Actions (lint → test → build → security-scan)
- ✅ **Docker** — Dockerfile + docker-compose (PostgreSQL + MongoDB)

---

## 🛠 Технологический стек
| Слой | Технология |
|---|---|
| Backend API | FastAPI (Python 3.13), SQLAlchemy |
| База данных | PostgreSQL (Supabase, AWS eu-west-1) |
| AI | Groq Llama 3.3 + Google Gemini fallback |
| Auth | JWT (python-jose), bcrypt cost=12 |
| Frontend | Next.js 16, ReactFlow |
| Деплой | Render.com (backend), Vercel (frontend) |
| CI/CD | GitHub Actions |

---

## 🔌 API Reference (`/api/v1/`)

### Auth
| Метод | Путь | Описание |
|---|---|---|
| POST | `/api/v1/auth/register` | Регистрация (email, password, role) |
| POST | `/api/v1/auth/login` | Вход → access_token + refresh_token |
| POST | `/api/v1/auth/token/refresh` | Обновить access_token |
| GET  | `/api/v1/users/me` | Текущий пользователь (требует Bearer JWT) |

### Задачи
| Метод | Путь | Описание |
|---|---|---|
| GET    | `/api/v1/tasks` | Список задач (фильтры: status_filter, assignee_id) |
| POST   | `/api/v1/tasks` | Создать задачу |
| GET    | `/api/v1/tasks/{id}` | Получить задачу |
| PATCH  | `/api/v1/tasks/{id}` | Обновить задачу |
| DELETE | `/api/v1/tasks/{id}` | Удалить задачу |

### Курсы
| Метод | Путь | Описание |
|---|---|---|
| GET  | `/api/v1/courses` | Список курсов с прогрессом |
| GET  | `/api/v1/courses/{id}` | Курс с графом узлов и рёбер |
| POST | `/api/v1/courses/{id}/nodes/{node_id}/complete` | Отметить узел пройденным |
| POST | `/api/courses/generate` | Сгенерировать курс по теме (AI) |
| GET  | `/api/courses/latest` | Последний курс (для ReactFlow) |

### Лента новостей
| Метод | Путь | Описание |
|---|---|---|
| GET    | `/api/v1/feed` | Опубликованные посты (новые первыми) |
| POST   | `/api/v1/feed` | Создать пост |
| GET    | `/api/v1/feed/{id}` | Получить пост |
| PATCH  | `/api/v1/feed/{id}` | Обновить / снять с публикации |
| DELETE | `/api/v1/feed/{id}` | Удалить пост |

### Системные
| Метод | Путь | Описание |
|---|---|---|
| GET | `/` | Статус бэкенда |
| GET | `/api/health` | Статус всех компонентов (БД, AI, аптайм) |
| GET | `/api/explain/{topic}` | AI-объяснение темы |

---

## 🚀 Локальный запуск

### Docker (рекомендуется)
```bash
cp .env.example .env  # заполнить GROQ_API_KEY
docker compose up
# Backend: http://localhost:8000
# Frontend: http://localhost:3000
```

### Вручную
```bash
# Backend
cd backend
pip install -r requirements.txt
DATABASE_URL="postgresql://..." uvicorn app.main:app --reload

# Frontend
cd frontend
npm install && npm run dev
```

### Тесты
```bash
cd backend
python -m pytest tests/ -v
# 68 тестов, без внешних зависимостей (SQLite in-memory)
```

---

## ⚙️ Переменные окружения

| Переменная | Обязательная | Описание |
|---|---|---|
| `DATABASE_URL` | ✅ | PostgreSQL connection string |
| `GROQ_API_KEY` | ✅ | Groq API ключ (Llama 3.3) |
| `GEMINI_API_KEY` | — | Google Gemini (запасной AI) |
| `SECRET_KEY` | ✅ | JWT signing secret (генерировать случайный) |

---

## ⚠️ Известные ограничения / TODO

- **Auth0/Cognito SSO** — placeholder JWT сейчас работает, но для пилота нужна интеграция SAML2 (spec 6.1)
- **Photo upload** — эндпоинт задаёт `photo_url`, реальный upload через AWS S3 + CloudFront не реализован
- **RBAC Guards** — роли в модели есть, но проверка `role` на эндпоинтах не реализована
- **FCM Push** — Firebase Cloud Messaging не подключён
- **Gemini 404** — модель gemini-3-flash может выдавать ошибку 404 при использовании API v1alpha; рекомендуется Groq

