import asyncio
import logging
import math
import secrets
from collections import defaultdict
from typing import List

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.ai.client import call_ai
from app.api.v1.courses import _build_graph_response, _parse_ai_nodes, _persist_course
from app.core.deps import get_db
from app.models.course import Course
from app.models.document import DocumentChunk
from app.models.knowledge import KnowledgeEdge, KnowledgeNode, NodeSRProgress
from app.models.org import OrgMember, Organization
from app.models.streak import UserStreak
from app.schemas.graph import CourseGenerationRequest, GraphResponse
from app.schemas.org import MemberProgress, OrgCreateRequest, OrgInfo, OrgJoinRequest, ROIResponse, WeekActivity
from app.services.pdf import build_graph_from_pdf, chunk_text, embed_chunks, extract_text_from_pdf
from app.services.sm2 import is_due

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["orgs"])


def _require_manager(org_id: int, user_key: str, db: Session) -> OrgMember:
    """Raise 403 if user_key is not a manager of org_id."""
    member = db.query(OrgMember).filter(
        OrgMember.org_id == org_id,
        OrgMember.user_key == user_key,
        OrgMember.is_manager == True,  # noqa: E712
    ).first()
    if not member:
        raise HTTPException(status_code=403, detail="Manager access required")
    return member


def _latest_course_for_org(org_id: int, db: Session) -> Course | None:
    """Return latest course for org, falling back to global (org_id=None) courses."""
    course = (
        db.query(Course)
        .filter(Course.org_id == org_id)
        .order_by(Course.id.desc())
        .first()
    )
    if not course:
        course = (
            db.query(Course)
            .filter(Course.org_id == None)  # noqa: E711
            .order_by(Course.id.desc())
            .first()
        )
    return course


@router.post("/orgs")
def create_org(request: OrgCreateRequest, db: Session = Depends(get_db)):
    """Manager creates an org and gets an invite link."""
    org = Organization(name=request.name)
    db.add(org)
    db.flush()
    db.add(OrgMember(org_id=org.id, user_key=request.manager_key, is_manager=True))
    db.commit()
    db.refresh(org)
    return {
        "org_id": org.id,
        "org_name": org.name,
        "invite_code": org.invite_code,
        "invite_url": f"?invite={org.invite_code}",
    }


@router.post("/orgs/join")
def join_org(invite_code: str, request: OrgJoinRequest, db: Session = Depends(get_db)):
    """Employee joins an org by invite code."""
    org = db.query(Organization).filter(Organization.invite_code == invite_code).first()
    if not org:
        raise HTTPException(status_code=404, detail="Invite code not found")
    existing = db.query(OrgMember).filter(
        OrgMember.org_id == org.id,
        OrgMember.user_key == request.user_key,
    ).first()
    if existing:
        return {"org_id": org.id, "org_name": org.name, "already_member": True}
    db.add(OrgMember(org_id=org.id, user_key=request.user_key, is_manager=False))
    db.commit()
    return {"org_id": org.id, "org_name": org.name, "already_member": False}


@router.get("/users/{user_key}/orgs", response_model=List[OrgInfo])
def get_user_orgs(user_key: str, db: Session = Depends(get_db)):
    """List orgs the user belongs to."""
    memberships = db.query(OrgMember).filter(OrgMember.user_key == user_key).all()
    result = []
    for m in memberships:
        org = db.query(Organization).filter(Organization.id == m.org_id).first()
        if org:
            result.append(OrgInfo(
                org_id=org.id,
                org_name=org.name,
                invite_code=org.invite_code,
                is_manager=m.is_manager,
            ))
    return result


@router.get("/orgs/{org_id}", response_model=OrgInfo)
def get_org(org_id: int, user_key: str, db: Session = Depends(get_db)):
    """Org info. Only accessible to members."""
    org = db.query(Organization).filter(Organization.id == org_id).first()
    if not org:
        raise HTTPException(status_code=404, detail="Org not found")
    member = db.query(OrgMember).filter(
        OrgMember.org_id == org_id,
        OrgMember.user_key == user_key,
    ).first()
    if not member:
        raise HTTPException(status_code=403, detail="Not a member of this org")
    return OrgInfo(
        org_id=org.id,
        org_name=org.name,
        invite_code=org.invite_code,
        is_manager=member.is_manager,
    )


