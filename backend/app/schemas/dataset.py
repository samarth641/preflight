"""Dataset API schemas."""

from pydantic import BaseModel, Field

from app.core.analyzers.dataset.models import DatasetAnalysisResult


class DatasetAnalyzeRequest(BaseModel):
    path: str = Field(description="Absolute or relative path to dataset directory")
    max_images: int | None = Field(default=None, ge=1)


class DatasetAnalyzeResponse(DatasetAnalysisResult):
    pass
