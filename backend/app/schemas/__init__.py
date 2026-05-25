"""Pydantic schemas for API request/response validation."""

from app.schemas.auth import (
    StudentRegister,
    StudentLogin,
    TokenResponse,
    StudentResponse,
)
from app.schemas.conversation import (
    ConversationCreate,
    ConversationResponse,
    ConversationWithMessages,
    MessageCreate,
    MessageResponse,
)
from app.schemas.profile import (
    StudentProfileResponse,
    ProfileDimensionResponse,
    ProfileUpdateRequest,
)
from app.schemas.resource import (
    ResourceGenerateRequest,
    ResourceGenerateResponse,
    ResourceListResponse,
    ResourceResponse,
)
from app.schemas.knowledge import (
    KnowledgeGraphResponse,
    KnowledgeNodeDetail,
    KnowledgeNodeResponse,
    KnowledgeSearchRequest,
    KnowledgeSearchResponse,
    KnowledgeSearchResult,
    KnowledgeTreeResponse,
)

__all__ = [
    "StudentRegister",
    "StudentLogin",
    "TokenResponse",
    "StudentResponse",
    "ConversationCreate",
    "ConversationResponse",
    "ConversationWithMessages",
    "MessageCreate",
    "MessageResponse",
    "StudentProfileResponse",
    "ProfileDimensionResponse",
    "ProfileUpdateRequest",
    "ResourceGenerateRequest",
    "ResourceGenerateResponse",
    "ResourceListResponse",
    "ResourceResponse",
    "KnowledgeTreeResponse",
    "KnowledgeGraphResponse",
    "KnowledgeNodeResponse",
    "KnowledgeNodeDetail",
    "KnowledgeSearchRequest",
    "KnowledgeSearchResponse",
    "KnowledgeSearchResult",
]
