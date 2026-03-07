from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List, Optional
import os
from dotenv import load_dotenv
from litellm import completion

load_dotenv()

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
    is_available: bool
    prerequisites: List[int]

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
    
    # Создаем словарь статусов для быстрой проверки
    completed_ids = {n.id for n in nodes if n.is_completed}
    
    node_schemas = []
    for n in nodes:
        # Узел доступен, если у него нет пререквизитов ИЛИ все пререквизиты выполнены
        prereqs = n.prerequisites or []
        is_available = all(pid in completed_ids for pid in prereqs)
        
        node_schemas.append(NodeSchema(
            id=n.id, 
            label=n.label, 
            level=n.level, 
            is_completed=n.is_completed,
            is_available=is_available,
            prerequisites=prereqs
        ))

    return GraphResponse(
        nodes=node_schemas,
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

@app.post("/api/nodes/{node_id}/complete")
def complete_node_rest(node_id: int, db: Session = Depends(get_db)):
    """
    Отмечает узел как изученный (REST-style).
    """
    node = db.query(KnowledgeNode).filter(KnowledgeNode.id == node_id).first()
    if not node:
        raise HTTPException(status_code=404, detail="Node not found")
    
    node.is_completed = True
    db.commit()
    return {"status": "ok", "message": f"Node {node.label} marked as completed", "is_completed": True}

@app.post("/api/nodes/{node_id}/toggle-complete")
def toggle_complete_node(node_id: int, db: Session = Depends(get_db)):
    """
    Переключает статус изучения узла (изучено/не изучено).
    """
    node = db.query(KnowledgeNode).filter(KnowledgeNode.id == node_id).first()
    if not node:
        raise HTTPException(status_code=404, detail="Node not found")
    
    # Инвертируем значение
    node.is_completed = not node.is_completed
    db.commit()
    
    status_msg = "completed" if node.is_completed else "uncompleted"
    return {
        "status": "ok", 
        "message": f"Node {node.label} marked as {status_msg}", 
        "is_completed": node.is_completed
    }

class ExplanationResponse(BaseModel):
    explanation: str

class QuizQuestion(BaseModel):
    question: str
    options: List[str]
    answer: str

class QuizResponse(BaseModel):
    questions: List[QuizQuestion]

@app.get("/api/explain/{topic}", response_model=ExplanationResponse)
async def explain_topic(topic: str, model: str = "gemini/gemini-2.0-flash"):
    """
    Генерирует короткое объяснение темы с помощью ИИ.
    """
    # Системный промпт
    messages = [
        {"role": "system", "content": "Ты — опытный и дружелюбный репетитор по программированию. Объясни тему кратко (2-3 предложения), просто и понятно для новичка."},
        {"role": "user", "content": f"Объясни тему: {topic}"}
    ]

    print(f"Использую модель: {model} для объяснения темы: {topic}")

    try:
        # Попытка 1: Запрошенная модель
        # LiteLLM поддерживает huggingface/..., groq/..., anthropic/... автоматически
        # Принудительно ставим v1 для Gemini
        api_ver = "v1" if "gemini" in model else None
        
        response = completion(
            model=model, 
            messages=messages,
            # Ключи берутся из os.environ
            api_version=api_ver
        )
        content = response.choices[0].message.content
        return ExplanationResponse(explanation=content)

    except Exception as e:
        print(f"LLM Error ({model}): {e}")
        
        # Fallback логика
        print("Попытка переключения на запасную модель (Groq Llama)...")
        try:
            fallback_model = "groq/llama-3.1-70b-versatile"
            # LiteLLM возьмет GROQ_API_KEY из env
            
            response = completion(
                model=fallback_model, 
                messages=messages
            )
            content = response.choices[0].message.content
            return ExplanationResponse(explanation=f"⚠️ Основная модель недоступна. Ответ от Llama 3.1 (Groq):\n\n{content}")
        except Exception as e_fallback:
            print(f"Fallback Error: {e_fallback}")

        return ExplanationResponse(explanation=f"ИИ временно недоступен ({model}). Ошибка: {str(e)}")

import json

@app.get("/api/quiz/{topic}", response_model=QuizResponse)
async def get_quiz(topic: str, model: str = "gemini/gemini-2.0-flash"):
    """
    Генерирует 3 вопроса с вариантами ответов по теме.
    """
    try:
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
        
        messages = [
            {"role": "system", "content": "Ты — генератор тестов. Ты отвечаешь только строгим JSON."},
            {"role": "user", "content": prompt}
        ]

        print(f"Генерирую тест моделью: {model}")

        try:
            # Попытка 1
            response = completion(
                model=model, 
                messages=messages, 
                api_version="v1" if "gemini" in model else None
            )
            content = response.choices[0].message.content
        except Exception as e:
            print(f"Quiz Error ({model}): {e}")
            
            # Fallback на Groq
            print("Quiz Fallback -> Groq Llama")
            response = completion(
                model="groq/llama-3.1-70b-versatile", 
                messages=messages
            )
            content = response.choices[0].message.content

        # Очистка от markdown
        content = content.replace("```json", "").replace("```", "").strip()
        
        questions_data = json.loads(content)
        return QuizResponse(questions=questions_data)

    except Exception as e:
        print(f"LLM Error (Quiz Final): {e}")
        return QuizResponse(questions=[
            QuizQuestion(
                question=f"Не удалось сгенерировать тест ({model}).", 
                options=["Ок"], 
                answer="Ок"
            )
        ])
