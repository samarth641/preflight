"""Pydantic models for training monitor and experiment dashboard."""

from __future__ import annotations

from pydantic import BaseModel, Field

from app.core.engine.models import Recommendation, Warning


class ExperimentRecord(BaseModel):
    id: str
    name: str
    model: str
    params_million: float
    dataset: str
    status: str  # running | completed | failed
    gpu: str
    total_epochs: int
    epochs_completed: int = 0
    final_accuracy: float | None = None
    best_val_loss: float | None = None
    convergence: str | None = None  # converged | plateau | diverging | running
    duration_hours: float | None = None
    started_at: str = ""
    target_accuracy: float | None = None


class EpochPoint(BaseModel):
    epoch: int
    train_loss: float | None = None
    val_loss: float | None = None
    accuracy: float | None = None
    gpu_utilization: float | None = None


class LiveTrainingMonitor(BaseModel):
    """Rule-based snapshot of an in-progress training run."""

    experiment_id: str
    experiment_name: str
    status: str
    params_million: float
    epoch: int
    total_epochs: int
    epoch_progress_percent: float
    samples_seen_million: float
    train_loss: float | None = None
    val_loss: float | None = None
    accuracy: float | None = None
    gpu_utilization: float | None = None
    convergence_status: str
    health_score: float = Field(ge=0, le=100)
    health_grade: str
    curve: list[EpochPoint] = Field(default_factory=list)
    warnings: list[Warning] = Field(default_factory=list)
    recommendations: list[Recommendation] = Field(default_factory=list)


class DashboardStats(BaseModel):
    total_experiments: int
    running: int
    completed: int
    failed: int
    experiments_100m: int
    avg_accuracy: float | None = None
    best_accuracy: float | None = None
    total_gpu_hours: float
    convergence_rate_percent: float
    active_experiment_id: str | None = None


class ExperimentHistoryResponse(BaseModel):
    experiments: list[ExperimentRecord]
    active_experiment_id: str | None = None
