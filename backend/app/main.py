from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.auth import router as auth_router
from app.api.assistant import router as assistant_router
from app.api.datasets import router as datasets_router
from app.api.health import router as health_router
from app.api.projects import router as projects_router
from app.api.monitoring import router as monitoring_router
from app.core.config import get_settings
from app.db.session import engine


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
    allow_origins=[origin.strip() for origin in settings.allowed_origins.split(",") if origin.strip()],
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
