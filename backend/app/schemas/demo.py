from pydantic import BaseModel, field_validator


class DemoRegisterRequest(BaseModel):
    full_name: str
    email: str
    company: str
    role: str       # Manager / L&D / Owner / Other
    industry: str   # HoReCa / Retail / FMCG / Other

    @field_validator("role")
    @classmethod
    def validate_role(cls, v: str) -> str:
        allowed = {"Manager", "L&D", "Owner", "Other"}
        if v not in allowed:
            raise ValueError(f"role must be one of {allowed}")
        return v

    @field_validator("industry")
    @classmethod
    def validate_industry(cls, v: str) -> str:
        allowed = {"HoReCa", "Retail", "FMCG", "Other"}
        if v not in allowed:
            raise ValueError(f"industry must be one of {allowed}")
        return v


class DemoRegisterResponse(BaseModel):
    magic_link: str
    show_on_screen: bool  # True when SMTP not configured


class DemoAuthResponse(BaseModel):
    session_token: str
    demo_user_id: str
    demo_course_id: int | None
    full_name: str
    expires_at: str


class DemoFeedbackRequest(BaseModel):
    rating: int
    message: str | None = None
    wants_pilot: bool = False

    @field_validator("rating")
    @classmethod
    def validate_rating(cls, v: int) -> int:
        if not 1 <= v <= 5:
            raise ValueError("rating must be 1-5")
        return v
