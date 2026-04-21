import os
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Header, HTTPException, Query
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.deps import get_db
from app.models.demo import DemoFeedback, DemoUser

router = APIRouter(prefix="/api/v1/admin", tags=["admin"])

ADMIN_EMAIL = os.getenv("ADMIN_EMAIL", "vatyutovd@gmail.com")


def _check_admin(
    x_admin_email: str = Header(default=""),
    admin_email: str = Query(default=""),
) -> None:
    email = x_admin_email or admin_email
    if email != ADMIN_EMAIL:
        raise HTTPException(status_code=403, detail="Admin access required")


@router.get("/demo/users")
def list_demo_users(
    _: None = Depends(_check_admin),
    db: Session = Depends(get_db),
):
    users = db.query(DemoUser).order_by(DemoUser.created_at.desc()).all()
    now = datetime.now(timezone.utc)

    feedback_counts = dict(
        db.query(DemoFeedback.demo_user_id, func.count(DemoFeedback.id))
        .group_by(DemoFeedback.demo_user_id)
        .all()
    )
    pilot_flags = set(
        row[0]
        for row in db.query(DemoFeedback.demo_user_id)
        .filter(DemoFeedback.wants_pilot.is_(True))
        .distinct()
        .all()
    )

    result = []
    for u in users:
        created = u.created_at.replace(tzinfo=timezone.utc) if u.created_at and u.created_at.tzinfo is None else u.created_at
        expires = u.session_expires_at.replace(tzinfo=timezone.utc) if u.session_expires_at and u.session_expires_at.tzinfo is None else u.session_expires_at
        days_left = max(0, (expires - now).days) if expires else 0
        result.append({
            "id": str(u.id),
            "email": u.email,
            "full_name": u.full_name,
            "company": u.company,
            "role": u.role,
            "industry": u.industry,
            "created_at": created.isoformat() if created else None,
            "session_days_left": days_left,
            "archived": u.archived_at is not None,
            "ai_calls_today": u.ai_calls_today,
            "feedback_count": feedback_counts.get(str(u.id), 0),
            "wants_pilot": str(u.id) in pilot_flags,
        })
    return result


@router.get("/demo/feedback")
def list_demo_feedback(
    _: None = Depends(_check_admin),
    db: Session = Depends(get_db),
):
    rows = (
        db.query(DemoFeedback, DemoUser.email, DemoUser.company)
        .join(DemoUser, DemoFeedback.demo_user_id == DemoUser.id)
        .order_by(DemoFeedback.created_at.desc())
        .all()
    )
    return [
        {
            "id": str(fb.id),
            "demo_user_email": email,
            "company": company,
            "rating": fb.rating,
            "message": fb.message,
            "wants_pilot": fb.wants_pilot,
            "created_at": fb.created_at.isoformat() if fb.created_at else None,
        }
        for fb, email, company in rows
    ]
