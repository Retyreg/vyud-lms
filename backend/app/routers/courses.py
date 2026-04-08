"""Course CRUD and AI generation endpoints."""
import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.auth.dependencies import get_telegram_user
from app.dependencies import get_db
from app.models.course import Course
from app.models.knowledge import KnowledgeNode, KnowledgeEdge
from app.schemas.graph import GraphResponse, NodeSchema
from app.schemas.course import CourseGenerationRequest
from app.services.ai import call_ai
from app.services.course import parse_ai_nodes, create_course_from_nodes

logger = logging.getLogger(__name__)

router = APIRouter()


def _build_graph_response(nodes, edges) -> dict:
    """Build a GraphResponse dict from ORM node and edge lists."""
    completed_ids = {n.id for n in nodes if n.is_completed}
    node_schemas = []
    for n in nodes:
        prereqs = n.prerequisites or []
        is_available = all(pid in completed_ids for pid in prereqs)
        node_schemas.append(
            NodeSchema(
                id=n.id,
                label=n.label,
                level=n.level,
                is_completed=n.is_completed,
                is_available=is_available,
            )
        )
    return {
        "nodes": node_schemas,
        "edges": [{"source": e.source_id, "target": e.target_id} for e in edges],
    }


@router.get("/api/courses/latest", response_model=GraphResponse)
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
        KnowledgeEdge.target_id.in_(node_ids),
    ).all()

    return _build_graph_response(nodes, edges)


_GENERATION_PROMPT_TEMPLATE = (
    "Создай дорожную карту обучения теме '{topic}'. "
    "Верни JSON-массив из 5–7 объектов, где каждый объект: "
    '[{{"title": "...", "description": "...", "list_of_prerequisite_titles": []}}]'
)

_GENERATION_SYSTEM = "Ты эксперт. Ответ — только валидный JSON без комментариев."


@router.post("/api/courses/generate")
async def generate_course_smart(
    request: CourseGenerationRequest,
    db: Session = Depends(get_db),
    _tg_user: dict = Depends(get_telegram_user),
):
    topic = request.topic
    prompt = _GENERATION_PROMPT_TEMPLATE.format(topic=topic)

    try:
        ai_content = await call_ai(prompt, _GENERATION_SYSTEM, json_mode=False)
        nodes_data = parse_ai_nodes(ai_content)
        create_course_from_nodes(db, topic, nodes_data)
        return {"status": "ok", "message": "Success"}

    except RuntimeError:
        db.rollback()
        raise HTTPException(status_code=503, detail="AI providers unavailable. Try again later.")
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))
