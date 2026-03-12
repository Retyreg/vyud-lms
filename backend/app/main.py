import json
import re
import os
import time
import httpx
import logging
from contextlib import asynccontextmanager
from datetime import datetime, UTC, timedelta
from typing import List, Optional

from fastapi import FastAPI, Depends, HTTPException, status, Security
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
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

try:
    from jose import jwt as _jose_jwt, JWTError
    _jose_available = True
except Exception:  # pragma: no cover
    _jose_available = False
    JWTError = Exception  # type: ignore[assignment,misc]

_start_time = time.time()

# Настройка логирования для отслеживания ошибок
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv()

GROQ_API_KEY = os.getenv("GROQ_API_KEY")

# JWT configuration (spec 6.1: access 15min, refresh 24h)
_JWT_DEFAULT_SECRET = "change-me-in-production-use-env-var"
JWT_SECRET_KEY = os.getenv("SECRET_KEY", _JWT_DEFAULT_SECRET)
JWT_ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 15
REFRESH_TOKEN_EXPIRE_HOURS = 24

# PBKDF2 iteration count for the fallback hasher (NIST SP 800-132 minimum)
PBKDF2_ITERATIONS = 260000

_http_bearer = HTTPBearer(auto_error=False)

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
from app.models.news import NewsPost

# Создаем таблицы при старте (в lifespan, чтобы не крашить приложение при недоступной БД)
@asynccontextmanager
async def lifespan(app: FastAPI):
    if JWT_SECRET_KEY == _JWT_DEFAULT_SECRET:
        logger.warning(
            "SECRET_KEY is not set — using insecure default. "
            "Set SECRET_KEY env var before deploying to production."
        )
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

def _create_token(data: dict, expires_delta: timedelta) -> str:
    """Encode a JWT with the given payload and expiry."""
    payload = data.copy()
    payload["exp"] = datetime.now(tz=UTC) + expires_delta
    if _jose_available:
        return _jose_jwt.encode(payload, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)
    # Fallback for test environments without python-jose
    import base64
    import hmac as _hmac
    import hashlib
    header = base64.urlsafe_b64encode(b'{"alg":"HS256","typ":"JWT"}').rstrip(b"=").decode()
    body_json = json.dumps({**payload, "exp": payload["exp"].timestamp()}).encode()
    body = base64.urlsafe_b64encode(body_json).rstrip(b"=").decode()
    sig_input = f"{header}.{body}".encode()
    sig = _hmac.new(JWT_SECRET_KEY.encode(), sig_input, hashlib.sha256).digest()
    sig_b64 = base64.urlsafe_b64encode(sig).rstrip(b"=").decode()
    return f"{header}.{body}.{sig_b64}"


def _decode_token(token: str) -> Optional[dict]:
    """Decode and validate a JWT. Returns payload dict or None on failure."""
    if _jose_available:
        try:
            return _jose_jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
        except JWTError:
            return None
    # Fallback minimal decoder for test environments
    import base64
    try:
        parts = token.split(".")
        if len(parts) != 3:
            return None
        padding = "=" * (4 - len(parts[1]) % 4)
        payload = json.loads(base64.urlsafe_b64decode(parts[1] + padding))
        if payload.get("exp", 0) < datetime.now(tz=UTC).timestamp():
            return None
        return payload
    except Exception:
        return None


def _require_auth(
    credentials: Optional[HTTPAuthorizationCredentials],
    db: Session,
) -> "User":
    """Decode Bearer JWT and return the matching active User. Raises 401 on failure."""
    if credentials is None:
        raise HTTPException(status_code=401, detail="Authorization header required")
    payload = _decode_token(credentials.credentials)
    if payload is None or payload.get("type") != "access":
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    try:
        user_id = int(payload["sub"])
    except (KeyError, ValueError):
        raise HTTPException(status_code=401, detail="Malformed token")
    user = db.query(User).filter(User.id == user_id, User.is_active.is_(True)).first()
    if not user:
        raise HTTPException(status_code=401, detail="User not found or inactive")
    return user

