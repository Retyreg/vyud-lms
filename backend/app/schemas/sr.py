from pydantic import BaseModel
from typing import Optional


class ReviewRequest(BaseModel):
    user_key: str
    quality: int  # 0-3 from 4-button UI (mapped to SM-2 q: 0→0, 1→2, 2→4, 3→5)


class CompleteRequest(BaseModel):
    user_key: str = ""


class AskRequest(BaseModel):
    question: str
    industry: Optional[str] = None  # e.g. "IT", "Продажи", "HR"
