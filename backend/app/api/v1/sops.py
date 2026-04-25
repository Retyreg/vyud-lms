import json as _json
import logging
import re
from datetime import date, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy.sql import func

from app.ai.client import call_ai
from app.core.deps import get_db
from app.models.org import OrgMember, Organization
from app.models.sop import SOP, SOPAssignment, SOPCertificate, SOPCompletion, SOPStep
from app.schemas.sop import SOPListItem, SOPResponse, SOPStepSchema
from app.services.pdf import extract_text_from_pdf
from app.services.streak import update_streak
from app.services.telegram import send_telegram_message

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["sops"])


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

    is_first_completion = existing is None

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

    # Issue certificate (idempotent)
    cert = db.query(SOPCertificate).filter(
        SOPCertificate.user_key == user_key,
        SOPCertificate.sop_id == sop_id,
    ).first()
    if not cert:
        cert = SOPCertificate(
            user_key=user_key,
            sop_id=sop_id,
            org_id=sop.org_id,
            score=score,
            max_score=max_score,
        )
        db.add(cert)
        db.commit()
        db.refresh(cert)

    # Notify org managers on first completion
    if is_first_completion:
        employee = db.query(OrgMember).filter(
            OrgMember.org_id == sop.org_id,
            OrgMember.user_key == user_key,
        ).first()
        employee_name = (employee.display_name if employee and employee.display_name else user_key)
        score_str = f" — {score}/{max_score}" if max_score > 0 else ""
        text = f"✅ <b>{employee_name}</b> прошёл «{sop.title}»{score_str}"
        managers = db.query(OrgMember).filter(
            OrgMember.org_id == sop.org_id,
            OrgMember.is_manager == True,  # noqa: E712
        ).all()
        for mgr in managers:
            send_telegram_message(mgr.user_key, text)

    return {"status": "ok", "sop_id": sop_id, "score": score, "max_score": max_score, "cert_token": cert.cert_token}


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

    if org.plan == "free":
        published_count = db.query(SOP).filter(
            SOP.org_id == org_id, SOP.status == "published"
        ).count()
        if published_count >= 1:
            raise HTTPException(
                status_code=403,
                detail={"code": "free_limit", "upgrade_url": "https://vyud.online/pricing"},
            )

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
            "display_name": m.display_name,
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

    employee_keys = {m.user_key for m in members if not m.is_manager}
    employee_count = len(employee_keys)

    sops_out = []
    for s in sops:
        sop_comps = [c for c in completions if c.sop_id == s.id and c.user_key in employee_keys]
        completed_count = len(sop_comps)
        avg_score: float | None = None
        avg_time: float | None = None
        if sop_comps:
            scored = [c for c in sop_comps if c.max_score and c.max_score > 0]
            if scored:
                avg_score = round(sum(c.score / c.max_score * 100 for c in scored) / len(scored), 1)
            timed = [c for c in sop_comps if c.time_spent_sec]
            if timed:
                avg_time = round(sum(c.time_spent_sec for c in timed) / len(timed))
        sops_out.append({
            "id": s.id,
            "title": s.title,
            "completed_count": completed_count,
            "employee_count": employee_count,
            "avg_score_pct": avg_score,
            "avg_time_sec": avg_time,
        })

    return {
        "org_name": org.name,
        "sops": sops_out,
        "members": matrix,
    }


# ── SOP Edit / Delete ─────────────────────────────────────────────────────


class SOPStepUpdate(BaseModel):
    step_number: int
    title: str
    content: str