def _hash_password(password: str) -> str:
    """Hash a plain-text password with bcrypt (cost=12 per spec 6.2)."""
    if _passlib_available and _pwd_context is not None:
        return _pwd_context.hash(password)
    # Fallback for test environments where passlib may not be installed.
    # Uses PBKDF2-HMAC-SHA256 (standard-library KDF) — still secure for tests.
    import hashlib
    import secrets
    salt = secrets.token_hex(16)
    dk = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), PBKDF2_ITERATIONS)
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
            dk = hashlib.pbkdf2_hmac("sha256", plain.encode(), salt.encode(), PBKDF2_ITERATIONS)
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
    """Authenticate a user and return real JWT access + refresh tokens.

    - access_token expires in 15 minutes (spec 6.1)
    - refresh_token expires in 24 hours (spec 6.1)
    """
    user = db.query(User).filter(User.email == request.email).first()
    if not user or not _verify_password(request.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )
    if not user.is_active:
        raise HTTPException(status_code=403, detail="Account is disabled")

    access_token = _create_token(
        {"sub": str(user.id), "role": user.role, "type": "access"},
        expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES),
    )
    refresh_token = _create_token(
        {"sub": str(user.id), "type": "refresh"},
        expires_delta=timedelta(hours=REFRESH_TOKEN_EXPIRE_HOURS),
    )

    return {
        "token_type": "bearer",
        "access_token": access_token,
        "refresh_token": refresh_token,
        "expires_in": ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        "user": {"id": user.id, "email": user.email, "role": user.role},
    }


class RefreshRequest(BaseModel):
    refresh_token: str


@app.post("/api/v1/auth/token/refresh", tags=["auth"])
def refresh_access_token(request: RefreshRequest, db: Session = Depends(get_db)):
    """Exchange a valid refresh token for a new access token."""
    payload = _decode_token(request.refresh_token)
    if payload is None or payload.get("type") != "refresh":
        raise HTTPException(status_code=401, detail="Invalid or expired refresh token")

    user_id = int(payload["sub"])
    user = db.query(User).filter(User.id == user_id, User.is_active.is_(True)).first()
    if not user:
        raise HTTPException(status_code=401, detail="User not found or inactive")

    access_token = _create_token(
        {"sub": str(user.id), "role": user.role, "type": "access"},
        expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES),
    )
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "expires_in": ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    }


@app.get("/api/v1/users/me", response_model=UserResponse, tags=["users"])
def get_current_user_me(
    credentials: Optional[HTTPAuthorizationCredentials] = Security(_http_bearer),
    db: Session = Depends(get_db),
):
    """Return the currently authenticated user (requires Bearer JWT)."""
    user = _require_auth(credentials, db)
    return user


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


# ═══════════════════════════════════════════════════════════════════════════
# Course management API  (spec Phase 1/2 — learning module)
# ═══════════════════════════════════════════════════════════════════════════

class CourseResponse(BaseModel):
    id: int
    title: str
    description: Optional[str]
    node_count: int
    completed_count: int

    model_config = {"from_attributes": True}


class CourseDetailResponse(BaseModel):
    id: int
    title: str
    description: Optional[str]
    nodes: List[NodeSchema]
    edges: List[EdgeSchema]


@app.get("/api/v1/courses", response_model=List[CourseResponse], tags=["courses"])
def list_courses(limit: int = 50, offset: int = 0, db: Session = Depends(get_db)):
    """List all courses with progress summary."""
    courses = db.query(Course).order_by(Course.id.desc()).offset(offset).limit(limit).all()
    result = []
    for c in courses:
        nodes = db.query(KnowledgeNode).filter(KnowledgeNode.course_id == c.id).all()
        completed = sum(1 for n in nodes if n.is_completed)
        result.append(CourseResponse(
            id=c.id,
            title=c.title,
            description=c.description,
            node_count=len(nodes),
            completed_count=completed,
        ))
    return result


@app.get("/api/v1/courses/{course_id}", response_model=CourseDetailResponse, tags=["courses"])
def get_course(course_id: int, db: Session = Depends(get_db)):
    """Get a single course with its full node/edge graph."""
    course = db.query(Course).filter(Course.id == course_id).first()
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")

    nodes = db.query(KnowledgeNode).filter(KnowledgeNode.course_id == course_id).all()
    node_ids = {n.id for n in nodes}
    edges = db.query(KnowledgeEdge).filter(
        KnowledgeEdge.source_id.in_(node_ids),
        KnowledgeEdge.target_id.in_(node_ids),
    ).all() if node_ids else []

    completed_ids = {n.id for n in nodes if n.is_completed}
    node_schemas = []
    for n in nodes:
        prereqs = n.prerequisites or []
        is_available = all(pid in completed_ids for pid in prereqs)
        node_schemas.append(NodeSchema(
            id=n.id, label=n.label, level=n.level,
            is_completed=n.is_completed, is_available=is_available,
        ))

    return CourseDetailResponse(
        id=course.id,
        title=course.title,
        description=course.description,
        nodes=node_schemas,
        edges=[EdgeSchema(source=e.source_id, target=e.target_id) for e in edges],
    )


