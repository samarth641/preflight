"""Schemas for the AI Explanation Engine endpoint."""
from __future__ import annotations

from pydantic import BaseModel, Field

from app.core.engine.models import EngineResult


class ExplainRequest(BaseModel):
    engine_result: EngineResult
    context: dict = Field(default_factory=dict)


class ExplainResponse(BaseModel):
    explanation: str
    backend: str
