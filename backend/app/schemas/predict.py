"""Schemas for ML prediction endpoints (duration + cost)."""
from __future__ import annotations

from pydantic import BaseModel, Field


class DurationPredictBody(BaseModel):
    parameter_count_billion: float = Field(..., gt=0, description="Model size in billions of parameters")
    dataset_tokens: float = Field(..., gt=0, description="Training tokens (or samples for non-LLM)")
    gpu_id: str = Field(..., description="GPU id from knowledge base, e.g. mi300x, rtx-4090")
    n_gpus: int = Field(1, ge=1)
    epochs: int = Field(1, ge=1)
    domain: str = Field("language", description="language|vision|multimodal|image generation|biology|other")
    cloud_provider: str | None = Field(None, description="If set, cost is computed from this provider's hourly rate")


class DurationPredictResponse(BaseModel):
    estimated_hours: float
    estimated_duration_human: str
    theoretical_hours: float
    gpu_id: str
    n_gpus: int
    model_version: str
    estimated_cost_usd: float | None = None
    cost_provider: str | None = None
    hourly_rate_usd: float | None = None
