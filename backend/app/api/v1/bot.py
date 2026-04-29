import logging
import os

import httpx
from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.core.deps import get_db
from app.models.org import OrgMember
from app.models.sop import SOP, SOPAssignment, SOPCertificate, SOPCompletion
from app.services.telegram import BOT_TOKEN, BOT_USERNAME, send_telegram_message

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/bot", tags=["bot"])

TMA_URL = f"https://t.me/{BOT_USERNAME}/app"

CRON_SECRET = os.getenv("CRON_SECRET", "")


def _set_commands():
    """Register bot command list with Telegram BotFather."""
    if not BOT_TOKEN:
        return
    commands = [
        {"command": "start",  "description": "Открыть VYUD Frontline"},
        {"command": "mysops", "description": "Мои регламенты и прогресс"},
        {"command": "stats",  "description": "Статистика команды (для менеджера)"},
        {"command": "cert",   "description": "Мои сертификаты"},
        {"command": "help",   "description": "Список команд"},
    ]
    httpx.post(
        f"https://api.telegram.org/bot{BOT_TOKEN}/setMyCommands",
        json={"commands": commands},
        timeout=5,
    )


@router.post("/set-webhook")
def set_webhook(secret: str, base_url: str):
    """One-time setup: register webhook URL with Telegram."""
    if secret != CRON_SECRET:
        from fastapi import HTTPException
        raise HTTPException(status_code=403, detail="Forbidden")
    webhook_url = f"{base_url}/api/bot/webhook"
    r = httpx.post(
        f"https://api.telegram.org/bot{BOT_TOKEN}/setWebhook",
        json={"url": webhook_url},
        timeout=10,
    )
    _set_commands()
    return r.json()


@router.post("/webhook")
async def telegram_webhook(request: Request, db: Session = Depends(get_db)):
    """Receive updates from Telegram Bot API."""
    try:
        update = await request.json()
    except Exception:
        return {"ok": True}

    message = update.get("message") or update.get("edited_message")
    if not message:
        return {"ok": True}

    chat_id = str(message.get("chat", {}).get("id", ""))
    text = (message.get("text") or "").strip()
    user_key = chat_id  # telegram_id == user_key

    if not text.startswith("/"):
        return {"ok": True}

    command = text.split()[0].lower().replace(f"@{BOT_USERNAME.lower()}", "")

    if command == "/start":
        _handle_start(user_key, db)
    elif command == "/mysops":
        _handle_mysops(user_key, db)
    elif command == "/stats":
        _handle_stats(user_key, db)
    elif command == "/cert":
        _handle_cert(user_key, db)
    elif command == "/help":
        _handle_help(user_key)

    return {"ok": True}


# ── Command handlers ──────────────────────────────────────────────────────


def _handle_start(user_key: str, db: Session):
    membership = db.query(OrgMember).filter(OrgMember.user_key == user_key).first()
    if membership:
        org_name = db.query(OrgMember).filter(OrgMember.user_key == user_key).first()
        send_telegram_message(user_key,
            f"👋 С возвращением!\n\n"
            f"Открывай регламенты прямо здесь:\n"
            f"<a href='{TMA_URL}'>📱 VYUD Frontline</a>\n\n"
            f"Команды: /mysops · /cert · /help"
        )
    else:
        send_telegram_message(user_key,
            f"👋 Добро пожаловать в VYUD Frontline!\n\n"
            f"Здесь вы проходите регламенты вашей компании.\n\n"
            f"<a href='{TMA_URL}'>📱 Открыть приложение</a>"
        )


