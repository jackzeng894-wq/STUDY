"""All ORM models imported so SQLAlchemy and Alembic can discover them."""

from app.models.student import Student
from app.models.profile import StudentProfile
from app.models.conversation import Conversation, Message
from app.models.knowledge import KnowledgeNode, KnowledgeRelation
from app.models.resource import Resource
from app.models.learning import LearningPath, LearningActivity, ExerciseSubmission

__all__ = [
    "Student",
    "StudentProfile",
    "Conversation",
    "Message",
    "KnowledgeNode",
    "KnowledgeRelation",
    "Resource",
    "LearningPath",
    "LearningActivity",
    "ExerciseSubmission",
]
