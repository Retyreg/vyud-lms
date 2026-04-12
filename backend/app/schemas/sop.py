from pydantic import BaseModel


class SOPCreateRequest(BaseModel):
    title: str
    description: str = ""


class SOPStepSchema(BaseModel):
    step_number: int
    title: str
    content: str


class SOPResponse(BaseModel):
    id: int
    title: str
    description: str | None
    status: str
    steps: list[SOPStepSchema]
    quiz_json: list | None
    created_at: str | None


class SOPListItem(BaseModel):
    id: int
    title: str
    description: str | None
    status: str
    steps_count: int
    is_completed: bool


class SOPCompletionRecord(BaseModel):
    user_key: str
    sop_id: int
    sop_title: str
    score: int | None
    max_score: int | None
    completed_at: str | None
