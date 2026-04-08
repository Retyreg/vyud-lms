"""Node completion, SM-2 review, and SR-status endpoints."""
import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.dependencies import get_db
from app.models.knowledge import KnowledgeNode, NodeSRProgress
from app.schemas.node import CompleteRequest, ReviewRequest
from app.services.sm2 import calculate_next_interval, get_mastery_level, is_due, next_review_date
from app.services.streak import update_streak

logger = logging.getLogger(__name__)

router = APIRouter()

# Maps 4-button UI rating (0-3) to SM-2 quality (0-5)
_QUALITY_MAP = {0: 0, 1: 2, 2: 4, 3: 5}


@router.post("/api/nodes/{node_id}/complete")
def mark_node_complete(
    node_id: int, request: CompleteRequest = CompleteRequest(), db: Session = Depends(get_db)
):
    node = db.query(KnowledgeNode).filter(KnowledgeNode.id == node_id).first()
    if not node:
        raise HTTPException(status_code=404, detail="Node not found")
    node.is_completed = True
    db.commit()
    if request.user_key:
        update_streak(request.user_key, db)
    return {"status": "ok", "node_id": node_id}


@router.post("/api/nodes/{node_id}/review")
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


@router.get("/api/nodes/{node_id}/sr-status")
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
