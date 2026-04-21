import logging
import os
import secrets
import smtplib
from datetime import datetime, timedelta, timezone
from email.mime.text import MIMEText

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.auth.demo import get_demo_user
from app.core.deps import get_db
from app.demo.seed import seed_demo_user
from app.models.demo import DemoFeedback, DemoUser
from app.schemas.demo import (
    DemoAuthResponse,
    DemoFeedbackRequest,
    DemoRegisterRequest,
    DemoRegisterResponse,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/demo", tags=["demo"])

SESSION_TTL_HOURS = 24
DEMO_LIFETIME_DAYS = 14
AI_RATE_LIMIT = 10

FRONTEND_URL = os.getenv("FRONTEND_URL", "https://lms.vyud.online")


def _send_magic_link_email(to_email: str, magic_link: str, full_name: str) -> bool:
    """Send magic link via SMTP if configured. Returns True on success."""
    host = os.getenv("SMTP_HOST")
    if not host:
        return False
    try:
        port = int(os.getenv("SMTP_PORT", "587"))
        user = os.getenv("SMTP_USER", "")
        password = os.getenv("SMTP_PASSWORD", "")
        from_addr = os.getenv("SMTP_FROM", user)

        body = (
            f"Привет, {full_name}!\n\n"
            f"Вот ваша ссылка для входа в демо VYUD LMS:\n{magic_link}\n\n"
            "Ссылка действительна 24 часа.\n\n— Команда VYUD"
        )
        msg = MIMEText(body, "plain", "utf-8")
        msg["Subject"] = "Ваш доступ к демо VYUD LMS"
        msg["From"] = from_addr
        msg["To"] = to_email

        with smtplib.SMTP(host, port) as smtp:
            smtp.starttls()
            if user:
                smtp.login(user, password)
            smtp.sendmail(from_addr, [to_email], msg.as_string())
        return True
    except Exception as exc:
        logger.warning("SMTP send failed: %s", exc)
        return False


@router.post("/register", response_model=DemoRegisterResponse)
def register_demo_user(payload: DemoRegisterRequest, db: Session = Depends(get_db)):
    existing = db.query(DemoUser).filter(DemoUser.email == payload.email).first()
    if existing and existing.archived_at is None:
        # Re-issue magic link for existing active session
        magic_link = f"{FRONTEND_URL}/demo/magic/{existing.magic_token}"
        sent = _send_magic_link_email(payload.email, magic_link, existing.full_name)
        return DemoRegisterResponse(magic_link=magic_link, show_on_screen=not sent)

    token = secrets.token_urlsafe(32)
    now = datetime.now(timezone.utc)

    user = DemoUser(
        email=payload.email,
        full_name=payload.full_name,
        company=payload.company,
        role=payload.role,
        industry=payload.industry,
        magic_token=token,
        session_expires_at=now + timedelta(hours=SESSION_TTL_HOURS),
        ai_calls_reset_at=now,
    )
    db.add(user)
    db.flush()  # get user.id before seed

    try:
        course = seed_demo_user(db, user)
        user.demo_course_id = course.id
    except Exception as exc:
        logger.error("Seed failed for %s: %s", payload.email, exc)

    db.commit()
    db.refresh(user)

    magic_link = f"{FRONTEND_URL}/demo/magic/{token}"
    sent = _send_magic_link_email(payload.email, magic_link, payload.full_name)
    return DemoRegisterResponse(magic_link=magic_link, show_on_screen=not sent)


@router.get("/auth/{token}", response_model=DemoAuthResponse)
def auth_demo_token(token: str, db: Session = Depends(get_db)):
    user = db.query(DemoUser).filter(DemoUser.magic_token == token).first()
    if not user:
        raise HTTPException(status_code=404, detail="Magic link not found or already used")

    if user.archived_at is not None:
        raise HTTPException(status_code=403, detail="Demo session has been archived")

    now = datetime.now(timezone.utc)
    # Refresh session on each magic-link use (within lifetime)
    created_at = user.created_at.replace(tzinfo=timezone.utc) if user.created_at.tzinfo is None else user.created_at
    if now > created_at + timedelta(days=DEMO_LIFETIME_DAYS):
        raise HTTPException(status_code=403, detail="Demo period of 14 days has ended")

    user.session_expires_at = now + timedelta(hours=SESSION_TTL_HOURS)
    db.commit()

    return DemoAuthResponse(
        session_token=user.magic_token,
        demo_user_id=str(user.id),
        demo_course_id=user.demo_course_id,
        full_name=user.full_name,
        expires_at=user.session_expires_at.isoformat(),
    )


@router.post("/feedback", status_code=201)
def submit_feedback(
    payload: DemoFeedbackRequest,
    demo_user: DemoUser = Depends(get_demo_user),
    db: Session = Depends(get_db),
):
    fb = DemoFeedback(
        demo_user_id=str(demo_user.id),
        rating=payload.rating,
        message=payload.message,
        wants_pilot=payload.wants_pilot,
    )
    db.add(fb)
    db.commit()
    logger.info(
        "Demo feedback from %s: rating=%d wants_pilot=%s",
        demo_user.email,
        payload.rating,
        payload.wants_pilot,
    )
    return {"status": "ok"}


@router.get("/ai-check")
def check_ai_rate_limit(
    demo_user: DemoUser = Depends(get_demo_user),
    db: Session = Depends(get_db),
):
    """Returns remaining AI calls for today. Called before triggering AI explanation."""
    now = datetime.now(timezone.utc)
    reset_at = demo_user.ai_calls_reset_at
    if reset_at:
        reset_at = reset_at.replace(tzinfo=timezone.utc) if reset_at.tzinfo is None else reset_at
    if reset_at is None or now.date() > reset_at.date():
        demo_user.ai_calls_today = 0
        demo_user.ai_calls_reset_at = now
        db.commit()

    remaining = max(0, AI_RATE_LIMIT - demo_user.ai_calls_today)
    return {"remaining": remaining, "limit": AI_RATE_LIMIT}


@router.post("/ai-increment")
def increment_ai_call(
    demo_user: DemoUser = Depends(get_demo_user),
    db: Session = Depends(get_db),
):
    """Called after a successful AI explanation to count against daily quota."""
    now = datetime.now(timezone.utc)
    reset_at = demo_user.ai_calls_reset_at
    if reset_at:
        reset_at = reset_at.replace(tzinfo=timezone.utc) if reset_at.tzinfo is None else reset_at
    if reset_at is None or now.date() > reset_at.date():
        demo_user.ai_calls_today = 0
        demo_user.ai_calls_reset_at = now

    if demo_user.ai_calls_today >= AI_RATE_LIMIT:
        raise HTTPException(status_code=429, detail="Daily AI call limit reached (10/day)")

    demo_user.ai_calls_today += 1
    db.commit()
    return {"calls_used": demo_user.ai_calls_today, "limit": AI_RATE_LIMIT}
