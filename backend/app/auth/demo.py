import logging
from datetime import datetime, timezone

from fastapi import Depends, Header, HTTPException
from sqlalchemy.orm import Session

from app.core.deps import get_db
from app.models.demo import DemoUser

logger = logging.getLogger(__name__)


def get_demo_user(
    x_demo_token: str = Header(default=""),
    db: Session = Depends(get_db),
) -> DemoUser:
    if not x_demo_token:
        raise HTTPException(status_code=401, detail="X-Demo-Token header required")

    user = db.query(DemoUser).filter(DemoUser.magic_token == x_demo_token).first()
    if not user:
        raise HTTPException(status_code=401, detail="Invalid demo token")

    if user.archived_at is not None:
        raise HTTPException(status_code=403, detail="Demo session has been archived")

    now = datetime.now(timezone.utc)
    if user.session_expires_at.replace(tzinfo=timezone.utc) < now:
        raise HTTPException(status_code=401, detail="Demo session expired — use your magic link to renew")

    return user
