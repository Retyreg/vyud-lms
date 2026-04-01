import json
import re
import os
import time
import httpx
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Depends, HTTPException, UploadFile, File, Form
from app.auth.dependencies import get_telegram_user
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List
from dotenv import load_dotenv
from litellm import completion

_start_time = time.time()

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

    # Fallback to Gemini via LiteLLM
    try:
        response = completion(model="gemini/gemini-2.0-flash", messages=messages)
        return response.choices[0].message.content
    except Exception as e:
        logger.error(f"Gemini fallback failed: {str(e)}")

    raise RuntimeError("All AI providers unavailable")

# Импорты БД
from app.db.base import Base, engine, SessionLocal
from app.models.course import Course
from app.models.knowledge import KnowledgeNode, KnowledgeEdge, NodeExplanation, NodeSRProgress
from app.services.sm2 import calculate_next_interval, get_mastery_level, is_due, next_review_date
from app.models.org import Organization, OrgMember
from app.models.document import DocumentChunk
from app.services.pdf import extract_text_from_pdf, chunk_text, embed_chunks, build_graph_from_pdf

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
        raise HTTPException(status_code=503, detail="Database is not configured on this server.")
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

class OrgCreateRequest(BaseModel):
    name: str
    manager_key: str  # email или любой идентификатор менеджера

class OrgJoinRequest(BaseModel):
    user_key: str     # идентификатор сотрудника

class MemberProgress(BaseModel):
    user_key: str
    completed_count: int
    total_count: int
    percent: float

class ReviewRequest(BaseModel):
    user_key: str
    quality: int  # 0-3 from 4-button UI (mapped to SM-2 q: 0→0, 1→2, 2→4, 3→5)

# Maps 4-button UI rating (0-3) to SM-2 quality (0-5)
_QUALITY_MAP = {0: 0, 1: 2, 2: 4, 3: 5}

@app.get("/")
def read_root():
    return {"status": "ok", "message": "Backend is running!"}

@app.get("/api/health")
def health_check():
    """Возвращает статус всех компонентов системы."""
    db_status = "not_configured"
    db_error: str | None = None

    if engine is not None:
        try:
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            db_status = "connected"
        except Exception as exc:
            db_status = "error"
            # Log the full error server-side but return only a generic message
            # to avoid leaking connection strings or internal paths.
            logger.error(f"Health check DB error: {exc}")
            db_error = "Database connection failed"
    
    uptime_seconds = int(time.time() - _start_time)

    groq_configured = bool(os.getenv("GROQ_API_KEY"))
    gemini_configured = bool(os.getenv("GEMINI_API_KEY"))
    ai_configured = groq_configured or gemini_configured

    overall = "ok" if (db_status == "connected" and ai_configured) else "degraded"

    return {
        "status": overall,
        "uptime_seconds": uptime_seconds,
        "database": db_status,
        "database_error": db_error,
        "ai_groq": "configured" if groq_configured else "not_configured",
        "ai_gemini": "configured" if gemini_configured else "not_configured",
    }


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
async def generate_course_smart(
    request: CourseGenerationRequest,
    db: Session = Depends(get_db),
    _tg_user: dict = Depends(get_telegram_user),
):
    topic = request.topic
    prompt = (
        f"Создай дорожную карту обучения теме '{topic}'. "
        f"Верни JSON-массив из 5–7 объектов, где каждый объект: "
        f'[{{"title": "...", "description": "...", "list_of_prerequisite_titles": []}}]'
    )

    try:
        # json_mode=False — не навязываем формат «JSON-object», чтобы модель
        # могла вернуть JSON-массив напрямую.
        ai_content = await call_ai(prompt, "Ты эксперт. Ответ — только валидный JSON без комментариев.", json_mode=False)

        # Извлекаем JSON из возможной markdown-обёртки
        if "```json" in ai_content:
            ai_content = ai_content.split("```json")[1].split("```")[0]
        elif "```" in ai_content:
            ai_content = ai_content.split("```")[1].split("```")[0]
        else:
            # Пытаемся найти первый JSON-массив или объект в тексте
            m = re.search(r"(\[[\s\S]*\]|\{[\s\S]*\})", ai_content)
            if m:
                ai_content = m.group(1)

        parsed = json.loads(ai_content.strip())

        # Модель могла вернуть объект вида {"courses": [...]} или {"nodes": [...]}
        # вместо прямого массива — нормализуем:
        if isinstance(parsed, dict):
            nodes_data = next(
                (v for v in parsed.values() if isinstance(v, list)),
                None,
            )
            if nodes_data is None:
                raise ValueError(f"AI вернул объект без списка: {list(parsed.keys())}")
        else:
            nodes_data = parsed
        
        # Validate each item has the required 'title' key
        if not nodes_data or not all(isinstance(n, dict) and "title" in n for n in nodes_data):
            raise ValueError(
                "AI вернул некорректные данные: каждый элемент должен быть объектом с полем 'title'"
            )

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

    except RuntimeError as e:
        db.rollback()
        raise HTTPException(status_code=503, detail="AI providers unavailable. Try again later.")
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/explain/{node_id}")
async def explain_node(node_id: int, regenerate: bool = False, db: Session = Depends(get_db)):
    # 1. Найти узел по id
    node = db.query(KnowledgeNode).filter(KnowledgeNode.id == node_id).first()
    if not node:
        raise HTTPException(status_code=404, detail="Node not found")

    # 2. Проверить кэш (если не regenerate)
    if not regenerate:
        cached = db.query(NodeExplanation)\
            .filter(NodeExplanation.node_id == node_id)\
            .order_by(NodeExplanation.created_at.desc())\
            .first()
        if cached:
            return {"explanation": cached.explanation, "cached": True}

    # 3. Сформировать промпт
    description_part = f"\nКонтекст: {node.description}" if node.description else ""
    prompt = f"Объясни концепт '{node.label}' простым языком для новичка.{description_part}"
    system = (
        "Ты AI-тьютор платформы VYUD. Правила: "
        "начни с ключевой идеи (1-2 предложения), "
        "приведи конкретный пример из жизни, "
        "объясни почему это важно знать. "
        "Максимум 120 слов. "
        "Не используй слова 'данный', 'следует отметить'. "
        "Отвечай сразу — без вводных фраз типа 'Конечно!' или 'Отличный вопрос!'."
    )

    # 4. Вызвать AI
    try:
        explanation = await call_ai(prompt, system, json_mode=False)
    except RuntimeError:
        raise HTTPException(status_code=503, detail="AI providers unavailable. Try again later.")

    # 5. Сохранить в кэш (upsert)
    existing = db.query(NodeExplanation)\
        .filter(NodeExplanation.node_id == node_id).first()
    if existing:
        existing.explanation = explanation
    else:
        db.add(NodeExplanation(node_id=node_id, explanation=explanation))
    db.commit()

    return {"explanation": explanation, "cached": False}

