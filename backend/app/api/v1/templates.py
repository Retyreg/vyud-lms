from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.deps import get_db
from app.models.org import OrgMember, Organization
from app.models.sop import SOP, SOPStep
from app.models.template import SOPTemplate

router = APIRouter(prefix="/api", tags=["templates"])


@router.get("/templates")
def list_templates(db: Session = Depends(get_db)):
    """List all SOP templates grouped by category."""
    templates = db.query(SOPTemplate).order_by(SOPTemplate.category, SOPTemplate.id).all()
    return [
        {
            "id": t.id,
            "title": t.title,
            "description": t.description,
            "category": t.category,
            "steps_count": len(t.steps) if t.steps else 0,
            "quiz_count": len(t.quiz_json) if t.quiz_json else 0,
        }
        for t in templates
    ]


@router.post("/orgs/{org_id}/templates/{template_id}/clone")
def clone_template(
    org_id: int,
    template_id: int,
    user_key: str,
    db: Session = Depends(get_db),
):
    """Clone a template into the org as a published SOP. Manager only."""
    org = db.query(Organization).filter(Organization.id == org_id).first()
    if not org:
        raise HTTPException(status_code=404, detail="Org not found")

    member = db.query(OrgMember).filter(
        OrgMember.org_id == org_id,
        OrgMember.user_key == user_key,
        OrgMember.is_manager == True,  # noqa: E712
    ).first()
    if not member:
        raise HTTPException(status_code=403, detail="Manager access required")

    if org.plan == "free":
        published_count = db.query(SOP).filter(
            SOP.org_id == org_id, SOP.status == "published"
        ).count()
        if published_count >= 1:
            raise HTTPException(
                status_code=403,
                detail={"code": "free_limit", "upgrade_url": "https://vyud.online/pricing"},
            )

    template = db.query(SOPTemplate).filter(SOPTemplate.id == template_id).first()
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")

    sop = SOP(
        org_id=org_id,
        title=template.title,
        description=template.description,
        status="published",
        created_by=user_key,
        quiz_json=template.quiz_json,
    )
    db.add(sop)
    db.flush()

    for step in (template.steps or []):
        db.add(SOPStep(
            sop_id=sop.id,
            step_number=step["step_number"],
            title=step["title"],
            content=step["content"],
        ))

    db.commit()
    return {
        "status": "ok",
        "sop_id": sop.id,
        "title": sop.title,
        "steps_count": len(template.steps or []),
    }
