"""Pydantic models for dataset analysis."""

from __future__ import annotations

from enum import Enum
from pathlib import Path

from pydantic import BaseModel, Field

from app.core.engine.models import Recommendation, Warning


class DatasetLayout(str, Enum):
    """Detected dataset directory layout."""

    CLASS_FOLDERS = "class_folders"
    FLAT = "flat"
    MIXED = "mixed"


class ImageSample(BaseModel):
    """Metadata for a single image in the dataset."""

    path: Path
    label: str | None = None
    width: int = 0
    height: int = 0
    file_hash: str = ""
    perceptual_hash: int = 0
    blur_score: float = 0.0
    is_blurry: bool = False
    is_duplicate: bool = False
    has_label: bool = False

    model_config = {"arbitrary_types_allowed": True}

    @property
    def min_dimension(self) -> int:
        if self.width == 0 or self.height == 0:
            return 0
        return min(self.width, self.height)


class ClassStats(BaseModel):
    """Statistics for a single class."""

    name: str
    count: int
    percent: float = 0.0


class DatasetMetrics(BaseModel):
    """Computed metrics from dataset scanning."""

    image_count: int = 0
    class_count: int = 0
    layout: DatasetLayout = DatasetLayout.FLAT
    class_distribution: dict[str, int] = Field(default_factory=dict)
    class_stats: list[ClassStats] = Field(default_factory=list)
    class_imbalance_ratio: float = 1.0
    duplicate_count: int = 0
    duplicate_percent: float = 0.0
    near_duplicate_count: int = 0
    blur_count: int = 0
    blur_percent: float = 0.0
    missing_label_count: int = 0
    missing_label_percent: float = 0.0
    median_resolution: int = 0
    min_resolution: int = 0
    max_resolution: int = 0
    avg_resolution: float = 0.0

    def to_context(self) -> dict:
        """Convert metrics to knowledge engine context."""
        return {
            "image_count": self.image_count,
            "class_count": self.class_count,
            "class_imbalance_ratio": self.class_imbalance_ratio,
            "duplicate_percent": self.duplicate_percent,
            "blur_percent": self.blur_percent,
            "missing_label_percent": self.missing_label_percent,
            "median_resolution": self.median_resolution,
            "min_resolution": self.min_resolution,
            "avg_resolution": self.avg_resolution,
        }


class AccuracyImpact(BaseModel):
    """Estimated accuracy impact from dataset quality issues."""

    estimated_loss_percent: float = Field(
        ge=0.0,
        description="Estimated accuracy reduction in percentage points",
    )
    confidence: float = Field(ge=0.0, le=1.0)
    factors: list[str] = Field(default_factory=list)


class DatasetAnalysisResult(BaseModel):
    """Complete output from dataset analysis."""

    dataset_path: Path | None = None
    metrics: DatasetMetrics
    score: float = Field(ge=0.0, le=100.0, description="Overall dataset quality score")
    grade: str = Field(description="Letter grade: A, B, C, D, F")
    warnings: list[Warning] = Field(default_factory=list)
    recommendations: list[Recommendation] = Field(default_factory=list)
    accuracy_impact: AccuracyImpact
    sources: list[str] = Field(default_factory=list)

    model_config = {"arbitrary_types_allowed": True}
