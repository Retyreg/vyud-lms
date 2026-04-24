import logging
import os
from datetime import date, datetime, timedelta

from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy.orm import Session

from app.core.deps import get_db
from app.models.org import OrgMember, Organization
from app.models.sop import SOP, SOPAssignment, SOPCompletion
from app.services.telegram import send_telegram_message

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/cron", tags=["cron"])

CRON_SECRET = os.getenv("CRON_SECRET", "")


def _check_secret(x_cron_secret: str = Header(default="")) -> None:
    if not CRON_SECRET or x_cron_secret != CRON_SECRET:
        raise HTTPException(status_code=403, detail="Forbidden")


@router.post("/reminders")
def send_reminders(db: Session = Depends(get_db), _: None = Depends(_check_secret)):
    """Send 24h deadline reminders. Called by cron every hour."""
    tomorrow = date.today() + timedelta(days=1)

    pending = db.query(SOPAssignment).filter(
        SOPAssignment.deadline == tomorrow,
        SOPAssignment.reminder_sent == False,  # noqa: E712
    ).all()

    if not pending:
        return {"sent": 0}

    sop_ids = list({a.sop_id for a in pending})
    user_keys = list({a.user_key for a in pending})
    org_ids = list({a.org_id for a in pending})

    sops_map = {s.id: s for s in db.query(SOP).filter(SOP.id.in_(sop_ids)).all()}
    orgs_map = {o.id: o for o in db.query(Organization).filter(Organization.id.in_(org_ids)).all()}
    completions = {
        (c.user_key, c.sop_id)
        for c in db.query(SOPCompletion).filter(
            SOPCompletion.sop_id.in_(sop_ids),
            SOPCompletion.user_key.in_(user_keys),
        ).all()
    }

    sent = 0
    for a in pending:
        if (a.user_key, a.sop_id) in completions:
            a.reminder_sent = True
            continue

        sop = sops_map.get(a.sop_id)
        org = orgs_map.get(a.org_id)
        if not sop:
            continue

        ok = send_telegram_message(
            a.user_key,
            f"⏰ <b>Напоминание о регламенте</b>\n\n"
            f"Завтра дедлайн по регламенту <b>{sop.title}</b>.\n\n"
            f"Откройте @{org.bot_username if org else 'VyudAiBot'} и пройдите сегодня.",
        )
        if ok:
            sent += 1
        a.reminder_sent = True

    db.commit()
    logger.info("Reminders sent: %d / %d pending", sent, len(pending))
    return {"sent": sent, "total_pending": len(pending)}


@router.post("/weekly-digest")
def send_weekly_digest(db: Session = Depends(get_db), _: None = Depends(_check_secret)):
    """Send weekly completion digest to all org managers. Run every Monday."""
    week_ago = datetime.utcnow() - timedelta(days=7)
    orgs = db.query(Organization).all()
    sent = 0

    for org in orgs:
        managers = db.query(OrgMember).filter(
            OrgMember.org_id == org.id,
            OrgMember.is_manager == True,  # noqa: E712
        ).all()
        if not managers:
            continue

        members = db.query(OrgMember).filter(OrgMember.org_id == org.id).all()
        if len(members) <= 1:
            continue  # skip orgs with only manager, no employees yet

        sops = db.query(SOP).filter(SOP.org_id == org.id, SOP.status == "published").all()
        if not sops:
            continue

        sop_ids = [s.id for s in sops]
        employee_keys = [m.user_key for m in members if not m.is_manager]

        completions_week = db.query(SOPCompletion).filter(
            SOPCompletion.sop_id.in_(sop_ids),
            SOPCompletion.completed_at >= week_ago,
        ).all()
        completed_users_week = {c.user_key for c in completions_week}

        all_completions_keys = {
            c.user_key
            for c in db.query(SOPCompletion.user_key).filter(
                SOPCompletion.sop_id.in_(sop_ids),
                SOPCompletion.user_key.in_(employee_keys),
            ).all()
        }
        not_started = [k for k in employee_keys if k not in all_completions_keys]

        lines = [
            f"📊 <b>Еженедельный отчёт — {org.name}</b>",
            "",
            f"✅ Завершили за неделю: {len(completed_users_week)} из {len(employee_keys)}",
            f"🆕 Ещё не начали: {len(not_started)}",
            f"📋 Регламентов в программе: {len(sops)}",
        ]
        text = "\n".join(lines)

        for manager in managers:
            ok = send_telegram_message(manager.user_key, text)
            if ok:
                sent += 1

    logger.info("Weekly digest sent: %d managers across %d orgs", sent, len(orgs))
    return {"sent": sent, "orgs_processed": len(orgs)}