@router.delete("/orgs/{org_id}/members/{member_key}", status_code=200)
def remove_org_member(org_id: int, member_key: str, user_key: str, db: Session = Depends(get_db)):
    """Manager removes a member from the org."""
    _require_manager(org_id, user_key, db)
    if member_key == user_key:
        raise HTTPException(status_code=400, detail="Cannot remove yourself")
    member = db.query(OrgMember).filter(
        OrgMember.org_id == org_id,
        OrgMember.user_key == member_key,
    ).first()
    if not member:
        raise HTTPException(status_code=404, detail="Member not found")
    db.delete(member)
    db.commit()
    return {"removed": member_key}


@router.post("/orgs/{org_id}/invite/regenerate")
def regenerate_invite(org_id: int, user_key: str, db: Session = Depends(get_db)):
    """Manager resets the invite code (old one stops working)."""
    _require_manager(org_id, user_key, db)
    org = db.query(Organization).filter(Organization.id == org_id).first()
    if not org:
        raise HTTPException(status_code=404, detail="Org not found")
    org.invite_code = secrets.token_urlsafe(8)
    db.commit()
    return {"invite_code": org.invite_code, "invite_url": f"?invite={org.invite_code}"}


@router.get("/orgs/{org_id}/courses/latest", response_model=GraphResponse)
def get_org_latest_course(org_id: int, user_key: str | None = None, db: Session = Depends(get_db)):
    """Graph of the latest org course."""
    org = db.query(Organization).filter(Organization.id == org_id).first()
    if not org:
        raise HTTPException(status_code=404, detail="Org not found")
    course = _latest_course_for_org(org_id, db)
    if not course:
        return {"nodes": [], "edges": []}
    return _build_graph_response(course, db, user_key=user_key)


@router.get("/orgs/{org_id}/progress")
def get_org_progress(org_id: int, user_key: str, db: Session = Depends(get_db)):
    """Manager dashboard: progress of each team member."""
    org = db.query(Organization).filter(Organization.id == org_id).first()
    if not org:
        raise HTTPException(status_code=404, detail="Org not found")
    _require_manager(org_id, user_key, db)

    members = db.query(OrgMember).filter(OrgMember.org_id == org_id).all()
    member_keys = [m.user_key for m in members]
    course = _latest_course_for_org(org_id, db)

    total = 0
    node_ids: list[int] = []
    if course:
        all_nodes = db.query(KnowledgeNode).filter(KnowledgeNode.course_id == course.id).all()
        total = len(all_nodes)
        node_ids = [n.id for n in all_nodes]

    # Per-user SM-2 progress in one query
    sr_all = []
    if member_keys and node_ids:
        sr_all = db.query(NodeSRProgress).filter(
            NodeSRProgress.user_key.in_(member_keys),
            NodeSRProgress.node_id.in_(node_ids),
        ).all()

    from app.services.sm2 import mastery_pct as _mastery_pct
    streaks = db.query(UserStreak).filter(UserStreak.user_key.in_(member_keys)).all() if member_keys else []
    streak_map = {s.user_key: s.current_streak for s in streaks}

    result = []
    for m in members:
        user_sr = [r for r in sr_all if r.user_key == m.user_key]
        reviewed = len({r.node_id for r in user_sr})
        pct = round(reviewed / total * 100, 1) if total > 0 else 0.0
        avg_mastery = (
            round(sum(_mastery_pct(r.repetitions, r.easiness_factor) for r in user_sr) / len(user_sr))
            if user_sr else 0
        )
        result.append(MemberProgress(
            user_key=m.user_key,
            completed_count=reviewed,
            total_count=total,
            percent=pct,
            avg_mastery_pct=avg_mastery,
            current_streak=streak_map.get(m.user_key, 0),
        ))

    result.sort(key=lambda x: x.percent, reverse=True)
    return {
        "org_name": org.name,
        "invite_code": org.invite_code,
        "members": result,
    }


