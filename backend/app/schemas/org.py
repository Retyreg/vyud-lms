from pydantic import BaseModel
from typing import List, Optional


class OrgCreateRequest(BaseModel):
    name: str
    manager_key: str


class OrgJoinRequest(BaseModel):
    user_key: str


class OrgInfo(BaseModel):
    org_id: int
    org_name: str
    invite_code: str
    is_manager: bool


class MemberProgress(BaseModel):
    user_key: str
    completed_count: int
    total_count: int
    percent: float
    avg_mastery_pct: int = 0      # average SM-2 mastery across reviewed nodes
    current_streak: int = 0


class WeekActivity(BaseModel):
    week_label: str   # e.g. "15 апр"
    reviews: int


class OrgBrand(BaseModel):
    brand_color: Optional[str] = None
    logo_url: Optional[str] = None
    bot_username: Optional[str] = None
    display_name: Optional[str] = None


class OrgBrandUpdate(BaseModel):
    brand_color: Optional[str] = None
    logo_url: Optional[str] = None
    bot_username: Optional[str] = None
    display_name: Optional[str] = None


class ROIResponse(BaseModel):
    org_name: str
    total_members: int
    active_members: int
    total_nodes: int
    avg_completion_rate: float
    avg_days_to_first_completion: float | None
    fastest_member: str | None
    total_reviews: int
    avg_streak: float
    onboarding_efficiency_score: float
    summary: str
    weekly_activity: list[WeekActivity] = []
