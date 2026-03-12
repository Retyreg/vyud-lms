# Импортируем модели, чтобы они зарегистрировались в Base.metadata
from app.models.course import Course, Lesson  # noqa: F401
from app.models.knowledge import KnowledgeNode, KnowledgeEdge  # noqa: F401
from app.models.user import User, UserRole  # noqa: F401
from app.models.task import Task, TaskStatus, TaskPriority  # noqa: F401
from app.models.news import NewsPost  # noqa: F401
