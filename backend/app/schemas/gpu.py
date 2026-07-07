"""GPU recommendation API schemas."""

from pydantic import BaseModel, Field

from app.core.recommenders.gpu.models import (
    BudgetTier,
    GPURecommendationRequest,
    GPURecommendationResult,
    ModelType,
    TrainingMode,
)


class GPURecommendBody(BaseModel):
    parameter_count_billion: float = Field(gt=0)
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
    include_cost: bool = True
    epochs: int = Field(default=10, ge=1)
    dataset_samples: int = Field(default=10_000, ge=1)
    dataset_size_gb: float | None = Field(default=None, ge=0)
    deployment: str = Field(default="cloud", pattern="^(local|cloud)$")

    def to_request(self) -> GPURecommendationRequest:
        return GPURecommendationRequest(
            parameter_count_billion=self.parameter_count_billion,
            batch_size=self.batch_size,
            precision=self.precision,
            training_mode=self.training_mode,
            model_type=self.model_type,
            image_size=self.image_size,
            sequence_length=self.sequence_length,
            budget_tier=self.budget_tier,
            preferred_vendor=self.preferred_vendor,
            max_results=self.max_results,
            include_cloud=self.include_cloud,
            include_cost=self.include_cost,
            epochs=self.epochs,
            dataset_samples=self.dataset_samples,
            dataset_size_gb=self.dataset_size_gb,
            deployment=self.deployment,
        )


class GPURecommendResponse(GPURecommendationResult):
    pass