@router.post("/orgs/{org_id}/courses/generate")
async def generate_org_course(
    org_id: int,
    request: CourseGenerationRequest,
    user_key: str,
    db: Session = Depends(get_db),
):
    """Generate a course tied to an org."""
    org = db.query(Organization).filter(Organization.id == org_id).first()
    if not org:
        raise HTTPException(status_code=404, detail="Org not found")
    _require_manager(org_id, user_key, db)

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
        _persist_course(request.topic, org_id, nodes_data, db)
        return {"status": "ok", "message": "Success"}
    except RuntimeError:
        db.rollback()
        raise HTTPException(status_code=503, detail="AI providers unavailable. Try again later.")
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/orgs/{org_id}/courses/upload-pdf")
async def upload_pdf(
    org_id: int,
    file: UploadFile = File(...),
    topic: str = Form(default=""),
    db: Session = Depends(get_db),
):
    """Generate knowledge graph from uploaded PDF file."""
    org = db.query(Organization).filter(Organization.id == org_id).first()
    if not org:
        raise HTTPException(status_code=404, detail="Org not found")

    file_bytes = await file.read()

    try:
        pdf_text = extract_text_from_pdf(file_bytes)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to parse PDF: {e}")

    if not pdf_text.strip():
        raise HTTPException(status_code=400, detail="PDF is empty or contains no extractable text")

    if not topic:
        topic = pdf_text[:100].strip()

    chunks = chunk_text(pdf_text)

    try:
        embeddings = await asyncio.wait_for(embed_chunks(chunks), timeout=15.0)
    except Exception as e:
        logger.error("Embedding skipped: %s", e)
        embeddings = [None] * len(chunks)

    try:
        nodes_data = await build_graph_from_pdf(chunks, topic, call_ai, embeddings=embeddings)
    except RuntimeError:
        raise HTTPException(status_code=503, detail="AI providers unavailable. Try again later.")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    try:
        new_course = Course(title=topic, description=f"Курс: {topic}", org_id=org_id)
        db.add(new_course)
        db.flush()

        title_to_id: dict[str, int] = {}
        created_nodes = []
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

        for idx, (chunk, embedding) in enumerate(zip(chunks, embeddings)):
            db.add(DocumentChunk(
                course_id=new_course.id,
                chunk_text=chunk,
                chunk_index=idx,
                embedding=embedding,
            ))

        db.commit()
        return {"status": "ok", "course_id": new_course.id, "node_count": len(created_nodes)}

    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/orgs/{org_id}/due-nodes")
def get_due_nodes(org_id: int, user_key: str, db: Session = Depends(get_db)):
    """Return IDs of nodes due for review today for this user."""
    org = db.query(Organization).filter(Organization.id == org_id).first()
    if not org:
        raise HTTPException(status_code=404, detail="Org not found")

    course = _latest_course_for_org(org_id, db)
    if not course:
        return {"due_node_ids": []}

    nodes = db.query(KnowledgeNode).filter(KnowledgeNode.course_id == course.id).all()
    node_ids = [n.id for n in nodes]

    sr_records = db.query(NodeSRProgress).filter(
        NodeSRProgress.node_id.in_(node_ids),
        NodeSRProgress.user_key == user_key,
    ).all()

    reviewed_ids = {r.node_id for r in sr_records if not is_due(r.next_review)}
    due_ids = [nid for nid in node_ids if nid not in reviewed_ids]

    return {"due_node_ids": due_ids}


