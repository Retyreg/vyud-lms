# Импортируем модели, чтобы они зарегистрировались в Base.metadata
from app.models.course import Course, Lesson
from app.models.knowledge import KnowledgeNode, KnowledgeEdge, NodeExplanation, NodeSRProgress
from app.models.org import Organization, OrgMember
from app.models.document import DocumentChunk
from app.models.streak import UserStreak
from app.models.sop import SOP, SOPStep, SOPCompletion
