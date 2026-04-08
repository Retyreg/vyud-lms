import json
import math
import re
import os
import time
import httpx
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Depends, HTTPException, UploadFile, File, Form, Header
from fastapi.responses import StreamingResponse
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
from app.models.streak import UserStreak
from app.services.pdf import extract_text_from_pdf, chunk_text, embed_chunks, build_graph_from_pdf
from app.services.streak import update_streak, get_streak

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

class OrgInfo(BaseModel):
    org_id: int
    org_name: str
    invite_code: str
    is_manager: bool

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

class CompleteRequest(BaseModel):
    user_key: str = ""


async def _stream_explanation(node_id: int, label: str, description: str | None, db: Session):
    """Async generator: streams Groq SSE chunks, saves full text to cache on finish."""
    description_part = f"\nКонтекст: {description}" if description else ""
    prompt = f"Объясни концепт '{label}' простым языком для новичка.{description_part}"
    system = (
        "Ты AI-тьютор платформы VYUD. Правила: "
        "начни с ключевой идеи (1-2 предложения), "
        "приведи конкретный пример из жизни, "
        "объясни почему это важно знать. "
        "Максимум 120 слов. "
        "Не используй слова 'данный', 'следует отметить'. "
        "Отвечай сразу — без вводных фраз типа 'Конечно!' или 'Отличный вопрос!'."
    )
    messages = [
        {"role": "system", "content": system},
        {"role": "user", "content": prompt},
    ]

    full_text_parts: list[str] = []

    try:
        async with httpx.AsyncClient() as client:
            async with client.stream(
                "POST",
                "https://api.groq.com/openai/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {GROQ_API_KEY}",
                    "Content-Type": "application/json",
                },
                json={"model": "llama-3.3-70b-versatile", "messages": messages, "temperature": 0.4, "stream": True},
                timeout=60.0,
            ) as resp:
                async for line in resp.aiter_lines():
                    if not line.startswith("data: "):
                        continue
                    raw = line[6:]
                    if raw == "[DONE]":
                        break
                    try:
                        delta = json.loads(raw)["choices"][0]["delta"].get("content", "")
                    except (KeyError, json.JSONDecodeError):
                        continue
                    if delta:
                        full_text_parts.append(delta)
                        yield f"data: {json.dumps({'text': delta})}\n\n"
    except Exception as e:
        logger.error("Groq streaming failed: %s", e)
        # Fallback: non-streaming Gemini
        try:
            from litellm import acompletion as _acompletion
            fallback = await _acompletion(model="gemini/gemini-2.0-flash", messages=messages, temperature=0.4)
            text = fallback.choices[0].message.content
            full_text_parts.append(text)
            yield f"data: {json.dumps({'text': text})}\n\n"
        except Exception as e2:
            logger.error("Gemini fallback failed: %s", e2)
            yield f"data: {json.dumps({'error': 'AI providers unavailable'})}\n\n"
            return

    # Save full explanation to cache
    full_text = "".join(full_text_parts)
    if full_text:
        existing = db.query(NodeExplanation).filter(NodeExplanation.node_id == node_id).first()
        if existing:
            existing.explanation = full_text
        else:
            db.add(NodeExplanation(node_id=node_id, explanation=full_text))
        db.commit()

    yield f"data: {json.dumps({'done': True})}\n\n"


