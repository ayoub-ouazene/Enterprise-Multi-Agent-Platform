from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Annotated, Literal

from fastapi import Depends, FastAPI, Response, status
from pydantic import BaseModel

from app.assistant.router import router as assistant_router
from app.auth.router import router as auth_router
from app.core.config import Settings, get_settings, validate_auth_configuration
from app.database.health import get_database_health
from app.database import models as database_models
from app.database.session import create_database_engine, create_session_factory
from app.failures.router import router as failures_router
from app.notifications.router import router as notifications_router
from app.requests.router import router as requests_router
from app.workflow.router import router as workflow_router


_ = database_models


class HealthResponse(BaseModel):
    status: Literal["ok", "degraded"]
    application: Literal["ok"]
    database: Literal["ok", "unavailable"]


def create_app(settings_override: Settings | None = None) -> FastAPI:
    @asynccontextmanager
    async def lifespan(application: FastAPI) -> AsyncIterator[None]:
        settings = settings_override or get_settings()
        validate_auth_configuration(settings)
        engine = create_database_engine(settings)

        application.title = settings.app_name
        application.state.settings = settings
        application.state.engine = engine
        application.state.session_factory = create_session_factory(engine)

        try:
            yield
        finally:
            await engine.dispose()

    application = FastAPI(
        title="Enterprise Multi-Agent Platform",
        lifespan=lifespan,
    )
    application.include_router(auth_router)
    application.include_router(assistant_router)
    application.include_router(requests_router)
    application.include_router(workflow_router)
    application.include_router(notifications_router)
    application.include_router(failures_router)

    @application.get("/health", response_model=HealthResponse)
    async def health(
        response: Response,
        database_healthy: Annotated[bool, Depends(get_database_health)],
    ) -> HealthResponse:
        if not database_healthy:
            response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
            return HealthResponse(
                status="degraded",
                application="ok",
                database="unavailable",
            )

        return HealthResponse(
            status="ok",
            application="ok",
            database="ok",
        )

    return application


app = create_app()
