from typing import List, Optional
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.deps import get_db
from app.models.feedback import Feedback

router = APIRouter(prefix="/api", tags=["feedback"])


class FeedbackRequest(BaseModel):
    user_key: Optional[str] = None
    rating: Optional[int] = None      # 1-5
    liked: Optional[str] = None
    missing: Optional[str] = None
    feature: Optional[str] = None
    contact: Optional[str] = None
    page: Optional[str] = None


class FeedbackItem(BaseModel):
    id: int
    user_key: Optional[str]
    rating: Optional[int]
    liked: Optional[str]
    missing: Optional[str]
    feature: Optional[str]
    contact: Optional[str]
    page: Optional[str]
    created_at: str

    class Config:
        from_attributes = True


@router.post("/feedback", status_code=201)
def submit_feedback(body: FeedbackRequest, db: Session = Depends(get_db)):
    """Submit user feedback — anonymous or with user_key."""
    fb = Feedback(
        user_key=body.user_key,
        rating=body.rating,
        liked=body.liked or None,
        missing=body.missing or None,
        feature=body.feature or None,
        contact=body.contact or None,
        page=body.page or None,
    )
    db.add(fb)
    db.commit()
    return {"status": "ok", "id": fb.id}


@router.get("/feedback", response_model=List[FeedbackItem])
def list_feedback(limit: int = 100, db: Session = Depends(get_db)):
    """List recent feedback entries (admin use)."""
    rows = db.query(Feedback).order_by(Feedback.created_at.desc()).limit(limit).all()
    return [
        FeedbackItem(
            id=r.id,
            user_key=r.user_key,
            rating=r.rating,
            liked=r.liked,
            missing=r.missing,
            feature=r.feature,
            contact=r.contact,
            page=r.page,
            created_at=r.created_at.isoformat() if r.created_at else "",
        )
        for r in rows
    ]
