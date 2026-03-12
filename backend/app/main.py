import json
import re
import os
import time
import httpx
import logging
from contextlib import asynccontextmanager
from datetime import datetime, UTC
from typing import List, Optional

from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from sqlalchemy.orm import Session
from pydantic import BaseModel, EmailStr
from dotenv import load_dotenv
from litellm import completion

try:
    from passlib.context import CryptContext
    _pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto", bcrypt__rounds=12)
    _passlib_available = True
except Exception:  # pragma: no cover
    _passlib_available = False
    _pwd_context = None  # type: ignore[assignment]

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

    # Запасной вариант на случай проблем с Groq
    response = completion(model="gemini/gemini-1.5-flash", messages=messages)
    return response.choices[0].message.content

# Импорты БД
from app.db.base import Base, engine, SessionLocal
from app.models.course import Course
from app.models.knowledge import KnowledgeNode, KnowledgeEdge
from app.models.user import User, UserRole
from app.models.task import Task, TaskStatus, TaskPriority

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
async def generate_course_smart(request: CourseGenerationRequest, db: Session = Depends(get_db)):
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

    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/explain/{topic}")
async def explain_topic(topic: str):
    content = await call_ai(f"Объясни для новичка: {topic}", "Ты репетитор.", json_mode=False)
    return {"explanation": content}


# ═══════════════════════════════════════════════════════════════════════════
# Auth endpoints  (spec section 4.4 / 6.1)
# ═══════════════════════════════════════════════════════════════════════════

def _hash_password(password: str) -> str:
    """Hash a plain-text password with bcrypt (cost=12 per spec 6.2)."""
    if _passlib_available and _pwd_context is not None:
        return _pwd_context.hash(password)
    # Fallback for test environments where passlib may not be installed.
    # Uses PBKDF2-HMAC-SHA256 (standard-library KDF) — still secure for tests.
    import hashlib
    import secrets
    salt = secrets.token_hex(16)
    dk = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 260000)
    return f"pbkdf2${salt}${dk.hex()}"


def _verify_password(plain: str, hashed: str) -> bool:
    """Verify a plain-text password against its hash."""
    if _passlib_available and _pwd_context is not None:
        try:
            return _pwd_context.verify(plain, hashed)
        except Exception:
            pass
    # Fallback: verify PBKDF2 hashes created by the fallback hasher above.
    if hashed.startswith("pbkdf2$"):
        import hashlib
        try:
            _, salt, stored_hex = hashed.split("$", 2)
            dk = hashlib.pbkdf2_hmac("sha256", plain.encode(), salt.encode(), 260000)
            return dk.hex() == stored_hex
        except Exception:
            return False
    return False


class UserRegisterRequest(BaseModel):
    email: EmailStr
    password: str
    full_name: Optional[str] = None
    role: UserRole = UserRole.ASSOCIATE


class UserResponse(BaseModel):
    id: int
    email: str
    full_name: Optional[str]
    role: UserRole
    is_active: bool

    model_config = {"from_attributes": True}


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


@app.post("/api/v1/auth/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED,
          tags=["auth"])
