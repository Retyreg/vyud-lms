from pydantic import BaseModel


class CourseGenerationRequest(BaseModel):
    topic: str