@app.post("/api/nodes/{node_id}/complete")
def mark_node_complete(node_id: int, db: Session = Depends(get_db)):
    node = db.query(KnowledgeNode).filter(KnowledgeNode.id == node_id).first()
    if not node:
        raise HTTPException(status_code=404, detail="Node not found")
    node.is_completed = True
    db.commit()
    return {"status": "ok", "node_id": node_id}


# --- Org endpoints ---

@app.post("/api/orgs")
def create_org(request: OrgCreateRequest, db: Session = Depends(get_db)):
    """Менеджер создаёт организацию и получает инвайт-ссылку."""
    org = Organization(name=request.name)
    db.add(org)
    db.flush()
    db.add(OrgMember(org_id=org.id, user_key=request.manager_key, is_manager=True))
    db.commit()
    db.refresh(org)
    return {
        "org_id": org.id,
        "org_name": org.name,
        "invite_code": org.invite_code,
        "invite_url": f"?invite={org.invite_code}",
    }


@app.post("/api/orgs/join")
def join_org(invite_code: str, request: OrgJoinRequest, db: Session = Depends(get_db)):
    """Сотрудник вступает в организацию по инвайт-коду."""
    org = db.query(Organization).filter(Organization.invite_code == invite_code).first()
    if not org:
        raise HTTPException(status_code=404, detail="Invite code not found")
    existing = db.query(OrgMember).filter(
        OrgMember.org_id == org.id,
        OrgMember.user_key == request.user_key
    ).first()
    if existing:
        return {"org_id": org.id, "org_name": org.name, "already_member": True}
    db.add(OrgMember(org_id=org.id, user_key=request.user_key, is_manager=False))
    db.commit()
    return {"org_id": org.id, "org_name": org.name, "already_member": False}


@app.get("/api/orgs/{org_id}/courses/latest", response_model=GraphResponse)
def get_org_latest_course(org_id: int, db: Session = Depends(get_db)):
    """Граф последнего курса организации."""
    org = db.query(Organization).filter(Organization.id == org_id).first()
    if not org:
        raise HTTPException(status_code=404, detail="Org not found")
    course = db.query(Course).filter(
        Course.org_id == org_id
    ).order_by(Course.id.desc()).first()
    # Обратная совместимость: если у org нет своего курса — показать глобальный
    if not course:
        course = db.query(Course).filter(
            Course.org_id == None  # noqa: E711
        ).order_by(Course.id.desc()).first()
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
        "edges": [{"source": e.source_id, "target": e.target_id} for e in edges],
    }


