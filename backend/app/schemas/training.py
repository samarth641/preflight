"""Training log API schemas."""

from pydantic import BaseModel, Field

from app.core.analyzers.training.models import TrainingAnalysisResult


class TrainingAnalyzeRequest(BaseModel):
    path: str = Field(description="Path to training log CSV or JSON")


class TrainingAnalyzeResponse(TrainingAnalysisResult):
    pass
