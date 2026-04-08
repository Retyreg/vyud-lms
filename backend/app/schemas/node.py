from pydantic import BaseModel


class CompleteRequest(BaseModel):
    user_key: str = ""


class ReviewRequest(BaseModel):
    user_key: str
    quality: int  # 0-3 from 4-button UI (mapped to SM-2 q: 0→0, 1→2, 2→4, 3→5)