@app.get("/api/explain-stream/{node_id}")
async def explain_node_stream(node_id: int, regenerate: bool = False, db: Session = Depends(get_db)):
    node = db.query(KnowledgeNode).filter(KnowledgeNode.id == node_id).first()
    if not node:
        raise HTTPException(status_code=404, detail="Node not found")

    if not regenerate:
        cached = (
            db.query(NodeExplanation)
            .filter(NodeExplanation.node_id == node_id)
            .order_by(NodeExplanation.created_at.desc())
            .first()
        )
        if cached:
            async def _cached():
                yield f"data: {json.dumps({'text': cached.explanation, 'cached': True})}\n\n"
                yield f"data: {json.dumps({'done': True})}\n\n"
            return StreamingResponse(_cached(), media_type="text/event-stream",
                                     headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})

    return StreamingResponse(
        _stream_explanation(node_id, node.label, node.description, db),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@app.post("/api/nodes/{node_id}/complete")
def mark_node_complete(node_id: int, request: CompleteRequest = CompleteRequest(), db: Session = Depends(get_db)):
    node = db.query(KnowledgeNode).filter(KnowledgeNode.id == node_id).first()
    if not node:
        raise HTTPException(status_code=404, detail="Node not found")
    node.is_completed = True
    db.commit()
    if request.user_key:
        update_streak(request.user_key, db)
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


def _require_manager(org_id: int, user_key: str, db: Session) -> OrgMember:
    """Raise 403 if user_key is not a manager of org_id."""
    member = db.query(OrgMember).filter(
        OrgMember.org_id == org_id,
        OrgMember.user_key == user_key,
        OrgMember.is_manager == True,  # noqa: E712
    ).first()
    if not member:
        raise HTTPException(status_code=403, detail="Manager access required")
    return member


@app.get("/api/users/{user_key}/orgs", response_model=List[OrgInfo])
def get_user_orgs(user_key: str, db: Session = Depends(get_db)):
    """Список организаций, в которых состоит пользователь."""
    memberships = db.query(OrgMember).filter(OrgMember.user_key == user_key).all()
    result = []
    for m in memberships:
        org = db.query(Organization).filter(Organization.id == m.org_id).first()
        if org:
            result.append(OrgInfo(
                org_id=org.id,
                org_name=org.name,
                invite_code=org.invite_code,
                is_manager=m.is_manager,
            ))
    return result


@app.get("/api/orgs/{org_id}", response_model=OrgInfo)
def get_org(org_id: int, user_key: str, db: Session = Depends(get_db)):
    """Информация об организации. Доступна только участникам."""
    org = db.query(Organization).filter(Organization.id == org_id).first()
    if not org:
        raise HTTPException(status_code=404, detail="Org not found")
    member = db.query(OrgMember).filter(
        OrgMember.org_id == org_id,
        OrgMember.user_key == user_key,
    ).first()
    if not member:
        raise HTTPException(status_code=403, detail="Not a member of this org")
    return OrgInfo(
        org_id=org.id,
        org_name=org.name,
        invite_code=org.invite_code,
        is_manager=member.is_manager,
    )


@app.delete("/api/orgs/{org_id}/members/{member_key}", status_code=200)
def remove_org_member(org_id: int, member_key: str, user_key: str, db: Session = Depends(get_db)):
    """Менеджер удаляет участника из организации."""
    _require_manager(org_id, user_key, db)
    if member_key == user_key:
        raise HTTPException(status_code=400, detail="Cannot remove yourself")
    member = db.query(OrgMember).filter(
        OrgMember.org_id == org_id,
        OrgMember.user_key == member_key,
    ).first()
    if not member:
        raise HTTPException(status_code=404, detail="Member not found")
    db.delete(member)
    db.commit()
    return {"removed": member_key}


@app.post("/api/orgs/{org_id}/invite/regenerate")
def regenerate_invite(org_id: int, user_key: str, db: Session = Depends(get_db)):
    """Менеджер сбрасывает инвайт-код (старый перестаёт работать)."""
    import secrets as _secrets
    _require_manager(org_id, user_key, db)
    org = db.query(Organization).filter(Organization.id == org_id).first()
    if not org:
        raise HTTPException(status_code=404, detail="Org not found")
    org.invite_code = _secrets.token_urlsafe(8)
    db.commit()
    return {"invite_code": org.invite_code, "invite_url": f"?invite={org.invite_code}"}


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
def get_org_progress(org_id: int, user_key: str, db: Session = Depends(get_db)):
    """Дашборд менеджера: прогресс каждого участника команды."""
    org = db.query(Organization).filter(Organization.id == org_id).first()
    if not org:
        raise HTTPException(status_code=404, detail="Org not found")
    _require_manager(org_id, user_key, db)
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
    user_key: str,
    db: Session = Depends(get_db),
):
    """Генерация курса привязанного к организации."""
    org = db.query(Organization).filter(Organization.id == org_id).first()
    if not org:
        raise HTTPException(status_code=404, detail="Org not found")
    _require_manager(org_id, user_key, db)

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
    update_streak(request.user_key, db)

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


def _compute_badge(current_streak: int) -> str | None:
    if current_streak >= 30:
        return "🔥 Легенда"
    if current_streak >= 14:
        return "⚡ Эксперт"
    if current_streak >= 7:
        return "🌟 Мастер"
    if current_streak >= 3:
        return "💪 В ударе"
    if current_streak >= 1:
        return "🌱 Новичок"
    return None


