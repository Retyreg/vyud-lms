from pydantic import BaseModel
from typing import List


class NodeSchema(BaseModel):
    id: int
    label: str
    level: int
    is_completed: bool
    is_available: bool
    mastery_pct: int = 0          # 0-100, based on SM-2 repetitions
    next_review: str | None = None  # ISO datetime or None


class EdgeSchema(BaseModel):
    source: int
    target: int


class GraphResponse(BaseModel):
    nodes: List[NodeSchema]
    edges: List[EdgeSchema]


class CourseGenerationRequest(BaseModel):
    topic: str
