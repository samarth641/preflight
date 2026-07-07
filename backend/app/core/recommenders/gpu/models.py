"""Pydantic models for GPU recommendation."""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field, model_validator

from app.core.engine.models import Recommendation, Warning


class TrainingMode(str, Enum):
    FULL = "full"
    LORA = "lora"
    INFERENCE = "inference"


class ModelType(str, Enum):
    VISION = "vision"
    CNN = "cnn"
    TRANSFORMER = "transformer"


class BudgetTier(str, Enum):
    ENTRY = "entry"
    MID = "mid"
    HIGH = "high"
    ENTHUSIAST = "enthusiast"
    DATACENTER = "datacenter"


class FitRating(str, Enum):
    EXCELLENT = "excellent"
    GOOD = "good"
    TIGHT = "tight"
    OVERKILL = "overkill"
    INSUFFICIENT = "insufficient"


class GPUSpec(BaseModel):
    """Hardware specification for a single GPU."""

    id: str
    name: str
    vendor: str
    vram_gb: int
    memory_bandwidth_gbps: int
    tflops_fp16: float
    power_watts: int
    training_speed_tier: str
    architecture: str
    msrp_usd: int | None = None


class CloudOffering(BaseModel):
    """Cloud provider GPU offering."""

    provider_id: str
    provider_name: str
    provider_url: str
    gpu_id: str
    gpu_name: str
    instance_type: str
    vram_gb: int
    gpu_count: int
    notes: str


class GPURecommendationRequest(BaseModel):
    """Input for GPU recommendation."""

    parameter_count: int | None = Field(default=None, description="Total model parameters")
    parameter_count_billion: float | None = Field(default=None, description="Params in billions")
    batch_size: int = Field(default=8, ge=1)
    precision: str = Field(default="fp16", pattern="^(fp32|fp16|int8)$")
    training_mode: TrainingMode = TrainingMode.FULL
    model_type: ModelType = ModelType.VISION
    image_size: int = Field(default=224, ge=32)
    sequence_length: int = Field(default=512, ge=1)
    budget_tier: BudgetTier | None = None
    preferred_vendor: str | None = Field(default=None, pattern="^(nvidia|amd)$")
    max_results: int = Field(default=5, ge=1, le=20)
    include_cloud: bool = True

    @model_validator(mode="after")
    def resolve_parameter_count(self) -> GPURecommendationRequest:
        if self.parameter_count is None and self.parameter_count_billion is not None:
            self.parameter_count = int(self.parameter_count_billion * 1_000_000_000)
        if self.parameter_count is None:
            raise ValueError("parameter_count or parameter_count_billion is required")
        return self


class GPUCandidate(BaseModel):
    """A ranked GPU recommendation."""

    gpu: GPUSpec
    score: float = Field(ge=0.0, le=1.0)
    fit_rating: FitRating
    vram_utilization: float = Field(description="Required VRAM / GPU VRAM ratio")
    headroom_gb: float
    reasons: list[str] = Field(default_factory=list)


class GPURecommendationResult(BaseModel):
    """Complete GPU recommendation output."""

    required_vram_gb: float
    request: GPURecommendationRequest
    candidates: list[GPUCandidate] = Field(default_factory=list)
    best_pick: GPUCandidate | None = None
    cloud_offerings: list[CloudOffering] = Field(default_factory=list)
    warnings: list[Warning] = Field(default_factory=list)
    knowledge_recommendations: list[Recommendation] = Field(default_factory=list)
    sources: list[str] = Field(default_factory=list)
