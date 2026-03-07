from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List, Optional
import os
from litellm import completion

from app.db.base import Base, engine, SessionLocal
import app.models 
from app.models.course import Course
from app.models.knowledge import KnowledgeNode, KnowledgeEdge

# Создаем таблицы при старте приложения
Base.metadata.create_all(bind=engine)

app = FastAPI(title="VYUD LMS API", version="0.1.0")

# Dependency
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Настройка CORS для общения с Next.js
origins = [
    "http://localhost:3000",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def read_root():
    return {"message": "Welcome to VYUD LMS API"}

@app.get("/health")
def health_check():
    return {"status": "ok"}

# --- Pydantic модели для ответа API (можно вынести в schemas/) ---
class NodeSchema(BaseModel):
    id: int
    label: str
    level: int

class EdgeSchema(BaseModel):
    source: int
    target: int

class GraphResponse(BaseModel):
    nodes: List[NodeSchema]
    edges: List[EdgeSchema]

class CourseSchema(BaseModel):
    id: int
    title: str
    description: Optional[str] = None

    class Config:
        from_attributes = True

@app.get("/api/courses", response_model=List[CourseSchema])
def get_courses(db: Session = Depends(get_db)):
    """
    Возвращает список доступных курсов из БД.
    """
    courses = db.query(Course).all()
    return courses

@app.get("/api/knowledge-graph", response_model=GraphResponse)
def get_knowledge_graph(db: Session = Depends(get_db)):
    """
    Возвращает структуру дерева навыков для визуализации из БД.
    """
    nodes = db.query(KnowledgeNode).all()
    edges = db.query(KnowledgeEdge).all()
    
    return GraphResponse(
        nodes=[NodeSchema(id=n.id, label=n.label, level=n.level) for n in nodes],
        edges=[EdgeSchema(source=e.source_id, target=e.target_id) for e in edges]
    )

class ExplanationResponse(BaseModel):
    explanation: str

@app.get("/api/explain/{topic}", response_model=ExplanationResponse)
async def explain_topic(topic: str):
    """
    Генерирует короткое объяснение темы с помощью ИИ.
    """
    try:
        # Проверяем наличие ключа API (в реальном проекте это должно быть в .env)
        # Для локального запуска можно задать: export GEMINI_API_KEY="ваш_ключ"
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
             # Возвращаем заглушку, если ключа нет, чтобы фронтенд не ломался при тесте
            return ExplanationResponse(explanation=f"Демо-режим (нет API ключа): {topic} — это важная концепция в программировании. Изучите её подробнее в уроках.")

        response = completion(
            model="gemini/gemini-3-pro-preview", 
            messages=[
                {"role": "system", "content": "Ты — опытный и дружелюбный репетитор по программированию. Объясни тему кратко (2-3 предложения), просто и понятно для новичка."},
                {"role": "user", "content": f"Объясни тему: {topic}"}
            ],
            api_key=api_key
        )
        # litellm возвращает структуру, похожую на OpenAI
        content = response.choices[0].message.content
        return ExplanationResponse(explanation=content)
    except Exception as e:
        print(f"LLM Error: {e}")
        raise HTTPException(status_code=500, detail=f"Ошибка генерации: {str(e)}")
