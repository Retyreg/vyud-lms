from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional

from app.db.base import Base, engine
import app.models 

# Создаем таблицы при старте приложения
Base.metadata.create_all(bind=engine)

app = FastAPI(title="VYUD LMS API", version="0.1.0")

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
def get_courses():
    """
    Возвращает список доступных курсов (пока пустой или моковый).
    """
    # В будущем здесь будет запрос к БД: db.query(Course).all()
    return []

@app.get("/api/knowledge-graph", response_model=GraphResponse)
def get_knowledge_graph():
    """
    Возвращает структуру дерева навыков для визуализации.
    Пока возвращаем моковые данные (Mock Data).
    """
    mock_nodes = [
        NodeSchema(id=1, label="Python Basics", level=1),
        NodeSchema(id=2, label="Variables", level=1),
        NodeSchema(id=3, label="Functions", level=2),
        NodeSchema(id=4, label="FastAPI", level=3),
    ]
    
    mock_edges = [
        EdgeSchema(source=1, target=2), # Basics -> Variables
        EdgeSchema(source=2, target=3), # Variables -> Functions
        EdgeSchema(source=3, target=4), # Functions -> FastAPI
    ]
    
    return GraphResponse(nodes=mock_nodes, edges=mock_edges)
