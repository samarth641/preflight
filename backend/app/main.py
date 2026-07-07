"""FastAPI application entry point."""

from fastapi import FastAPI

from app.core.bootstrap import setup_plugins
from app.core.config import settings

app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="AI Training Intelligence Platform",
)


@app.on_event("startup")
def on_startup() -> None:
    setup_plugins()


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "version": settings.app_version}
