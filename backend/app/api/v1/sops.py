import logging

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy.orm import Session
from sqlalchemy.sql import func

from app.ai.client import call_ai
from app.core.deps import get_db
from app.models.org import OrgMember, Organization
from app.models.sop import SOP, SOPCompletion, SOPStep
from app.schemas.sop import SOPListItem, SOPResponse, SOPStepSchema
from app.services.pdf import extract_text_from_pdf
from app.services.streak import update_streak

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["sops"])

import re
import json as _json


def _extract_json_list(raw: str) -> list:
    """Parse a JSON list from AI response, stripping markdown fences."""
    if "```json" in raw:
        raw = raw.split("```json")[1].split("```")[0]
    elif "```" in raw:
        raw = raw.split("```")[1].split("```")[0]
    else:
        m = re.search(r"(\[[\s\S]*\])", raw)
        if m:
            raw = m.group(1)
    parsed = _json.loads(raw.strip())
    if isinstance(parsed, dict):
        parsed = next((v for v in parsed.values() if isinstance(v, list)), [])
    return parsed


def _require_manager(org_id: int, user_key: str, db: Session) -> OrgMember:
    member = db.query(OrgMember).filter(
        OrgMember.org_id == org_id,
        OrgMember.user_key == user_key,
        OrgMember.is_manager == True,  # noqa: E712
    ).first()
    if not member:
        raise HTTPException(status_code=403, detail="Manager access required")
    return member


@router.get("/orgs/{org_id}/sops")
def list_org_sops(org_id: int, user_key: str, db: Session = Depends(get_db)):
    """List published SOPs for the org with completion flag for user_key."""
    org = db.query(Organization).filter(Organization.id == org_id).first()
    if not org:
        raise HTTPException(status_code=404, detail="Org not found")

    sops = (
        db.query(SOP)
        .filter(SOP.org_id == org_id, SOP.status == "published")
        .order_by(SOP.created_at.desc())
        .all()
    )

    completed_sop_ids: set[int] = set()
    if user_key:
        completions = db.query(SOPCompletion.sop_id).filter(
            SOPCompletion.user_key == user_key,
            SOPCompletion.sop_id.in_([s.id for s in sops]),
        ).all()
        completed_sop_ids = {c.sop_id for c in completions}

    result = []
    for s in sops:
        steps_count = db.query(SOPStep).filter(SOPStep.sop_id == s.id).count()
        result.append(SOPListItem(
            id=s.id,
            title=s.title,
            description=s.description,
            status=s.status,
            steps_count=steps_count,
            is_completed=s.id in completed_sop_ids,
        ))
    return result


@router.get("/sops/{sop_id}")
def get_sop(sop_id: int, db: Session = Depends(get_db)):
    """Get SOP with steps and quiz."""
    sop = db.query(SOP).filter(SOP.id == sop_id).first()
    if not sop:
        raise HTTPException(status_code=404, detail="SOP not found")

    steps = (
        db.query(SOPStep)
        .filter(SOPStep.sop_id == sop_id)
        .order_by(SOPStep.step_number)
        .all()
    )

    return SOPResponse(
        id=sop.id,
        title=sop.title,
        description=sop.description,
        status=sop.status,
        steps=[
            SOPStepSchema(
                step_number=st.step_number,
                title=st.title,
                content=st.content,
            )
            for st in steps
        ],
        quiz_json=sop.quiz_json,
        created_at=sop.created_at.isoformat() if sop.created_at else None,
    )


@router.post("/sops/{sop_id}/complete")
def complete_sop(
    sop_id: int,
    user_key: str,
    score: int = 0,
    max_score: int = 0,
    time_spent_sec: int = 0,
    db: Session = Depends(get_db),
):
    """Mark SOP as completed by an employee."""
    sop = db.query(SOP).filter(SOP.id == sop_id).first()
    if not sop:
        raise HTTPException(status_code=404, detail="SOP not found")

    existing = db.query(SOPCompletion).filter(
        SOPCompletion.sop_id == sop_id,
        SOPCompletion.user_key == user_key,
    ).first()

    if existing:
        existing.score = score
        existing.max_score = max_score
        existing.time_spent_sec = time_spent_sec
        existing.completed_at = func.now()
    else:
        db.add(SOPCompletion(
            sop_id=sop_id,
            user_key=user_key,
            score=score,
            max_score=max_score,
            time_spent_sec=time_spent_sec,
        ))

    db.commit()
    update_streak(user_key, db)

    return {"status": "ok", "sop_id": sop_id, "score": score, "max_score": max_score}


