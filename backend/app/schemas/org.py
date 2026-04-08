from pydantic import BaseModel


class OrgCreateRequest(BaseModel):
    name: str
    manager_key: str  # email или любой идентификатор менеджера


class OrgJoinRequest(BaseModel):
    user_key: str     # идентификатор сотрудника


class MemberProgress(BaseModel):
    user_key: str
    completed_count: int
    total_count: int
    percent: float


class OrgInfo(BaseModel):
    org_id: int
    org_name: str
    invite_code: str
    is_manager: bool


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
