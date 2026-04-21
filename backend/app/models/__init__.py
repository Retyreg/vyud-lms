# Импортируем модели, чтобы они зарегистрировались в Base.metadata
from app.models.course import Course, Lesson  # noqa: F401
from app.models.document import DocumentChunk  # noqa: F401
from app.models.knowledge import KnowledgeEdge, KnowledgeNode, NodeExplanation, NodeSRProgress  # noqa: F401
from app.models.org import OrgMember, Organization  # noqa: F401
from app.models.sop import SOP, SOPCompletion, SOPStep  # noqa: F401
from app.models.streak import UserStreak  # noqa: F401
from app.models.template import SOPTemplate  # noqa: F401
from app.models.demo import DemoUser, DemoFeedback  # noqa: F401