def _handle_mysops(user_key: str, db: Session):
    memberships = db.query(OrgMember).filter(OrgMember.user_key == user_key).all()
    if not memberships:
        send_telegram_message(user_key,
            "❌ Вы не состоите ни в одной организации.\n"
            f"Попросите менеджера прислать ссылку-приглашение."
        )
        return

    lines = ["📋 <b>Ваши регламенты:</b>\n"]
    for m in memberships:
        sops = db.query(SOP).filter(SOP.org_id == m.org_id, SOP.status == "published").order_by(SOP.created_at).all()
        if not sops:
            continue
        completions = {
            c.sop_id for c in db.query(SOPCompletion).filter(
                SOPCompletion.user_key == user_key,
                SOPCompletion.sop_id.in_([s.id for s in sops]),
            ).all()
        }
        for s in sops:
            icon = "✅" if s.id in completions else "⏳"
            lines.append(f"{icon} {s.title}")

    if len(lines) == 1:
        send_telegram_message(user_key, "📋 Регламентов пока нет.")
        return

    lines.append(f"\n<a href='{TMA_URL}'>Открыть приложение →</a>")
    send_telegram_message(user_key, "\n".join(lines))


def _handle_stats(user_key: str, db: Session):
    memberships = db.query(OrgMember).filter(
        OrgMember.user_key == user_key,
        OrgMember.is_manager == True,  # noqa: E712
    ).all()
    if not memberships:
        send_telegram_message(user_key, "❌ Команда /stats доступна только менеджерам.")
        return

    lines = ["📊 <b>Статистика команды:</b>\n"]
    for m in memberships:
        from sqlalchemy import func as sqlfunc
        from app.models.org import Organization
        org = db.query(Organization).filter(Organization.id == m.org_id).first()
        if not org:
            continue

        total_members = db.query(OrgMember).filter(
            OrgMember.org_id == m.org_id,
            OrgMember.is_manager == False,  # noqa: E712
        ).count()

        sops = db.query(SOP).filter(SOP.org_id == m.org_id, SOP.status == "published").all()
        total_completions = db.query(SOPCompletion).filter(
            SOPCompletion.sop_id.in_([s.id for s in sops])
        ).count()

        lines.append(f"🏢 <b>{org.name}</b>")
        lines.append(f"   👥 Сотрудников: {total_members}")
        lines.append(f"   📋 Регламентов: {len(sops)}")
        lines.append(f"   ✅ Прохождений: {total_completions}")

    lines.append(f"\n<a href='{TMA_URL}'>Открыть дашборд →</a>")
    send_telegram_message(user_key, "\n".join(lines))


def _handle_cert(user_key: str, db: Session):
    certs = db.query(SOPCertificate).filter(
        SOPCertificate.user_key == user_key,
    ).order_by(SOPCertificate.issued_at.desc()).limit(5).all()

    if not certs:
        send_telegram_message(user_key,
            "🏆 У вас пока нет сертификатов.\n"
            f"Пройдите регламент в <a href='{TMA_URL}'>приложении</a>."
        )
        return

    lines = ["🏆 <b>Ваши сертификаты:</b>\n"]
    for cert in certs:
        sop = db.query(SOP).filter(SOP.id == cert.sop_id).first()
        title = sop.title if sop else "—"
        issued = cert.issued_at.strftime("%d.%m.%Y") if cert.issued_at else "—"
        score_str = f" · {cert.score}/{cert.max_score}" if cert.max_score else ""
        lines.append(
            f"📜 <b>{title}</b>{score_str}\n"
            f"   Выдан: {issued}\n"
            f"   <a href='https://lms.vyud.online/cert/{cert.cert_token}'>Открыть сертификат</a>"
        )
    send_telegram_message(user_key, "\n\n".join(lines))


def _handle_help(user_key: str):
    send_telegram_message(user_key,
        "ℹ️ <b>Команды VYUD Frontline:</b>\n\n"
        "/mysops — мои регламенты и статус\n"
        "/cert — мои сертификаты\n"
        "/stats — статистика команды (менеджер)\n"
        f"/start — открыть приложение\n\n"
        f"<a href='{TMA_URL}'>📱 Открыть VYUD Frontline</a>"
    )
