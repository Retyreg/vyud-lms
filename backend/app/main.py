import json
import os
import httpx
import traceback
import logging
from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List, Optional
from dotenv import load_dotenv
from litellm import completion

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv()

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
if not GROQ_API_KEY:
    logger.error("GROQ_API_KEY environment variable is not set")
    raise RuntimeError("GROQ_API_KEY environment variable is not set")

async def call_ai(prompt: str, system: str, json_mode: bool = True) -> str:
    """ Улучшенная функция вызова ИИ с расширенными таймаутами """
    messages = [
        {"role": "system", "content": system},
        {"role": "user", "content": prompt}
    ]
    
    # Попытка 1: Groq
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
                timeout=60.0 # Увеличен таймаут
            )
            
            if response.status_code == 200:
                return response.json()['choices'][0]['message']['content']
            else:
                logger.warning(f"Groq API error {response.status_code}: {response.text}")
    except Exception as e:
        logger.error(f"Groq failed: {str(e)}")

    # Попытка 2: Gemini Fallback
    try:
        response = completion(
            model="gemini/gemini-1.5-flash", 
            messages=messages,
            api_version="v1"
        )
        return response.choices[0].message.content
    except Exception as e:
        logger.error(f"Gemini failed: {str(e)}")
        raise HTTPException(status_code=503, detail="ИИ временно недоступен. Попробуйте через минуту.")

from app.db.base import Base, engine, SessionLocal
import app.models 
from app.models.course import Course
from app.models.knowledge import KnowledgeNode, KnowledgeEdge

# Создаем таблицы
Base.metadata.create_all(bind=engine)

app = FastAPI(title="VYUD LMS API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Схемы данных
class NodeSchema(BaseModel):
    id: int
    label: str
    level: int
    is_completed: bool
    is_available: bool
    prerequisites: List[int] = []

class EdgeSchema(BaseModel):
    source: int
    target: int

class GraphResponse(BaseModel):
    nodes: List[NodeSchema]
    edges: List[EdgeSchema]

class CourseGenerationRequest(BaseModel):
    topic: str

@app.get("/api/courses/latest", response_model=GraphResponse)
def get_latest_course(db: Session = Depends(get_db)):
    """ Возвращает последний курс или пустой граф, если курсов нет """
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
            is_completed=n.is_completed, is_available=is_available,
            prerequisites=prereqs
        ))

    return {
        "nodes": node_schemas,
        "edges": [{"source": e.source_id, "target": e.target_id} for e in edges]
    }

@app.post("/api/courses/generate")
async def generate_course_smart(request: CourseGenerationRequest, db: Session = Depends(get_db)):
    """ Умная генерация курса с сохранением в БД """
    topic = request.topic
    
    prompt = f"Создай структуру курса по теме '{topic}'. 10 тем в JSON: [{{'title': '...', 'description': '...', 'list_of_prerequisite_titles': []}}]"

    try:
        ai_content = await call_ai(prompt, "Ты — методист. Отвечай только JSON.")
        
        # Очистка от markdown
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
        logger.error(f"Generation error: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/explain/{topic}")
async def explain_topic(topic: str):
    content = await call_ai(f"Объясни кратко: {topic}", "Ты репетитор.", json_mode=False)
    return {"explanation": content}

@app.get("/api/quiz/{topic}")
async def get_quiz(topic: str):
    prompt = f"Создай 3 вопроса по теме {topic} в формате JSON: {{'questions': [{{'question': '...', 'options': [], 'correct_answer': 0}}]}}"
    content = await call_ai(prompt, "Ты эксперт.")
    return json.loads(content)