@app.get("/api/orgs/{org_id}/progress")
def get_org_progress(org_id: int, db: Session = Depends(get_db)):
    """Дашборд менеджера: прогресс каждого участника команды."""
    org = db.query(Organization).filter(Organization.id == org_id).first()
    if not org:
        raise HTTPException(status_code=404, detail="Org not found")
    members = db.query(OrgMember).filter(OrgMember.org_id == org_id).all()
    course = db.query(Course).filter(
        Course.org_id == org_id
    ).order_by(Course.id.desc()).first()
    if not course:
        course = db.query(Course).filter(
            Course.org_id == None  # noqa: E711
        ).order_by(Course.id.desc()).first()
    total = 0
    completed = 0
    if course:
        all_nodes = db.query(KnowledgeNode).filter(KnowledgeNode.course_id == course.id).all()
        total = len(all_nodes)
        completed = sum(1 for n in all_nodes if n.is_completed)
    # Для пилота is_completed глобальный — у всех одинаковый прогресс.
    # Индивидуальный прогресс — задача Фазы 3 после первого платящего клиента.
    result = []
    for m in members:
        pct = round(completed / total * 100, 1) if total > 0 else 0.0
        result.append(MemberProgress(
            user_key=m.user_key,
            completed_count=completed,
            total_count=total,
            percent=pct,
        ))
    return {
        "org_name": org.name,
        "invite_code": org.invite_code,
        "members": result,
    }


@app.post("/api/orgs/{org_id}/courses/generate")
async def generate_org_course(
    org_id: int,
    request: CourseGenerationRequest,
    db: Session = Depends(get_db),
):
    """Генерация курса привязанного к организации."""
    org = db.query(Organization).filter(Organization.id == org_id).first()
    if not org:
        raise HTTPException(status_code=404, detail="Org not found")

    topic = request.topic
    prompt = (
        f"Создай дорожную карту обучения теме '{topic}'. "
        f"Верни JSON-массив из 5–7 объектов, где каждый объект: "
        f'[{{"title": "...", "description": "...", "list_of_prerequisite_titles": []}}]'
    )
    try:
        ai_content = await call_ai(prompt, "Ты эксперт. Ответ — только валидный JSON без комментариев.", json_mode=False)

        if "```json" in ai_content:
            ai_content = ai_content.split("```json")[1].split("```")[0]
        elif "```" in ai_content:
            ai_content = ai_content.split("```")[1].split("```")[0]
        else:
            m = re.search(r"(\[[\s\S]*\]|\{[\s\S]*\})", ai_content)
            if m:
                ai_content = m.group(1)

        parsed = json.loads(ai_content.strip())
        if isinstance(parsed, dict):
            nodes_data = next((v for v in parsed.values() if isinstance(v, list)), None)
            if nodes_data is None:
                raise ValueError(f"AI вернул объект без списка: {list(parsed.keys())}")
        else:
            nodes_data = parsed

        if not nodes_data or not all(isinstance(n, dict) and "title" in n for n in nodes_data):
            raise ValueError("AI вернул некорректные данные")

        new_course = Course(title=topic, description=f"Курс: {topic}", org_id=org_id)
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
                prerequisites=[],
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

    except RuntimeError:
        db.rollback()
        raise HTTPException(status_code=503, detail="AI providers unavailable. Try again later.")
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


# --- SM-2 Spaced Repetition endpoints ---

@app.post("/api/nodes/{node_id}/review")
def review_node(node_id: int, request: ReviewRequest, db: Session = Depends(get_db)):
    """Submit a recall quality rating (0-3) for a node. Updates SM-2 state."""
    node = db.query(KnowledgeNode).filter(KnowledgeNode.id == node_id).first()
    if not node:
        raise HTTPException(status_code=404, detail="Node not found")

    if request.quality not in _QUALITY_MAP:
        raise HTTPException(status_code=422, detail="quality must be 0-3")

    q = _QUALITY_MAP[request.quality]

    sr = db.query(NodeSRProgress).filter(
        NodeSRProgress.node_id == node_id,
        NodeSRProgress.user_key == request.user_key,
    ).first()

    if sr is None:
        sr = NodeSRProgress(
            node_id=node_id,
            user_key=request.user_key,
            easiness_factor=2.5,
            interval=0,
            repetitions=0,
            total_reviews=0,
            correct_reviews=0,
        )
        db.add(sr)

    new_interval, new_reps, new_ef = calculate_next_interval(
        q=q,
        repetitions=sr.repetitions,
        interval=sr.interval,
        easiness_factor=sr.easiness_factor,
    )

    sr.interval = new_interval
    sr.repetitions = new_reps
    sr.easiness_factor = new_ef
    sr.next_review = next_review_date(new_interval)
    sr.last_reviewed = next_review_date(0)  # now
    sr.total_reviews += 1
    if q >= 3:
        sr.correct_reviews += 1
        node.is_completed = True

    db.commit()

    return {
        "node_id": node_id,
        "next_review_days": new_interval,
        "mastery": get_mastery_level(sr.repetitions, sr.correct_reviews, sr.total_reviews),
    }