class SOPUpdateRequest(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    steps: Optional[list[SOPStepUpdate]] = None


@router.patch("/sops/{sop_id}")
def update_sop(
    sop_id: int,
    user_key: str,
    body: SOPUpdateRequest,
    db: Session = Depends(get_db),
):
    """Manager edits SOP title, description, and/or steps."""
    sop = db.query(SOP).filter(SOP.id == sop_id).first()
    if not sop:
        raise HTTPException(status_code=404, detail="SOP not found")
    _require_manager(sop.org_id, user_key, db)

    if body.title is not None:
        sop.title = body.title
    if body.description is not None:
        sop.description = body.description

    if body.steps is not None:
        existing_steps = {s.step_number: s for s in db.query(SOPStep).filter(SOPStep.sop_id == sop_id).all()}
        for step_data in body.steps:
            step = existing_steps.get(step_data.step_number)
            if step:
                step.title = step_data.title
                step.content = step_data.content

    db.commit()
    return {"status": "ok", "sop_id": sop_id}


@router.delete("/sops/{sop_id}", status_code=200)
def delete_sop(sop_id: int, user_key: str, db: Session = Depends(get_db)):
    """Manager deletes a SOP and all its steps/completions."""
    sop = db.query(SOP).filter(SOP.id == sop_id).first()
    if not sop:
        raise HTTPException(status_code=404, detail="SOP not found")
    _require_manager(sop.org_id, user_key, db)
    db.delete(sop)
    db.commit()
    return {"status": "ok", "deleted_sop_id": sop_id}


# ── Certificates ──────────────────────────────────────────────────────────


@router.get("/cert/{token}")
def get_certificate(token: str, db: Session = Depends(get_db)):
    """Public endpoint — verify and display a SOP completion certificate."""
    cert = db.query(SOPCertificate).filter(SOPCertificate.cert_token == token).first()
    if not cert:
        raise HTTPException(status_code=404, detail="Certificate not found")
    sop = db.query(SOP).filter(SOP.id == cert.sop_id).first()
    org = db.query(Organization).filter(Organization.id == cert.org_id).first()
    return {
        "cert_token": cert.cert_token,
        "user_key": cert.user_key,
        "sop_title": sop.title if sop else "—",
        "org_name": org.name if org else "—",
        "score": cert.score,
        "max_score": cert.max_score,
        "issued_at": cert.issued_at.isoformat() if cert.issued_at else None,
    }


# ── User progress history ─────────────────────────────────────────────────


@router.get("/orgs/{org_id}/my-progress")
def get_my_progress(org_id: int, user_key: str, db: Session = Depends(get_db)):
    """Employee: list of SOPs with completion status and cert_token."""
    org = db.query(Organization).filter(Organization.id == org_id).first()
    if not org:
        raise HTTPException(status_code=404, detail="Org not found")

    sops = (
        db.query(SOP)
        .filter(SOP.org_id == org_id, SOP.status == "published")
        .order_by(SOP.created_at.desc())
        .all()
    )

    completions = {
        c.sop_id: c for c in db.query(SOPCompletion).filter(
            SOPCompletion.user_key == user_key,
            SOPCompletion.sop_id.in_([s.id for s in sops]),
        ).all()
    }

    certs = {
        c.sop_id: c for c in db.query(SOPCertificate).filter(
            SOPCertificate.user_key == user_key,
            SOPCertificate.sop_id.in_([s.id for s in sops]),
        ).all()
    }

    result = []
    for s in sops:
        comp = completions.get(s.id)
        cert = certs.get(s.id)
        steps_count = db.query(SOPStep).filter(SOPStep.sop_id == s.id).count()
        result.append({
            "sop_id": s.id,
            "title": s.title,
            "steps_count": steps_count,
            "completed": comp is not None,
            "score": comp.score if comp else None,
            "max_score": comp.max_score if comp else None,
            "time_spent_sec": comp.time_spent_sec if comp else None,
            "completed_at": comp.completed_at.isoformat() if comp and comp.completed_at else None,
            "cert_token": cert.cert_token if cert else None,
        })

    return {"org_name": org.name, "items": result}


# ── Assignments ────────────────────────────────────────────────────────────


class AssignmentRequest(BaseModel):
    sop_id: int
    user_key: str
    deadline: date


@router.post("/orgs/{org_id}/assignments", status_code=201)
def create_assignment(
    org_id: int,
    body: AssignmentRequest,
    user_key: str,
    db: Session = Depends(get_db),
):
    """Manager assigns a SOP to an employee with a deadline."""
    org = db.query(Organization).filter(Organization.id == org_id).first()
    if not org:
        raise HTTPException(status_code=404, detail="Org not found")
    _require_manager(org_id, user_key, db)

    sop = db.query(SOP).filter(SOP.id == body.sop_id, SOP.org_id == org_id).first()
    if not sop:
        raise HTTPException(status_code=404, detail="SOP not found in this org")

    existing = db.query(SOPAssignment).filter(
        SOPAssignment.org_id == org_id,
        SOPAssignment.sop_id == body.sop_id,
        SOPAssignment.user_key == body.user_key,
    ).first()
    if existing:
        existing.deadline = body.deadline
        existing.assigned_by = user_key
        existing.reminder_sent = False
        db.commit()
        assignment = existing
    else:
        assignment = SOPAssignment(
            org_id=org_id,
            sop_id=body.sop_id,
            user_key=body.user_key,
            assigned_by=user_key,
            deadline=body.deadline,
        )
        db.add(assignment)
        db.commit()
        db.refresh(assignment)

    # Immediate push to employee
    deadline_str = body.deadline.strftime("%d.%m.%Y")
    send_telegram_message(
        body.user_key,
        f"📋 <b>Новый регламент</b>\n\n"
        f"Вам назначен регламент <b>{sop.title}</b>.\n"
        f"Дедлайн: <b>{deadline_str}</b>\n\n"
        f"Откройте @{org.bot_username or 'VyudAiBot'} для прохождения.",
    )

    return {
        "id": assignment.id,
        "sop_id": body.sop_id,
        "sop_title": sop.title,
        "user_key": body.user_key,
        "deadline": body.deadline.isoformat(),
        "assigned_at": assignment.assigned_at.isoformat() if assignment.assigned_at else None,
    }


@router.get("/orgs/{org_id}/assignments")
def list_assignments(org_id: int, user_key: str, db: Session = Depends(get_db)):
    """Manager: all assignments for the org with completion status."""
    org = db.query(Organization).filter(Organization.id == org_id).first()
    if not org:
        raise HTTPException(status_code=404, detail="Org not found")
    _require_manager(org_id, user_key, db)

    assignments = db.query(SOPAssignment).filter(SOPAssignment.org_id == org_id).all()
    sop_ids = list({a.sop_id for a in assignments})
    user_keys = list({a.user_key for a in assignments})

    sops_map = {s.id: s for s in db.query(SOP).filter(SOP.id.in_(sop_ids)).all()} if sop_ids else {}
    completions = set()
    if sop_ids and user_keys:
        completions = {
            (c.user_key, c.sop_id)
            for c in db.query(SOPCompletion).filter(
                SOPCompletion.sop_id.in_(sop_ids),
                SOPCompletion.user_key.in_(user_keys),
            ).all()
        }

    members_map = {
        m.user_key: m.display_name
        for m in db.query(OrgMember).filter(OrgMember.org_id == org_id).all()
    }

    today = date.today()
    result = []
    for a in assignments:
        sop = sops_map.get(a.sop_id)
        overdue = a.deadline < today and (a.user_key, a.sop_id) not in completions
        result.append({
            "id": a.id,
            "sop_id": a.sop_id,
            "sop_title": sop.title if sop else "—",
            "user_key": a.user_key,
            "display_name": members_map.get(a.user_key),
            "deadline": a.deadline.isoformat(),
            "completed": (a.user_key, a.sop_id) in completions,
            "overdue": overdue,
        })
    result.sort(key=lambda x: x["deadline"])
    return result


@router.get("/orgs/{org_id}/my-assignments")
def list_my_assignments(org_id: int, user_key: str, db: Session = Depends(get_db)):
    """Employee: their own assignments with deadline info."""
    org = db.query(Organization).filter(Organization.id == org_id).first()
    if not org:
        raise HTTPException(status_code=404, detail="Org not found")

    member = db.query(OrgMember).filter(
        OrgMember.org_id == org_id,
        OrgMember.user_key == user_key,
    ).first()
    if not member:
        raise HTTPException(status_code=403, detail="Not a member of this org")

    assignments = db.query(SOPAssignment).filter(
        SOPAssignment.org_id == org_id,
        SOPAssignment.user_key == user_key,
    ).all()

    completions = {
        c.sop_id
        for c in db.query(SOPCompletion).filter(
            SOPCompletion.user_key == user_key,
            SOPCompletion.sop_id.in_([a.sop_id for a in assignments]),
        ).all()
    } if assignments else set()

    today = date.today()
    return [
        {
            "sop_id": a.sop_id,
            "deadline": a.deadline.isoformat(),
            "days_left": (a.deadline - today).days,
            "completed": a.sop_id in completions,
            "overdue": a.deadline < today and a.sop_id not in completions,
        }
        for a in assignments
    ]
