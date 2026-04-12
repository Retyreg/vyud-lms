import logging

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.ai.client import _stream_explanation, call_ai
from app.core.deps import get_db
from app.models.knowledge import KnowledgeEdge, KnowledgeNode, NodeExplanation, NodeSRProgress
from app.schemas.sr import CompleteRequest, ReviewRequest
from app.services.sm2 import calculate_next_interval, get_mastery_level, is_due, next_review_date
from app.services.streak import update_streak

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["nodes"])

# Maps 4-button UI rating (0-3) to SM-2 quality (0-5)
_QUALITY_MAP = {0: 0, 1: 2, 2: 4, 3: 5}

_TUTOR_SYSTEM = (
    "Ты AI-тьютор платформы VYUD. Правила: "
    "начни с ключевой идеи (1-2 предложения), "
    "приведи конкретный пример из жизни, "
    "объясни почему это важно знать. "
    "Максимум 120 слов. "
    "Не используй слова 'данный', 'следует отметить'. "
    "Отвечай сразу — без вводных фраз типа 'Конечно!' или 'Отличный вопрос!'."
)


@router.get("/explain/{node_id}")
async def explain_node(node_id: int, regenerate: bool = False, db: Session = Depends(get_db)):
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
            return {"explanation": cached.explanation, "cached": True}

    description_part = f"\nКонтекст: {node.description}" if node.description else ""
    prompt = f"Объясни концепт '{node.label}' простым языком для новичка.{description_part}"

    try:
        explanation = await call_ai(prompt, _TUTOR_SYSTEM, json_mode=False)
    except RuntimeError:
        raise HTTPException(status_code=503, detail="AI providers unavailable. Try again later.")

    existing = db.query(NodeExplanation).filter(NodeExplanation.node_id == node_id).first()
    if existing:
        existing.explanation = explanation
    else:
        db.add(NodeExplanation(node_id=node_id, explanation=explanation))
    db.commit()

    return {"explanation": explanation, "cached": False}


@router.get("/explain-stream/{node_id}")
async def explain_node_stream(node_id: int, regenerate: bool = False, db: Session = Depends(get_db)):
    import json

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

            return StreamingResponse(
                _cached(),
                media_type="text/event-stream",
                headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
            )

    return StreamingResponse(
        _stream_explanation(node_id, node.label, node.description, db),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.post("/nodes/{node_id}/complete")
def mark_node_complete(
    node_id: int,
    request: CompleteRequest = CompleteRequest(),
    db: Session = Depends(get_db),
):
    node = db.query(KnowledgeNode).filter(KnowledgeNode.id == node_id).first()
    if not node:
        raise HTTPException(status_code=404, detail="Node not found")
    node.is_completed = True
    db.commit()
    if request.user_key:
        update_streak(request.user_key, db)
    return {"status": "ok", "node_id": node_id}


@router.post("/nodes/{node_id}/review")
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


@router.get("/nodes/{node_id}/sr-status")
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
