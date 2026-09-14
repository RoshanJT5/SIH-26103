from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .api.auth import router as auth_router
from .api.assistant import router as assistant_router
from .api.datasets import router as datasets_router
from .api.health import router as health_router
from .api.projects import router as projects_router
from .api.monitoring import router as monitoring_router
from .api.trends import router as trends_router
from .api.interventions import router as interventions_router
from .api.early_warnings import router as early_warnings_router
from .api.project_extensions import router as project_ext_router
from .api.analytics_extra import router as analytics_extra_router
from .api.updates import router as updates_router
from .core.config import get_settings
from .db.session import engine


@asynccontextmanager
async def lifespan(_app: FastAPI):
    # Fail early when the configured database cannot be reached. Schema changes
    # remain Alembic's responsibility rather than being created implicitly.
    with engine.connect():
        pass
    yield


settings = get_settings()
app = FastAPI(title=settings.app_name, lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        origin.strip()
        for origin in settings.allowed_origins.split(",")
        if origin.strip()
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
)
app.include_router(health_router, prefix="/api")
app.include_router(auth_router, prefix="/api")
app.include_router(assistant_router, prefix="/api")
app.include_router(projects_router, prefix="/api")
app.include_router(datasets_router, prefix="/api")
app.include_router(monitoring_router, prefix="/api")
app.include_router(trends_router, prefix="/api")
app.include_router(interventions_router, prefix="/api")
app.include_router(early_warnings_router, prefix="/api")
app.include_router(project_ext_router, prefix="/api")
app.include_router(analytics_extra_router, prefix="/api")
app.include_router(updates_router, prefix="/api")


@app.get("/", include_in_schema=False)
def root() -> dict[str, str]:
    return {
        "status": "ok",
        "service": settings.app_name,
        "health": "/api/health",
        "docs": "/docs",
    }
