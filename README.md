# 🧠 VYUD AI (LMS) — Интерактивный граф знаний

## 📋 Обзор проекта
AI-платформа для обучения с визуализацией прогресса через граф знаний. Основатель: Retyreg

## 🛠 Технологический стек
- **Frontend**: Next.js (React), ReactFlow для графа.
- **Backend**: FastAPI (Python 3.13), SQLAlchemy, LiteLLM.
- **Database**: PostgreSQL в облаке Supabase (AWS-1-eu-west-1, Ирландия).
- **AI**: Поддержка моделей Groq (Llama 3.1) и Google Gemini.

## ⚙️ Инфраструктура базы данных
- **Host**: aws-1-eu-west-1.pooler.supabase.com
- **Port**: 6543 (Transaction Pooler)
- **Database**: postgres
- **Синхронизация**: Реализовано сохранение прогресса через поле `is_completed`. Узлы меняют цвет на #4ADE80 (зелёный) при завершении.

## ⚠️ Известные проблемы (Troubleshooting)
- **Gemini 404**: На текущий момент (март 2026) модель gemini-3-flash может выдавать ошибку 404 при использовании API v1alpha. Рекомендуется использовать v1 или переключаться на модели Groq для мгновенных ответов.

## 🚀 Как запустить
1. **Backend**: `DATABASE_URL="postgresql://user:pass@host:6543/postgres" uvicorn app.main:app --reload` (пароль требует URL-кодирования спецсимволов).
2. **Frontend**: `npm run dev` на порту 3000.
