"""Pydantic models for training log analysis."""

from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel, Field

from app.core.engine.models import Recommendation, Warning


class EpochMetrics(BaseModel):
    """Metrics recorded for a single training epoch."""

    epoch: int
    train_loss: float | None = None
    val_loss: float | None = None
    accuracy: float | None = None
    gpu_utilization: float | None = None
    cpu_utilization: float | None = None
    vram_gb: float | None = None
    vram_percent: float | None = None
    power_watts: float | None = None


class TrainingMetrics(BaseModel):
    """Computed trend and resource signals from a full training log."""

    epoch_count: int = 0
    current_epoch: int = 0
    latest_train_loss: float | None = None
    latest_val_loss: float | None = None
    best_val_loss: float | None = None
    best_epoch: int | None = None

    # Derived trend signals (used by rule engine)
    validation_loss_increasing: bool = False
    train_loss_stagnant: bool = False
    overfitting_gap: float = 0.0
    overfitting_detected: bool = False
    loss_diverging: bool = False
    accuracy_plateau: bool = False

    # Resource signals
    gpu_utilization: float | None = None
    cpu_utilization: float | None = None
    avg_gpu_utilization: float | None = None
    vram_usage_percent: float | None = None
    vram_near_limit: bool = False

    def to_context(self) -> dict:
        """Convert metrics to knowledge engine context."""
        return {
            "epoch": self.current_epoch,
            "epoch_count": self.epoch_count,
            "validation_loss_increasing": self.validation_loss_increasing,
            "train_loss_stagnant": self.train_loss_stagnant,
            "overfitting_detected": self.overfitting_detected,
            "overfitting_gap": self.overfitting_gap,
            "loss_diverging": self.loss_diverging,
            "accuracy_plateau": self.accuracy_plateau,
            "gpu_utilization": self.avg_gpu_utilization or self.gpu_utilization,
            "cpu_utilization": self.cpu_utilization,
            "vram_usage_percent": self.vram_usage_percent,
            "train_loss": self.latest_train_loss,
            "val_loss": self.latest_val_loss,
        }


class TrainingTrend(BaseModel):
    """A human-readable detected training pattern."""

    name: str
    description: str
    severity: str
    epochs_affected: list[int] = Field(default_factory=list)


class TrainingAnalysisResult(BaseModel):
    """Complete output from training log analysis."""

    log_path: Path | None = None
    metrics: TrainingMetrics
    trends: list[TrainingTrend] = Field(default_factory=list)
    score: float = Field(ge=0.0, le=100.0)
    grade: str
    warnings: list[Warning] = Field(default_factory=list)
    recommendations: list[Recommendation] = Field(default_factory=list)
    sources: list[str] = Field(default_factory=list)