@app.get("/api/streaks/{user_key}")
def get_user_streak(user_key: str, db: Session = Depends(get_db)):
    """Return streak info and badge for a user."""
    streak = get_streak(user_key, db)
    if streak is None:
        return {
            "current_streak": 0,
            "longest_streak": 0,
            "total_days_active": 0,
            "last_activity_date": None,
            "badge": None,
        }
    return {
        "current_streak": streak.current_streak,
        "longest_streak": streak.longest_streak,
        "total_days_active": streak.total_days_active,
        "last_activity_date": streak.last_activity_date.isoformat() if streak.last_activity_date else None,
        "badge": _compute_badge(streak.current_streak),
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


class ROIResponse(BaseModel):
    org_name: str
    total_members: int
    active_members: int
    total_nodes: int
    avg_completion_rate: float
    avg_days_to_first_completion: float | None
    fastest_member: str | None
    total_reviews: int
    avg_streak: float
    onboarding_efficiency_score: float
    summary: str


@app.get("/api/orgs/{org_id}/roi", response_model=ROIResponse)
def get_org_roi(org_id: int, db: Session = Depends(get_db)):
    """ROI-метрики организации для менеджера/CXO."""
    org = db.query(Organization).filter(Organization.id == org_id).first()
    if not org:
        raise HTTPException(status_code=404, detail="Org not found")

    members = db.query(OrgMember).filter(OrgMember.org_id == org_id).all()
    total_members = len(members)
    member_keys = [m.user_key for m in members]
    member_joined = {m.user_key: m.joined_at for m in members}

    # Последний курс организации
    course = db.query(Course).filter(
        Course.org_id == org_id
    ).order_by(Course.id.desc()).first()
    if not course:
        course = db.query(Course).filter(
            Course.org_id == None  # noqa: E711
        ).order_by(Course.id.desc()).first()

    total_nodes = 0
    node_ids: list[int] = []
    if course:
        nodes = db.query(KnowledgeNode).filter(KnowledgeNode.course_id == course.id).all()
        total_nodes = len(nodes)
        node_ids = [n.id for n in nodes]

    # SR-прогресс всех участников по узлам курса
    sr_records = []
    if member_keys and node_ids:
        sr_records = db.query(NodeSRProgress).filter(
            NodeSRProgress.user_key.in_(member_keys),
            NodeSRProgress.node_id.in_(node_ids),
        ).all()

    # active_members: хоть раз делали review
    active_keys = {r.user_key for r in sr_records}
    active_members = len(active_keys)

    # avg_completion_rate: среднее % охваченных узлов по всем участникам
    from collections import defaultdict
    reviewed_per_user: dict[str, set[int]] = defaultdict(set)
    for r in sr_records:
        reviewed_per_user[r.user_key].add(r.node_id)

    if total_nodes > 0 and member_keys:
        rates = [len(reviewed_per_user[k]) / total_nodes * 100 for k in member_keys]
        avg_completion_rate = round(sum(rates) / len(rates), 1)
    else:
        avg_completion_rate = 0.0

    # total_reviews
    total_reviews = sum(r.total_reviews for r in sr_records)

    # avg_days_to_first_completion
    days_list: list[float] = []
    for key in member_keys:
        user_sr = [r for r in sr_records if r.user_key == key and r.last_reviewed is not None]
        if user_sr:
            first_review = min(r.last_reviewed for r in user_sr)  # type: ignore[type-var]
            joined = member_joined.get(key)
            if joined and first_review:
                delta = (first_review - joined).total_seconds() / 86400
                if delta >= 0:
                    days_list.append(delta)
    avg_days_to_first_completion = round(sum(days_list) / len(days_list), 1) if days_list else None

    # fastest_member: участник с наибольшим количеством просмотренных узлов
    fastest_member: str | None = None
    if reviewed_per_user:
        fastest_member = max(reviewed_per_user, key=lambda k: len(reviewed_per_user[k]))

    # avg_streak
    streaks = (
        db.query(UserStreak).filter(UserStreak.user_key.in_(member_keys)).all()
        if member_keys else []
    )
    streak_map = {s.user_key: s.current_streak for s in streaks}
    avg_streak = (
        round(sum(streak_map.get(k, 0) for k in member_keys) / len(member_keys), 1)
        if member_keys else 0.0
    )

    # onboarding_efficiency_score: 0-100
    raw_score = avg_completion_rate * (1 + math.log(total_reviews + 1) / 10)
    onboarding_efficiency_score = round(min(100.0, max(0.0, raw_score)), 1)

    # summary (статический, без AI)
    completion_int = round(avg_completion_rate)
    if avg_completion_rate >= 80:
        summary = f"Команда освоила курс на {completion_int}%. Онбординг прошёл успешно."
    elif avg_completion_rate >= 50:
        summary = (
            f"Команда на полпути — {completion_int}% завершено. "
            f"{active_members} из {total_members} участников активны."
        )
    else:
        summary = f"Онбординг в процессе. {active_members} из {total_members} участников начали обучение."

    return ROIResponse(
        org_name=org.name,
        total_members=total_members,
        active_members=active_members,
        total_nodes=total_nodes,
        avg_completion_rate=avg_completion_rate,
        avg_days_to_first_completion=avg_days_to_first_completion,
        fastest_member=fastest_member,
        total_reviews=total_reviews,
        avg_streak=avg_streak,
        onboarding_efficiency_score=onboarding_efficiency_score,
        summary=summary,
    )


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


@app.post("/api/generate-file")
async def generate_file_quiz(
    file: UploadFile = File(...),
    num_questions: str = Form("10"),
    difficulty: str = Form("medium"),
    language: str = Form("Russian"),
    email: str = Form(...),
    telegram_id: str = Form(None),
    username: str = Form(None),
    x_api_key: str = Header(None, alias="x-api-key"),
):
    import uuid as uuid_lib

    expected_key = os.getenv("API_KEY")
    if expected_key and x_api_key != expected_key:
        raise HTTPException(status_code=401, detail="Invalid API key")

    file_bytes = await file.read()
    try:
        text = extract_text_from_pdf(file_bytes)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Cannot read file: {str(e)}")

    if not text.strip():
        raise HTTPException(status_code=400, detail="File is empty or unreadable")

    text = text[:12000]
    n = int(num_questions)

    diff_map = {
        "easy": "лёгкие вопросы на базовое понимание",
        "medium": "вопросы среднего уровня на применение знаний",
        "hard": "сложные вопросы на глубокий анализ",
    }
    diff_desc = diff_map.get(difficulty, diff_map["medium"])

    prompt = (
        f"На основе текста создай ровно {n} тестовых вопросов на {language} языке. "
        f"Сложность: {diff_desc}.\n\nТекст:\n{text}\n\n"
        f"Верни ТОЛЬКО валидный JSON-массив без текста вне массива:\n"
        f'[{{"id":"uuid","type":"single_choice","question":"...","options":["A","B","C","D"],"correct_answer":"A","explanation":"..."}}]'
    )

    raw = await call_ai(
        prompt,
        "Ты эксперт по образовательным тестам. Отвечай ТОЛЬКО валидным JSON-массивом.",
        json_mode=False,
    )

    if "```json" in raw:
        raw = raw.split("```json")[1].split("```")[0]
    elif "```" in raw:
        raw = raw.split("```")[1].split("```")[0]
    else:
        m = re.search(r"(\[[\s\S]*\])", raw)
        if m:
            raw = m.group(1)

    questions = json.loads(raw.strip())
    for q in questions:
        q["id"] = str(uuid_lib.uuid4())

    quiz_id = str(uuid_lib.uuid4())
    title = (file.filename or "Тест").rsplit(".", 1)[0]

    supabase_url = os.getenv("SUPABASE_URL")
    supabase_key = os.getenv("SUPABASE_SERVICE_KEY")
    sb_headers = {
        "apikey": supabase_key,
        "Authorization": f"Bearer {supabase_key}",
        "Content-Type": "application/json",
    }

    async with httpx.AsyncClient() as client:
        r = await client.get(
            f"{supabase_url}/rest/v1/users_credits",
            headers=sb_headers,
            params={"email": f"eq.{email}", "select": "credits"},
        )
        data = r.json()
        if not data:
            raise HTTPException(status_code=404, detail="User not found")
        credits = data[0].get("credits", 0)
        if credits < 1:
            raise HTTPException(status_code=402, detail="Insufficient credits")

        r = await client.post(
            f"{supabase_url}/rest/v1/quizzes",
            headers={**sb_headers, "Prefer": "return=minimal"},
            json={"id": quiz_id, "title": title, "questions": questions, "email": email},
        )
        if r.status_code not in (200, 201):
            raise HTTPException(status_code=500, detail=f"Supabase error: {r.text}")

        await client.patch(
            f"{supabase_url}/rest/v1/users_credits",
            headers={**sb_headers, "Prefer": "return=minimal"},
            params={"email": f"eq.{email}"},
            json={"credits": credits - 1},
        )

    return {"test_id": quiz_id}
