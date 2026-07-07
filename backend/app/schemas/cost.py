"""Cost estimation API schemas."""

from pydantic import BaseModel, Field

from app.core.calculators.cost.models import CostEstimateRequest, CostEstimateResult, DeploymentType


class CostEstimateBody(BaseModel):
    parameter_count_billion: float = Field(gt=0)
    gpu_id: str
    epochs: int = Field(default=10, ge=1)
    dataset_samples: int = Field(default=10_000, ge=1)
    dataset_size_gb: float | None = Field(default=None, ge=0)
    batch_size: int = Field(default=8, ge=1)
    model_type: str = Field(default="transformer", pattern="^(vision|cnn|transformer)$")
    deployment: DeploymentType = DeploymentType.CLOUD
    cloud_provider: str | None = None
    electricity_usd_per_kwh: float | None = Field(default=None, ge=0)
    gpu_count: int = Field(default=1, ge=1)

    def to_request(self) -> CostEstimateRequest:
        return CostEstimateRequest(
            parameter_count_billion=self.parameter_count_billion,
            gpu_id=self.gpu_id,
            epochs=self.epochs,
            dataset_samples=self.dataset_samples,
            dataset_size_gb=self.dataset_size_gb,
            batch_size=self.batch_size,
            model_type=self.model_type,
            deployment=self.deployment,
            cloud_provider=self.cloud_provider,
            electricity_usd_per_kwh=self.electricity_usd_per_kwh,
            gpu_count=self.gpu_count,
        )


class CostEstimateResponse(CostEstimateResult):
    pass