@router.get("/orgs/{org_id}/roi", response_model=ROIResponse)
def get_org_roi(org_id: int, db: Session = Depends(get_db)):
    """ROI metrics for manager/CXO."""
    org = db.query(Organization).filter(Organization.id == org_id).first()
    if not org:
        raise HTTPException(status_code=404, detail="Org not found")

    members = db.query(OrgMember).filter(OrgMember.org_id == org_id).all()
    total_members = len(members)
    member_keys = [m.user_key for m in members]
    member_joined = {m.user_key: m.joined_at for m in members}

    course = _latest_course_for_org(org_id, db)

    total_nodes = 0
    node_ids: list[int] = []
    if course:
        nodes = db.query(KnowledgeNode).filter(KnowledgeNode.course_id == course.id).all()
        total_nodes = len(nodes)
        node_ids = [n.id for n in nodes]

    sr_records = []
    if member_keys and node_ids:
        sr_records = db.query(NodeSRProgress).filter(
            NodeSRProgress.user_key.in_(member_keys),
            NodeSRProgress.node_id.in_(node_ids),
        ).all()

    active_keys = {r.user_key for r in sr_records}
    active_members = len(active_keys)

    reviewed_per_user: dict[str, set[int]] = defaultdict(set)
    for r in sr_records:
        reviewed_per_user[r.user_key].add(r.node_id)

    if total_nodes > 0 and member_keys:
        rates = [len(reviewed_per_user[k]) / total_nodes * 100 for k in member_keys]
        avg_completion_rate = round(sum(rates) / len(rates), 1)
    else:
        avg_completion_rate = 0.0

    total_reviews = sum(r.total_reviews for r in sr_records)

    days_list: list[float] = []
    for key in member_keys:
        user_sr = [r for r in sr_records if r.user_key == key and r.last_reviewed is not None]
        if user_sr:
            first_review = min(r.last_reviewed for r in user_sr)  # type: ignore[type-var]
            joined = member_joined.get(key)
            if joined and first_review:
                delta = (first_review - joined).total_seconds() / 86400
                if delta >= 0:
                    days_list.append(delta)
    avg_days_to_first_completion = (
        round(sum(days_list) / len(days_list), 1) if days_list else None
    )

    fastest_member: str | None = None
    if reviewed_per_user:
        fastest_member = max(reviewed_per_user, key=lambda k: len(reviewed_per_user[k]))

    streaks = (
        db.query(UserStreak).filter(UserStreak.user_key.in_(member_keys)).all()
        if member_keys else []
    )
    streak_map = {s.user_key: s.current_streak for s in streaks}
    avg_streak = (
        round(sum(streak_map.get(k, 0) for k in member_keys) / len(member_keys), 1)
        if member_keys else 0.0
    )

    raw_score = avg_completion_rate * (1 + math.log(total_reviews + 1) / 10)
    onboarding_efficiency_score = round(min(100.0, max(0.0, raw_score)), 1)

    completion_int = round(avg_completion_rate)
    if avg_completion_rate >= 80:
        summary = f"Команда освоила курс на {completion_int}%. Онбординг прошёл успешно."
    elif avg_completion_rate >= 50:
        summary = (
            f"Команда на полпути — {completion_int}% завершено. "
            f"{active_members} из {total_members} участников активны."
        )
    else:
        summary = (
            f"Онбординг в процессе. {active_members} из {total_members} "
            f"участников начали обучение."
        )

    # Weekly activity — count reviews per week for last 5 weeks
    from datetime import date, timedelta
    MONTHS_RU = ["янв","фев","мар","апр","май","июн","июл","авг","сен","окт","ноя","дек"]
    today = date.today()
    weekly_activity: list[WeekActivity] = []
    for weeks_back in range(4, -1, -1):
        week_start = today - timedelta(days=today.weekday() + weeks_back * 7)
        week_end = week_start + timedelta(days=6)
        count = sum(
            1 for r in sr_records
            if r.last_reviewed is not None
            and week_start <= r.last_reviewed.date() <= week_end
        )
        label = f"{week_start.day} {MONTHS_RU[week_start.month - 1]}"
        weekly_activity.append(WeekActivity(week_label=label, reviews=count))

    return ROIResponse(
        org_name=org.name,
        total_members=total_members,
        active_members=active_members,
        total_nodes=total_nodes,
        avg_completion_rate=avg_completion_rate,
        avg_days_to_first_completion=avg_days_to_first_completion,
        fastest_member=fastest_member,
        total_reviews=total_reviews,
        avg_streak=avg_streak,
        onboarding_efficiency_score=onboarding_efficiency_score,
        summary=summary,
        weekly_activity=weekly_activity,
    )