@app.get("/api/nodes/{node_id}/sr-status")
def get_sr_status(node_id: int, user_key: str, db: Session = Depends(get_db)):
    """Return current SM-2 state for a user+node pair."""
    node = db.query(KnowledgeNode).filter(KnowledgeNode.id == node_id).first()
    if not node:
        raise HTTPException(status_code=404, detail="Node not found")

    sr = db.query(NodeSRProgress).filter(
        NodeSRProgress.node_id == node_id,
        NodeSRProgress.user_key == user_key,
    ).first()

    if sr is None:
        return {
            "node_id": node_id,
            "is_due": True,
            "interval": 0,
            "repetitions": 0,
            "easiness_factor": 2.5,
            "mastery": "новый",
            "next_review": None,
        }

    return {
        "node_id": node_id,
        "is_due": is_due(sr.next_review),
        "interval": sr.interval,
        "repetitions": sr.repetitions,
        "easiness_factor": sr.easiness_factor,
        "mastery": get_mastery_level(sr.repetitions, sr.correct_reviews, sr.total_reviews),
        "next_review": sr.next_review.isoformat() if sr.next_review else None,
    }


@app.get("/api/orgs/{org_id}/due-nodes")
def get_due_nodes(org_id: int, user_key: str, db: Session = Depends(get_db)):
    """Return IDs of nodes that are due for review today for this user."""
    org = db.query(Organization).filter(Organization.id == org_id).first()
    if not org:
        raise HTTPException(status_code=404, detail="Org not found")

    course = db.query(Course).filter(
        Course.org_id == org_id
    ).order_by(Course.id.desc()).first()
    if not course:
        course = db.query(Course).filter(
            Course.org_id == None  # noqa: E711
        ).order_by(Course.id.desc()).first()
    if not course:
        return {"due_node_ids": []}

    nodes = db.query(KnowledgeNode).filter(KnowledgeNode.course_id == course.id).all()
    node_ids = [n.id for n in nodes]

    sr_records = db.query(NodeSRProgress).filter(
        NodeSRProgress.node_id.in_(node_ids),
        NodeSRProgress.user_key == user_key,
    ).all()

    reviewed_ids = {r.node_id for r in sr_records if not is_due(r.next_review)}
    due_ids = [nid for nid in node_ids if nid not in reviewed_ids]

    return {"due_node_ids": due_ids}


@app.post("/api/orgs/{org_id}/courses/upload-pdf")
async def upload_pdf(
    org_id: int,
    file: UploadFile = File(...),
    topic: str = Form(default=""),
    db: Session = Depends(get_db),
):
    """Генерация графа знаний из загруженного PDF-файла."""
    org = db.query(Organization).filter(Organization.id == org_id).first()
    if not org:
        raise HTTPException(status_code=404, detail="Org not found")

    file_bytes = await file.read()

    try:
        pdf_text = extract_text_from_pdf(file_bytes)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to parse PDF: {e}")

    if not pdf_text.strip():
        raise HTTPException(status_code=400, detail="PDF is empty or contains no extractable text")

    if not topic:
        topic = pdf_text[:100].strip()

    chunks = chunk_text(pdf_text)

    try:
        embeddings = await embed_chunks(chunks)
    except Exception as e:
        logger.error(f"Embedding failed: {e}")
        embeddings = [None] * len(chunks)

    try:
        nodes_data = await build_graph_from_pdf(chunks, topic, call_ai)
    except RuntimeError:
        raise HTTPException(status_code=503, detail="AI providers unavailable. Try again later.")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    try:
        new_course = Course(title=topic, description=f"Курс: {topic}", org_id=org_id)
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
                prerequisites=[],
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

        for idx, (chunk, embedding) in enumerate(zip(chunks, embeddings)):
            db.add(DocumentChunk(
                course_id=new_course.id,
                chunk_text=chunk,
                chunk_index=idx,
                embedding=embedding,
            ))

        db.commit()
        return {"status": "ok", "course_id": new_course.id, "node_count": len(created_nodes)}

    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))
