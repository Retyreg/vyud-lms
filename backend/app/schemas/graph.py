from pydantic import BaseModel


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
    nodes: list[NodeSchema]
    edges: list[EdgeSchema]
