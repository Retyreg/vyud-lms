import json
import logging
import re

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.ai.client import call_ai
from app.auth.dependencies import get_telegram_user
from app.core.deps import get_db
from app.models.course import Course
from app.models.knowledge import KnowledgeEdge, KnowledgeNode, NodeSRProgress
from app.schemas.graph import CourseGenerationRequest, GraphResponse, NodeSchema
from app.services.sm2 import mastery_pct

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["courses"])


def _build_graph_response(course: Course, db: Session, user_key: str | None = None) -> dict:
    """Build GraphResponse dict for a given course.

    When user_key is provided, enriches each node with mastery_pct and
    next_review from the user's SM-2 progress records.
    """
    nodes = db.query(KnowledgeNode).filter(KnowledgeNode.course_id == course.id).all()
    if not nodes:
        return {"nodes": [], "edges": []}

    node_ids = {n.id for n in nodes}
    edges = db.query(KnowledgeEdge).filter(
        KnowledgeEdge.source_id.in_(node_ids),
        KnowledgeEdge.target_id.in_(node_ids),
    ).all()

    # Fetch SM-2 progress for the user in one query
    sr_map: dict[int, NodeSRProgress] = {}
    if user_key:
        sr_records = db.query(NodeSRProgress).filter(
            NodeSRProgress.node_id.in_(node_ids),
            NodeSRProgress.user_key == user_key,
        ).all()
        sr_map = {r.node_id: r for r in sr_records}

    completed_ids = {n.id for n in nodes if n.is_completed}
    node_schemas = []
    for n in nodes:
        prereqs = n.prerequisites or []
        is_available = all(pid in completed_ids for pid in prereqs)
        sr = sr_map.get(n.id)
        pct = mastery_pct(sr.repetitions, sr.easiness_factor) if sr else 0
        next_rev = sr.next_review.isoformat() if sr and sr.next_review else None
        node_schemas.append(NodeSchema(
            id=n.id, label=n.label, level=n.level,
            is_completed=n.is_completed, is_available=is_available,
            mastery_pct=pct, next_review=next_rev,
        ))

    return {
        "nodes": node_schemas,
        "edges": [{"source": e.source_id, "target": e.target_id} for e in edges],
    }


def _parse_ai_nodes(ai_content: str) -> list[dict]:
    """Extract and validate node list from AI response text."""
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
        raise ValueError("AI вернул некорректные данные: каждый элемент должен быть объектом с полем 'title'")

    return nodes_data


def _persist_course(topic: str, org_id: int | None, nodes_data: list[dict], db: Session) -> Course:
    """Create Course + KnowledgeNode + KnowledgeEdge rows and commit."""
    new_course = Course(title=topic, description=f"Курс: {topic}", org_id=org_id)
    db.add(new_course)
    db.flush()

    title_to_id: dict[str, int] = {}
    created_nodes: list[tuple[KnowledgeNode, list[str]]] = []

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
    return new_course


@router.get("/courses/latest", response_model=GraphResponse)
def get_latest_course(user_key: str | None = None, db: Session = Depends(get_db)):
    course = db.query(Course).order_by(Course.id.desc()).first()
    if not course:
        return {"nodes": [], "edges": []}
    return _build_graph_response(course, db, user_key=user_key)


@router.post("/courses/generate")
async def generate_course_smart(
    request: CourseGenerationRequest,
    db: Session = Depends(get_db),
    _tg_user: dict = Depends(get_telegram_user),
):
    prompt = (
        f"Создай дорожную карту обучения теме '{request.topic}'. "
        f"Верни JSON-массив из 5–7 объектов, где каждый объект: "
        f'[{{"title": "...", "description": "...", "list_of_prerequisite_titles": []}}]'
    )
    try:
        ai_content = await call_ai(
            prompt,
            "Ты эксперт. Ответ — только валидный JSON без комментариев.",
            json_mode=False,
        )
        nodes_data = _parse_ai_nodes(ai_content)
        _persist_course(request.topic, None, nodes_data, db)
        return {"status": "ok", "message": "Success"}
    except RuntimeError:
        db.rollback()
        raise HTTPException(status_code=503, detail="AI providers unavailable. Try again later.")
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))
