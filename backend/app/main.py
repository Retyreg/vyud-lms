import json
import os
import httpx
import traceback
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List
from dotenv import load_dotenv
from litellm import completion

# Настройка логирования для отслеживания ошибок
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv()

GROQ_API_KEY = os.getenv("GROQ_API_KEY")

async def call_ai(prompt: str, system: str, json_mode: bool = True) -> str:
    messages = [
        {"role": "system", "content": system},
        {"role": "user", "content": prompt}
    ]
    try:
        payload = {
            "model": "llama-3.3-70b-versatile",
            "messages": messages,
            "temperature": 0.4,
        }
        if json_mode:
            payload["response_format"] = {"type": "json_object"}

        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {GROQ_API_KEY}",
                    "Content-Type": "application/json"
                },
                json=payload,
                timeout=60.0
            )
            if response.status_code == 200:
                return response.json()['choices'][0]['message']['content']
    except Exception as e:
        logger.error(f"Groq failed: {str(e)}")

    # Запасной вариант на случай проблем с Groq
    response = completion(model="gemini/gemini-1.5-flash", messages=messages)
    return response.choices[0].message.content

# Импорты БД
from app.db.base import Base, engine, SessionLocal
from app.models.course import Course
from app.models.knowledge import KnowledgeNode, KnowledgeEdge

# Создаем таблицы при старте (в lifespan, чтобы не крашить приложение при недоступной БД)
@asynccontextmanager
async def lifespan(app: FastAPI):
    if engine is not None:
        try:
            Base.metadata.create_all(bind=engine)
            logger.info("Database tables created/verified successfully")
        except Exception as e:
            logger.error(f"Failed to create database tables: {e}")
    else:
        logger.warning("No database engine available — skipping table creation")
    yield

app = FastAPI(title="VYUD LMS API", lifespan=lifespan)

# Разрешаем запросы с Vercel
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def get_db():
    if SessionLocal is None:
        raise HTTPException(status_code=503, detail="Database service is temporarily unavailable.")
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

class NodeSchema(BaseModel):
    id: int
    label: str
    level: int
    is_completed: bool
    is_available: bool

class EdgeSchema(BaseModel):
    source: int
    target: int

class GraphResponse(BaseModel):
    nodes: List[NodeSchema]
    edges: List[EdgeSchema]

class CourseGenerationRequest(BaseModel):
    topic: str

@app.get("/")
def read_root():
    return {"status": "ok", "message": "Backend is running!"}

# ТОТ САМЫЙ МАРШРУТ, КОТОРОГО НЕ ХВАТАЛО НА VERCEL (ошибка 404)
@app.get("/api/courses/latest", response_model=GraphResponse)
def get_latest_course(db: Session = Depends(get_db)):
    course = db.query(Course).order_by(Course.id.desc()).first()
    if not course:
        return {"nodes": [], "edges": []}
        
    nodes = db.query(KnowledgeNode).filter(KnowledgeNode.course_id == course.id).all()
    if not nodes:
        return {"nodes": [], "edges": []}
        
    node_ids = {n.id for n in nodes}
    edges = db.query(KnowledgeEdge).filter(
        KnowledgeEdge.source_id.in_(node_ids),
        KnowledgeEdge.target_id.in_(node_ids)
    ).all()
    
    completed_ids = {n.id for n in nodes if n.is_completed}
    
    node_schemas = []
    for n in nodes:
        prereqs = n.prerequisites or []
        is_available = all(pid in completed_ids for pid in prereqs)
        node_schemas.append(NodeSchema(
            id=n.id, label=n.label, level=n.level, 
            is_completed=n.is_completed, is_available=is_available
        ))

    return {
        "nodes": node_schemas,
        "edges": [{"source": e.source_id, "target": e.target_id} for e in edges]
    }

@app.post("/api/courses/generate")
async def generate_course_smart(request: CourseGenerationRequest, db: Session = Depends(get_db)):
    topic = request.topic
    prompt = f"Создай дорожную карту обучения теме '{topic}'. Верни JSON массив из 5-7 объектов: [{{'title': '...', 'description': '...', 'list_of_prerequisite_titles': []}}]"

    try:
        ai_content = await call_ai(prompt, "Ты профи. Ответ только JSON.")
        
        if "```json" in ai_content:
            ai_content = ai_content.split("```json")[1].split("```")[0]
        elif "```" in ai_content:
            ai_content = ai_content.split("```")[1].split("```")[0]
        
        nodes_data = json.loads(ai_content.strip())
        
        new_course = Course(title=topic, description=f"Курс: {topic}")
        db.add(new_course)
        db.flush()

        title_to_id = {}
        created_nodes = []

        for node_data in nodes_data:
            new_node = KnowledgeNode(
                label=node_data["title"],
                description=node_data.get("description", ""),
                level=1,
                course_id=new_course.id,
                prerequisites=[]
            )
            db.add(new_node)
            db.flush()
            title_to_id[node_data["title"]] = new_node.id
            created_nodes.append((new_node, node_data.get("list_of_prerequisite_titles", [])))
        
        for node, prereq_titles in created_nodes:
            new_prereq_ids = []
            for p_title in prereq_titles:
                if p_title in title_to_id:
                    p_id = title_to_id[p_title]
                    new_prereq_ids.append(p_id)
                    db.add(KnowledgeEdge(source_id=p_id, target_id=node.id))
            node.prerequisites = new_prereq_ids

        db.commit()
        return {"status": "ok", "message": "Success"}

    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/explain/{topic}")
async def explain_topic(topic: str):
    content = await call_ai(f"Объясни для новичка: {topic}", "Ты репетитор.", json_mode=False)
    return {"explanation": content}
