from fastapi import HTTPException
from app.db.base import SessionLocal


def get_db():
    if SessionLocal is None:
        raise HTTPException(status_code=503, detail="Database is not configured on this server.")
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