@router.post("/orgs/{org_id}/sops/upload-pdf")
async def upload_sop_pdf(
    org_id: int,
    file: UploadFile = File(...),
    title: str = Form(default=""),
    user_key: str = Form(default=""),
    db: Session = Depends(get_db),
):
    """Upload PDF → AI generates SOP steps + quiz questions."""
    org = db.query(Organization).filter(Organization.id == org_id).first()
    if not org:
        raise HTTPException(status_code=404, detail="Org not found")

    file_bytes = await file.read()
    try:
        pdf_text = extract_text_from_pdf(file_bytes)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to parse PDF: {e}")

    if not pdf_text.strip():
        raise HTTPException(status_code=400, detail="PDF is empty or unreadable")

    if not title:
        title = (file.filename or "СОП").rsplit(".", 1)[0]

    text_for_ai = pdf_text[:10000]

    steps_prompt = (
        f"Разбей следующий текст на 5-7 чётких пронумерованных шагов стандартной "
        f"операционной процедуры (СОП).\n\n"
        f"Текст:\n{text_for_ai}\n\n"
        f"Верни JSON-массив:\n"
        f'[{{"step_number": 1, "title": "Краткое название шага", '
        f'"content": "Подробное описание шага в 2-3 предложения"}}]'
    )

    try:
        steps_raw = await call_ai(
            steps_prompt,
            "Ты эксперт по стандартным операционным процедурам. "
            "Ответ — только валидный JSON-массив, без текста вокруг.",
            json_mode=False,
        )
        steps_data = _extract_json_list(steps_raw)
    except Exception as e:
        logger.error("AI steps generation failed: %s", e)
        raise HTTPException(status_code=503, detail="AI unavailable. Try again later.")

    steps_text = "\n".join(
        f"{s['step_number']}. {s['title']}: {s['content']}" for s in steps_data
    )
    quiz_prompt = (
        f"На основе следующих шагов СОП создай 5 тестовых вопросов на русском языке.\n\n"
        f"Шаги:\n{steps_text}\n\n"
        f"Верни JSON-массив:\n"
        f'[{{"question": "...", "options": ["A", "B", "C", "D"], '
        f'"correct_answer": "A", "explanation": "..."}}]'
    )

    try:
        quiz_raw = await call_ai(
            quiz_prompt,
            "Ты эксперт по обучению персонала. Ответ — только валидный JSON-массив.",
            json_mode=False,
        )
        quiz_data = _extract_json_list(quiz_raw)
    except Exception as e:
        logger.error("AI quiz generation failed: %s", e)
        quiz_data = []

    try:
        new_sop = SOP(
            org_id=org_id,
            title=title,
            description=f"СОП: {title}",
            status="published",
            created_by=user_key or "anonymous",
            quiz_json=quiz_data,
        )
        db.add(new_sop)
        db.flush()

        for step in steps_data:
            db.add(SOPStep(
                sop_id=new_sop.id,
                step_number=step.get("step_number", 0),
                title=step.get("title", ""),
                content=step.get("content", ""),
            ))

        db.commit()
        return {
            "status": "ok",
            "sop_id": new_sop.id,
            "steps_count": len(steps_data),
            "quiz_count": len(quiz_data),
        }

    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/orgs/{org_id}/sop-progress")
def get_sop_progress(org_id: int, user_key: str, db: Session = Depends(get_db)):
    """Manager dashboard: employee × SOP completion matrix."""
    org = db.query(Organization).filter(Organization.id == org_id).first()
    if not org:
        raise HTTPException(status_code=404, detail="Org not found")

    _require_manager(org_id, user_key, db)

    members = db.query(OrgMember).filter(OrgMember.org_id == org_id).all()
    sops = (
        db.query(SOP)
        .filter(SOP.org_id == org_id, SOP.status == "published")
        .order_by(SOP.created_at)
        .all()
    )

    completions = db.query(SOPCompletion).filter(
        SOPCompletion.sop_id.in_([s.id for s in sops]),
        SOPCompletion.user_key.in_([m.user_key for m in members]),
    ).all()

    comp_map = {(c.user_key, c.sop_id): c for c in completions}

    matrix = []
    for m in members:
        row: dict = {
            "user_key": m.user_key,
            "is_manager": m.is_manager,
            "sops": [],
        }
        for s in sops:
            comp = comp_map.get((m.user_key, s.id))
            row["sops"].append({
                "sop_id": s.id,
                "sop_title": s.title,
                "completed": comp is not None,
                "score": comp.score if comp else None,
                "max_score": comp.max_score if comp else None,
                "completed_at": (
                    comp.completed_at.isoformat() if comp and comp.completed_at else None
                ),
            })
        matrix.append(row)

    return {
        "org_name": org.name,
        "sops": [{"id": s.id, "title": s.title} for s in sops],
        "members": matrix,
    }
