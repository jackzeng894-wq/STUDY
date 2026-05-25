"""Main API router that aggregates all v1 sub-routers."""

from fastapi import APIRouter

from app.api.auth import router as auth_router
from app.api.conversation import router as conversation_router
from app.api.evaluation import router as evaluation_router
from app.api.knowledge import router as knowledge_router
from app.api.learning import router as learning_router
from app.api.profile import router as profile_router
from app.api.resource import router as resource_router

api_router = APIRouter()

api_router.include_router(auth_router, prefix="/auth", tags=["Auth"])
api_router.include_router(
    conversation_router, prefix="/conversations", tags=["Conversations"]
)
api_router.include_router(
    evaluation_router, prefix="/evaluation", tags=["Evaluation"]
)
api_router.include_router(knowledge_router, prefix="/knowledge", tags=["Knowledge"])
api_router.include_router(
    learning_router, prefix="/learning-paths", tags=["LearningPaths"]
)
api_router.include_router(profile_router, prefix="/profiles", tags=["Profiles"])
api_router.include_router(resource_router, prefix="/resources", tags=["Resources"])
