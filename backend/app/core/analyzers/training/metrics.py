"""Training trend detection and health scoring — pure functions, no I/O."""

from __future__ import annotations

import statistics

from app.core.analyzers.dataset.metrics import score_to_grade
from app.core.analyzers.training.models import EpochMetrics, TrainingMetrics, TrainingTrend

__all__ = [
    "compute_training_metrics",
    "compute_health_score",
    "detect_trends",
    "score_to_grade",
    "is_loss_increasing",
    "is_stagnant",
    "is_diverging",
    "is_accuracy_plateau",
]

OVERFITTING_GAP_THRESHOLD = 0.5
STAGNATION_WINDOW = 5
STAGNATION_THRESHOLD_PERCENT = 1.0
DIVERGENCE_MULTIPLIER = 2.0
ACCURACY_PLATEAU_WINDOW = 5
ACCURACY_PLATEAU_THRESHOLD_PERCENT = 0.5
LOW_GPU_UTILIZATION = 70.0
LOW_CPU_UTILIZATION = 50.0
VRAM_NEAR_LIMIT_PERCENT = 90.0


def is_loss_increasing(losses: list[float], window: int = 3) -> bool:
    """True if loss rose for `window` consecutive epochs at the end."""
    if len(losses) < window + 1:
        return False
    recent = losses[-(window + 1) :]
    return all(recent[i] < recent[i + 1] for i in range(window))


def is_stagnant(
    values: list[float],
    window: int = STAGNATION_WINDOW,
    threshold_percent: float = STAGNATION_THRESHOLD_PERCENT,
) -> bool:
    """True if value changed less than `threshold_percent` over the last `window` epochs."""
    if len(values) < window + 1:
        return False
    recent = values[-(window + 1) :]
    start, end = recent[0], recent[-1]
    if start == 0:
        return False
    change_percent = abs(end - start) / abs(start) * 100
    return change_percent < threshold_percent


def is_diverging(values: list[float], multiplier: float = DIVERGENCE_MULTIPLIER) -> bool:
    """True if the latest value exceeds `multiplier` times the best (lowest) observed value."""
    if len(values) < 2:
        return False
    best = min(values)
    if best <= 0:
        return False
    return values[-1] > best * multiplier


def is_accuracy_plateau(
    values: list[float],
    window: int = ACCURACY_PLATEAU_WINDOW,
    threshold_percent: float = ACCURACY_PLATEAU_THRESHOLD_PERCENT,
) -> bool:
    """True if accuracy improved less than `threshold_percent` (absolute) over the last `window` epochs."""
    if len(values) < window + 1:
        return False
    recent = values[-(window + 1) :]
    improvement = (recent[-1] - recent[0]) * 100
    return improvement < threshold_percent


def compute_training_metrics(epochs: list[EpochMetrics]) -> TrainingMetrics:
    """Compute aggregate trend and resource signals from a full training log."""
    if not epochs:
        return TrainingMetrics()

    ordered = sorted(epochs, key=lambda e: e.epoch)

    train_losses = [e.train_loss for e in ordered if e.train_loss is not None]
    val_losses = [e.val_loss for e in ordered if e.val_loss is not None]
    accuracies = [e.accuracy for e in ordered if e.accuracy is not None]
    gpu_utils = [e.gpu_utilization for e in ordered if e.gpu_utilization is not None]
    cpu_utils = [e.cpu_utilization for e in ordered if e.cpu_utilization is not None]
    vram_percents = [e.vram_percent for e in ordered if e.vram_percent is not None]

    best_val_loss = min(val_losses) if val_losses else None
    best_epoch = None
    if best_val_loss is not None:
        for e in ordered:
            if e.val_loss == best_val_loss:
                best_epoch = e.epoch
                break

    latest_train_loss = train_losses[-1] if train_losses else None
    latest_val_loss = val_losses[-1] if val_losses else None

    overfitting_gap = 0.0
    overfitting_detected = False
    if latest_train_loss is not None and latest_val_loss is not None:
        overfitting_gap = round(latest_val_loss - latest_train_loss, 4)
        overfitting_detected = overfitting_gap > OVERFITTING_GAP_THRESHOLD

    avg_gpu_utilization = round(statistics.mean(gpu_utils), 1) if gpu_utils else None
    avg_cpu_utilization = round(statistics.mean(cpu_utils), 1) if cpu_utils else None
    vram_usage_percent = round(statistics.mean(vram_percents), 1) if vram_percents else None
    vram_near_limit = vram_usage_percent is not None and vram_usage_percent >= VRAM_NEAR_LIMIT_PERCENT

    return TrainingMetrics(
        epoch_count=len(ordered),
        current_epoch=ordered[-1].epoch,
        latest_train_loss=latest_train_loss,
        latest_val_loss=latest_val_loss,
        best_val_loss=best_val_loss,
        best_epoch=best_epoch,
        validation_loss_increasing=is_loss_increasing(val_losses),
        train_loss_stagnant=is_stagnant(train_losses),
        overfitting_gap=overfitting_gap,
        overfitting_detected=overfitting_detected,
        loss_diverging=is_diverging(train_losses) or is_diverging(val_losses),
        accuracy_plateau=is_accuracy_plateau(accuracies),
        gpu_utilization=gpu_utils[-1] if gpu_utils else None,
        cpu_utilization=avg_cpu_utilization,
        avg_gpu_utilization=avg_gpu_utilization,
        vram_usage_percent=vram_usage_percent,
        vram_near_limit=vram_near_limit,
    )


