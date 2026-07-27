from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Annotated, Literal

from fastapi import Depends, FastAPI, Response, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from app.assistant.router import router as assistant_router
from app.auth.router import router as auth_router
from app.companies.router import router as companies_router
from app.core.config import Settings, get_settings, validate_auth_configuration
from app.database.health import get_database_health, get_database_readiness
from app.database import models as database_models
from app.database.session import create_database_engine, create_session_factory
from app.failures.router import router as failures_router
from app.departments.finance.router import router as finance_router
from app.departments.procurement.router import router as procurement_router
from app.departments.hr.router import router as hr_router
from app.human_actions.router import router as human_actions_router
from app.notifications.router import router as notifications_router
from app.onboarding.router import router as onboarding_router
from app.rag.router import router as rag_router
from app.admin.router import router as admin_router
from app.departments.router import router as departments_router
from app.dashboard.router import router as dashboard_router
from app.requests.router import router as requests_router
from app.workflow.router import router as workflow_router
from app.realtime import realtime_router


_ = database_models


class HealthResponse(BaseModel):
    status: Literal["ok", "degraded"]
    application: Literal["ok"]
    database: Literal["ok", "unavailable"]


class ReadinessResponse(BaseModel):
    status: Literal["ready", "not_ready"]
    application: Literal["ok"]
    database: Literal["ready", "migration_required", "unavailable"]


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
        application.state.pinecone_provider = None

        try:
            yield
        finally:
            pinecone_provider = application.state.pinecone_provider
            if pinecone_provider is not None:
                await pinecone_provider.close()
            await engine.dispose()

    application = FastAPI(
        title="Enterprise Multi-Agent Platform",
        lifespan=lifespan,
    )
    configured_settings = settings_override or get_settings()
    application.add_middleware(
        CORSMiddleware,
        allow_origins=[str(origin).rstrip("/") for origin in configured_settings.cors_origins],
        allow_credentials=True,
        allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type", "Accept", "Last-Event-ID"],
    )
    application.include_router(auth_router)
    application.include_router(companies_router)
    application.include_router(assistant_router)
    application.include_router(requests_router)
    application.include_router(workflow_router)
    application.include_router(realtime_router)
    application.include_router(notifications_router)
    application.include_router(failures_router)
    application.include_router(finance_router)
    application.include_router(procurement_router)
    application.include_router(hr_router)
    application.include_router(human_actions_router)
    application.include_router(onboarding_router)
    application.include_router(rag_router)
    application.include_router(admin_router)
    application.include_router(departments_router)
    application.include_router(dashboard_router)

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

    @application.get("/ready", response_model=ReadinessResponse)
    async def ready(
        response: Response,
        database_healthy: Annotated[bool, Depends(get_database_health)],
        database_ready: Annotated[bool, Depends(get_database_readiness)],
    ) -> ReadinessResponse:
        if not database_healthy:
            response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
            return ReadinessResponse(
                status="not_ready",
                application="ok",
                database="unavailable",
            )
        if not database_ready:
            response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
            return ReadinessResponse(
                status="not_ready",
                application="ok",
                database="migration_required",
            )
        return ReadinessResponse(
            status="ready",
            application="ok",
            database="ready",
        )

    return application


app = create_app()

