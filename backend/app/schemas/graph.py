from pydantic import BaseModel
from typing import List


class NodeSchema(BaseModel):
    id: int
    label: str
    level: int
    is_completed: bool
    is_available: bool


class EdgeSchema(BaseModel):
    source: int
    target: int


class GraphResponse(BaseModel):
    nodes: List[NodeSchema]
    edges: List[EdgeSchema]