def compute_health_score(metrics: TrainingMetrics) -> float:
    """Compute overall training health score (0-100)."""
    score = 100.0

    if metrics.validation_loss_increasing:
        score -= 20
    if metrics.overfitting_detected:
        score -= 15
    if metrics.loss_diverging:
        score -= 25
    if metrics.train_loss_stagnant:
        score -= 10
    if metrics.accuracy_plateau:
        score -= 8
    if metrics.avg_gpu_utilization is not None and metrics.avg_gpu_utilization < 50:
        score -= 10
    if metrics.vram_near_limit:
        score -= 12

    return max(0.0, min(100.0, round(score, 1)))


def detect_trends(metrics: TrainingMetrics, epochs: list[EpochMetrics]) -> list[TrainingTrend]:
    """Build human-readable trend descriptions from computed metrics."""
    trends: list[TrainingTrend] = []
    epoch_numbers = sorted(e.epoch for e in epochs)

    if metrics.validation_loss_increasing:
        trends.append(
            TrainingTrend(
                name="overfitting",
                description="Validation loss has increased for multiple consecutive epochs while training continues.",
                severity="high",
                epochs_affected=epoch_numbers[-4:],
            )
        )
    if metrics.overfitting_detected:
        trends.append(
            TrainingTrend(
                name="train_val_gap",
                description=(
                    f"Validation loss exceeds training loss by {metrics.overfitting_gap:.2f}, "
                    "indicating memorization."
                ),
                severity="medium",
                epochs_affected=[metrics.current_epoch],
            )
        )
    if metrics.train_loss_stagnant:
        trends.append(
            TrainingTrend(
                name="stagnation",
                description="Training loss has barely changed over recent epochs.",
                severity="medium",
                epochs_affected=epoch_numbers[-(STAGNATION_WINDOW + 1) :],
            )
        )
    if metrics.loss_diverging:
        trends.append(
            TrainingTrend(
                name="divergence",
                description="Loss has more than doubled from its best observed value.",
                severity="high",
                epochs_affected=[metrics.current_epoch],
            )
        )
    if metrics.accuracy_plateau:
        trends.append(
            TrainingTrend(
                name="accuracy_plateau",
                description="Accuracy has improved less than 0.5% over recent epochs.",
                severity="low",
                epochs_affected=epoch_numbers[-(ACCURACY_PLATEAU_WINDOW + 1) :],
            )
        )
    if (
        metrics.avg_gpu_utilization is not None
        and metrics.avg_gpu_utilization < LOW_GPU_UTILIZATION
        and metrics.cpu_utilization is not None
        and metrics.cpu_utilization < LOW_CPU_UTILIZATION
    ):
        trends.append(
            TrainingTrend(
                name="dataloader_bottleneck",
                description="Low GPU utilization alongside low CPU utilization suggests a data loading bottleneck.",
                severity="medium",
                epochs_affected=epoch_numbers,
            )
        )
    if metrics.vram_near_limit:
        trends.append(
            TrainingTrend(
                name="vram_near_limit",
                description="VRAM usage is near the device limit, risking out-of-memory errors.",
                severity="high",
                epochs_affected=[metrics.current_epoch],
            )
        )

    return trends
