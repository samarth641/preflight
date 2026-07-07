"""FastAPI application entry point."""

from fastapi import FastAPI

from app.api.routes import router
from app.core.bootstrap import setup_plugins
from app.core.config import settings

app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="AI Training Intelligence Platform — rule-based training copilot API",
    docs_url="/docs",
    redoc_url="/redoc",
)

app.include_router(router, prefix="/api/v1")


@app.on_event("startup")
def on_startup() -> None:
    setup_plugins()


@app.get("/health")
def root_health() -> dict:
    return {"status": "ok", "version": settings.app_version}
