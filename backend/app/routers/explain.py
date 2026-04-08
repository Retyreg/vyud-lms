"""AI explanation endpoints (cached and SSE-streaming)."""
import json
import logging

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.dependencies import get_db
from app.models.knowledge import KnowledgeNode, NodeExplanation
from app.services.ai import call_ai, build_explain_prompt, TUTOR_SYSTEM_PROMPT, stream_explanation

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/api/explain/{node_id}")
async def explain_node(node_id: int, regenerate: bool = False, db: Session = Depends(get_db)):
    node = db.query(KnowledgeNode).filter(KnowledgeNode.id == node_id).first()
    if not node:
        raise HTTPException(status_code=404, detail="Node not found")

    # Check cache
    if not regenerate:
        cached = (
            db.query(NodeExplanation)
            .filter(NodeExplanation.node_id == node_id)
            .order_by(NodeExplanation.created_at.desc())
            .first()
        )
        if cached:
            return {"explanation": cached.explanation, "cached": True}

    # Call AI
    prompt = build_explain_prompt(node.label, node.description)
    try:
        explanation = await call_ai(prompt, TUTOR_SYSTEM_PROMPT, json_mode=False)
    except RuntimeError:
        raise HTTPException(status_code=503, detail="AI providers unavailable. Try again later.")

    # Save to cache (upsert)
    existing = db.query(NodeExplanation).filter(NodeExplanation.node_id == node_id).first()
    if existing:
        existing.explanation = explanation
    else:
        db.add(NodeExplanation(node_id=node_id, explanation=explanation))
    db.commit()

    return {"explanation": explanation, "cached": False}


@router.get("/api/explain-stream/{node_id}")
async def explain_node_stream(
    node_id: int, regenerate: bool = False, db: Session = Depends(get_db)
):
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
        stream_explanation(node_id, node.label, node.description, db),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
