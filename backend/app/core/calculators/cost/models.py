"""Pydantic models for cost estimation."""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field, model_validator


class DeploymentType(str, Enum):
    LOCAL = "local"
    CLOUD = "cloud"


class CostEstimateRequest(BaseModel):
    """Input for training cost estimation."""

    parameter_count: int | None = None
    parameter_count_billion: float | None = None
    gpu_id: str = Field(description="GPU id from knowledge/hardware/gpus.yaml")
    epochs: int = Field(default=10, ge=1)
    dataset_samples: int = Field(default=10_000, ge=1)
    dataset_size_gb: float | None = Field(default=None, ge=0)
    batch_size: int = Field(default=8, ge=1)
    model_type: str = Field(default="transformer", pattern="^(vision|cnn|transformer)$")
    deployment: DeploymentType = DeploymentType.CLOUD
    cloud_provider: str | None = Field(default=None, description="aws, gcp, runpod, lambda, vast, azure")
    electricity_usd_per_kwh: float | None = None
    gpu_count: int = Field(default=1, ge=1)

    @model_validator(mode="after")
    def resolve_parameter_count(self) -> CostEstimateRequest:
        if self.parameter_count is None and self.parameter_count_billion is not None:
            self.parameter_count = int(self.parameter_count_billion * 1_000_000_000)
        if self.parameter_count is None:
            raise ValueError("parameter_count or parameter_count_billion is required")
        return self


class CostBreakdown(BaseModel):
    """Itemized cost components in USD."""

    cloud_usd: float = 0.0
    electricity_usd: float = 0.0
    storage_usd: float = 0.0
    bandwidth_usd: float = 0.0
    hardware_amortization_usd: float = 0.0


class CostEstimateResult(BaseModel):
    """Complete cost estimate output."""

    gpu_id: str
    gpu_name: str
    deployment: DeploymentType
    cloud_provider: str | None = None
    estimated_hours: float
    estimated_days: float
    seconds_per_epoch: float
    breakdown: CostBreakdown
    total_usd: float
    hourly_rate_usd: float | None = None
    notes: list[str] = Field(default_factory=list)
