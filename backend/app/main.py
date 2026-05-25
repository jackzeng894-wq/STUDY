"""FastAPI application entry point.

Mounts all API routers, configures CORS middleware, and provides
startup/shutdown hooks for database connection management.
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.streaming.event_bus import EventBus
from app.streaming.sse_manager import SSEManager
from app.services.profile_service import ProfileService
from app.services.resource_service import ResourceService
from app.services.graph_service import GraphService
from app.services.path_service import PathService
from app.services.tutoring_service import TutoringService
from app.services.evaluation_service import EvaluationService


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown lifecycle management."""
    # Startup: verify database connection
    from app.database import engine

    async with engine.begin() as conn:
        await conn.run_sync(lambda _: None)

    # Initialize streaming infrastructure
    event_bus = EventBus()
    sse_manager = SSEManager(event_bus)
    profile_service = ProfileService(event_bus)
    graph_service = GraphService()
    resource_service = ResourceService(event_bus, graph_service)
    path_service = PathService(event_bus, graph_service)
    tutoring_service = TutoringService(event_bus)
    evaluation_service = EvaluationService(event_bus, graph_service)

    app.state.event_bus = event_bus
    app.state.sse_manager = sse_manager
    app.state.profile_service = profile_service
    app.state.graph_service = graph_service
    app.state.resource_service = resource_service
    app.state.path_service = path_service
    app.state.tutoring_service = tutoring_service
    app.state.evaluation_service = evaluation_service

    # Initialize API routers with shared services
    from app.api.conversation import init_conversation_api
    from app.api.evaluation import init_evaluation_api
    from app.api.knowledge import init_knowledge_api
    from app.api.learning import init_learning_api
    from app.api.profile import init_profile_api
    from app.api.resource import init_resource_api

    init_conversation_api(event_bus, sse_manager, profile_service, tutoring_service)
    init_evaluation_api(evaluation_service, event_bus)
    init_knowledge_api(graph_service)
    init_learning_api(path_service, event_bus)
    init_profile_api(profile_service)
    init_resource_api(resource_service, event_bus, sse_manager)

    yield

    # Shutdown: dispose engine
    await engine.dispose()


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    lifespan=lifespan,
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount API routers
from app.api.router import api_router

app.include_router(api_router, prefix="/api/v1")


@app.get("/health")
async def health_check():
    """Health check endpoint for Docker / monitoring."""
    return {"status": "ok", "version": settings.APP_VERSION}