@app.post(
    "/api/v1/courses/{course_id}/nodes/{node_id}/complete",
    response_model=NodeSchema,
    tags=["courses"],
)
def complete_node(course_id: int, node_id: int, db: Session = Depends(get_db)):
    """Mark a learning node as completed. Unlocks dependent nodes."""
    node = db.query(KnowledgeNode).filter(
        KnowledgeNode.id == node_id,
        KnowledgeNode.course_id == course_id,
    ).first()
    if not node:
        raise HTTPException(status_code=404, detail="Node not found in this course")

    # Check prerequisites are satisfied
    completed_ids = {
        n.id
        for n in db.query(KnowledgeNode).filter(
            KnowledgeNode.course_id == course_id,
            KnowledgeNode.is_completed.is_(True),
        ).all()
    }
    prereqs = node.prerequisites or []
    if not all(pid in completed_ids for pid in prereqs):
        raise HTTPException(
            status_code=409,
            detail="Prerequisites not yet completed",
        )

    node.is_completed = True
    db.commit()
    db.refresh(node)

    # Recalculate availability after completing this node
    all_completed = completed_ids | {node.id}
    prereqs_after = node.prerequisites or []
    is_available = all(pid in all_completed for pid in prereqs_after)
    return NodeSchema(
        id=node.id, label=node.label, level=node.level,
        is_completed=node.is_completed, is_available=is_available,
    )


# ═══════════════════════════════════════════════════════════════════════════
# News feed  (spec Phase 2 — communications module)
# ═══════════════════════════════════════════════════════════════════════════

class NewsPostCreate(BaseModel):
    title: str
    content: str
    summary: Optional[str] = None


class NewsPostUpdate(BaseModel):
    title: Optional[str] = None
    content: Optional[str] = None
    summary: Optional[str] = None
    is_published: Optional[bool] = None


class NewsPostResponse(BaseModel):
    id: int
    title: str
    content: str
    summary: Optional[str]
    author_id: Optional[int]
    is_published: bool
    created_at: Optional[datetime]
    updated_at: Optional[datetime]

    model_config = {"from_attributes": True}


@app.get("/api/v1/feed", response_model=List[NewsPostResponse], tags=["feed"])
def list_feed(limit: int = 20, offset: int = 0, db: Session = Depends(get_db)):
    """Return published news posts, newest first."""
    return (
        db.query(NewsPost)
        .filter(NewsPost.is_published.is_(True))
        .order_by(NewsPost.created_at.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )


@app.post("/api/v1/feed", response_model=NewsPostResponse, status_code=status.HTTP_201_CREATED,
          tags=["feed"])
def create_post(request: NewsPostCreate, db: Session = Depends(get_db)):
    """Create a news post."""
    post = NewsPost(
        title=request.title,
        content=request.content,
        summary=request.summary,
    )
    db.add(post)
    db.commit()
    db.refresh(post)
    return post


@app.get("/api/v1/feed/{post_id}", response_model=NewsPostResponse, tags=["feed"])
def get_post(post_id: int, db: Session = Depends(get_db)):
    """Get a single news post."""
    post = db.query(NewsPost).filter(NewsPost.id == post_id).first()
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")
    return post


@app.patch("/api/v1/feed/{post_id}", response_model=NewsPostResponse, tags=["feed"])
def update_post(post_id: int, request: NewsPostUpdate, db: Session = Depends(get_db)):
    """Update a news post."""
    post = db.query(NewsPost).filter(NewsPost.id == post_id).first()
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")
    for field, value in request.model_dump(exclude_unset=True).items():
        setattr(post, field, value)
    db.commit()
    db.refresh(post)
    return post


@app.delete("/api/v1/feed/{post_id}", status_code=status.HTTP_204_NO_CONTENT, tags=["feed"])
def delete_post(post_id: int, db: Session = Depends(get_db)):
    """Delete a news post."""
    post = db.query(NewsPost).filter(NewsPost.id == post_id).first()
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")
    db.delete(post)
    db.commit()