def register_user(request: UserRegisterRequest, db: Session = Depends(get_db)):
    """Register a new user. Passwords are hashed with bcrypt (cost=12)."""
    existing = db.query(User).filter(User.email == request.email).first()
    if existing:
        raise HTTPException(status_code=409, detail="Email already registered")

    user = User(
        email=request.email,
        hashed_password=_hash_password(request.password),
        full_name=request.full_name,
        role=request.role,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@app.post("/api/v1/auth/login", tags=["auth"])
def login_user(request: LoginRequest, db: Session = Depends(get_db)):
    """Authenticate a user and return a placeholder token.

    In production this endpoint will issue JWT access/refresh tokens via
    Auth0/Cognito (spec section 6.1). The token field is intentionally a
    placeholder for the MVP — replace with real JWT issuance before pilot.
    """
    user = db.query(User).filter(User.email == request.email).first()
    if not user or not _verify_password(request.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )
    if not user.is_active:
        raise HTTPException(status_code=403, detail="Account is disabled")

    return {
        "token_type": "bearer",
        # TODO: replace with real JWT (Auth0/Cognito) before pilot
        "access_token": f"placeholder_token_user_{user.id}",
        "user": {"id": user.id, "email": user.email, "role": user.role},
    }


@app.get("/api/v1/users/me", response_model=UserResponse, tags=["users"])
def get_current_user_placeholder():
    """Placeholder — returns 501 until JWT middleware is wired up."""
    raise HTTPException(status_code=501, detail="JWT auth not yet implemented — see Auth0/Cognito integration")


# ═══════════════════════════════════════════════════════════════════════════
# Task management endpoints  (spec Phase 1 / section 4.4)
# ═══════════════════════════════════════════════════════════════════════════

class TaskCreate(BaseModel):
    title: str
    description: Optional[str] = None
    priority: TaskPriority = TaskPriority.MEDIUM
    assignee_id: Optional[int] = None
    due_date: Optional[datetime] = None
    checklist: Optional[List[dict]] = None


class TaskUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    status: Optional[TaskStatus] = None
    priority: Optional[TaskPriority] = None
    assignee_id: Optional[int] = None
    due_date: Optional[datetime] = None
    checklist: Optional[List[dict]] = None
    photo_url: Optional[str] = None


class TaskResponse(BaseModel):
    id: int
    title: str
    description: Optional[str]
    status: TaskStatus
    priority: TaskPriority
    assignee_id: Optional[int]
    created_by_id: Optional[int]
    checklist: Optional[List[dict]]
    due_date: Optional[datetime]
    created_at: Optional[datetime]
    updated_at: Optional[datetime]
    completed_at: Optional[datetime]
    photo_url: Optional[str]

    model_config = {"from_attributes": True}


@app.get("/api/v1/tasks", response_model=List[TaskResponse], tags=["tasks"])
def list_tasks(
    status_filter: Optional[TaskStatus] = None,
    assignee_id: Optional[int] = None,
    limit: int = 50,
    offset: int = 0,
    db: Session = Depends(get_db),
):
    """List tasks with optional filters. Supports cursor-based style via offset."""
    q = db.query(Task)
    if status_filter:
        q = q.filter(Task.status == status_filter)
    if assignee_id is not None:
        q = q.filter(Task.assignee_id == assignee_id)
    return q.order_by(Task.created_at.desc()).offset(offset).limit(limit).all()


@app.post("/api/v1/tasks", response_model=TaskResponse, status_code=status.HTTP_201_CREATED,
          tags=["tasks"])
def create_task(request: TaskCreate, db: Session = Depends(get_db)):
    """Create a new task."""
    task = Task(
        title=request.title,
        description=request.description,
        priority=request.priority,
        assignee_id=request.assignee_id,
        due_date=request.due_date,
        checklist=request.checklist or [],
    )
    db.add(task)
    db.commit()
    db.refresh(task)
    return task


@app.get("/api/v1/tasks/{task_id}", response_model=TaskResponse, tags=["tasks"])
def get_task(task_id: int, db: Session = Depends(get_db)):
    """Get a single task by ID."""
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return task


@app.patch("/api/v1/tasks/{task_id}", response_model=TaskResponse, tags=["tasks"])
def update_task(task_id: int, request: TaskUpdate, db: Session = Depends(get_db)):
    """Update a task. Marks completed_at when status → completed."""
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    for field, value in request.model_dump(exclude_unset=True).items():
        setattr(task, field, value)

    if request.status == TaskStatus.COMPLETED and not task.completed_at:
        task.completed_at = datetime.now(tz=UTC)

    db.commit()
    db.refresh(task)
    return task


@app.delete("/api/v1/tasks/{task_id}", status_code=status.HTTP_204_NO_CONTENT, tags=["tasks"])
def delete_task(task_id: int, db: Session = Depends(get_db)):
    """Delete a task."""
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    db.delete(task)
    db.commit()
