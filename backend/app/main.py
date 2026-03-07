from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
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
    is_completed: bool

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
        nodes=[NodeSchema(id=n.id, label=n.label, level=n.level, is_completed=n.is_completed) for n in nodes],
        edges=[EdgeSchema(source=e.source_id, target=e.target_id) for e in edges]
    )

@app.post("/api/complete/{node_id}")
def complete_node(node_id: int, db: Session = Depends(get_db)):
    """
    Отмечает узел как изученный.
    """
    node = db.query(KnowledgeNode).filter(KnowledgeNode.id == node_id).first()
    if not node:
        raise HTTPException(status_code=404, detail="Node not found")
    
    node.is_completed = True
    db.commit()
    return {"status": "ok", "message": f"Node {node.label} marked as completed"}

class ExplanationResponse(BaseModel):
    explanation: str

class QuizQuestion(BaseModel):
    question: str
    options: List[str]
    answer: str

class QuizResponse(BaseModel):
    questions: List[QuizQuestion]

@app.get("/api/explain/{topic}", response_model=ExplanationResponse)
async def explain_topic(topic: str):
    """
    Генерирует короткое объяснение темы с помощью ИИ.
    """
    try:
        # Проверяем наличие ключа API
        if not os.getenv("GEMINI_API_KEY"):
            return ExplanationResponse(explanation="Ключ API не найден в системе")

        response = completion(
            model="gemini/gemini-1.5-flash", 
            messages=[
                {"role": "system", "content": "Ты — опытный и дружелюбный репетитор по программированию. Объясни тему кратко (2-3 предложения), просто и понятно для новичка."},
                {"role": "user", "content": f"Объясни тему: {topic}"}
            ],
            api_key=os.getenv("GEMINI_API_KEY")
        )
        # litellm возвращает структуру, похожую на OpenAI
        content = response.choices[0].message.content
        return ExplanationResponse(explanation=content)
    except Exception as e:
        print(f"LLM Error: {e}")
        # Возвращаем заглушку вместо ошибки, чтобы пользователь не расстраивался
        return ExplanationResponse(explanation=f"ИИ временно недоступен, но тема {topic} очень важна для вашего развития! Попробуйте позже.")

import json

@app.get("/api/quiz/{topic}", response_model=QuizResponse)
async def get_quiz(topic: str):
    """
    Генерирует 3 вопроса с вариантами ответов по теме.
    """
    try:
        if not os.getenv("GEMINI_API_KEY"):
            # Возвращаем мок-данные, если нет ключа
            return QuizResponse(questions=[
                QuizQuestion(
                    question=f"Что такое {topic}?", 
                    options=["Еда", "Концепция программирования", "Вид спорта", "Планета"], 
                    answer="Концепция программирования"
                )
            ])

        prompt = f"""
        Сгенерируй тест по теме "{topic}".
        Нужно ровно 3 вопроса.
        У каждого вопроса должно быть 4 варианта ответа.
        Верни ТОЛЬКО валидный JSON массив объектов без лишнего текста и без markdown-разметки (```json ... ```).
        Формат:
        [
            {{
                "question": "Текст вопроса",
                "options": ["Вариант 1", "Вариант 2", "Вариант 3", "Вариант 4"],
                "answer": "Правильный вариант (должен точно совпадать с одним из options)"
            }}
        ]
        """

        response = completion(
            model="gemini/gemini-1.5-flash", 
            messages=[
                {"role": "system", "content": "Ты — генератор тестов. Ты отвечаешь только строгим JSON."},
                {"role": "user", "content": prompt}
            ],
            api_key=os.getenv("GEMINI_API_KEY")
        )
        
        content = response.choices[0].message.content
        # Очистка от markdown, если модель все-таки его добавила
        content = content.replace("```json", "").replace("```", "").strip()
        
        questions_data = json.loads(content)
        return QuizResponse(questions=questions_data)

    except Exception as e:
        print(f"LLM Error (Quiz): {e}")
        # Возвращаем безопасный фолбек
        return QuizResponse(questions=[
            QuizQuestion(
                question=f"Не удалось сгенерировать тест по теме {topic}. Попробуйте позже.", 
                options=["Ок"], 
                answer="Ок"
            )
        ])
