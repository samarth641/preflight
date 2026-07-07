"""Dataset metrics computation and scoring."""

from __future__ import annotations

import statistics

from app.core.analyzers.dataset.models import (
    AccuracyImpact,
    ClassStats,
    DatasetLayout,
    DatasetMetrics,
    ImageSample,
)


def compute_metrics(samples: list[ImageSample], layout: DatasetLayout) -> DatasetMetrics:
    """Compute aggregate metrics from scanned image samples."""
    if not samples:
        return DatasetMetrics(layout=layout)

    class_distribution: dict[str, int] = {}
    for sample in samples:
        label = sample.label or "__unlabeled__"
        class_distribution[label] = class_distribution.get(label, 0) + 1

    labeled_classes = {
        name: count for name, count in class_distribution.items() if name != "__unlabeled__"
    }
    class_count = len(labeled_classes) or len(class_distribution)

    counts = list(labeled_classes.values()) if labeled_classes else list(class_distribution.values())
    imbalance_ratio = max(counts) / min(counts) if counts and min(counts) > 0 else 1.0

    duplicate_count = sum(1 for sample in samples if sample.is_duplicate)
    blur_count = sum(1 for sample in samples if sample.is_blurry)
    missing_label_count = sum(1 for sample in samples if not sample.has_label)

    resolutions = [sample.min_dimension for sample in samples if sample.min_dimension > 0]

    class_stats = [
        ClassStats(
            name=name,
            count=count,
            percent=round(count / len(samples) * 100, 1),
        )
        for name, count in sorted(class_distribution.items(), key=lambda item: -item[1])
    ]

    return DatasetMetrics(
        image_count=len(samples),
        class_count=class_count,
        layout=layout,
        class_distribution=class_distribution,
        class_stats=class_stats,
        class_imbalance_ratio=round(imbalance_ratio, 2),
        duplicate_count=duplicate_count,
        duplicate_percent=round(duplicate_count / len(samples) * 100, 1),
        blur_count=blur_count,
        blur_percent=round(blur_count / len(samples) * 100, 1),
        missing_label_count=missing_label_count,
        missing_label_percent=round(missing_label_count / len(samples) * 100, 1),
        median_resolution=int(statistics.median(resolutions)) if resolutions else 0,
        min_resolution=min(resolutions) if resolutions else 0,
        max_resolution=max(resolutions) if resolutions else 0,
        avg_resolution=round(statistics.mean(resolutions), 1) if resolutions else 0.0,
    )


def compute_score(metrics: DatasetMetrics) -> float:
    """Compute overall dataset quality score (0-100)."""
    score = 100.0

    if metrics.class_imbalance_ratio >= 10:
        score -= 20
    elif metrics.class_imbalance_ratio >= 5:
        score -= 12
    elif metrics.class_imbalance_ratio >= 3:
        score -= 6

    score -= min(25, metrics.duplicate_percent * 0.8)
    score -= min(20, metrics.blur_percent * 0.6)
    score -= min(30, metrics.missing_label_percent * 0.5)

    if metrics.median_resolution < 128:
        score -= 15
    elif metrics.median_resolution < 224:
        score -= 8

    if metrics.image_count < 100:
        score -= 10
    elif metrics.image_count < 500:
        score -= 5

    return max(0.0, min(100.0, round(score, 1)))


def score_to_grade(score: float) -> str:
    if score >= 90:
        return "A"
    if score >= 80:
        return "B"
    if score >= 70:
        return "C"
    if score >= 60:
        return "D"
    return "F"


def estimate_accuracy_impact(metrics: DatasetMetrics) -> AccuracyImpact:
    """Estimate expected accuracy reduction from dataset quality issues."""
    loss = 0.0
    factors: list[str] = []
    confidence_factors = 0

    if metrics.class_imbalance_ratio >= 5:
        penalty = min(15.0, 2.0 + metrics.class_imbalance_ratio)
        loss += penalty
        factors.append(f"Class imbalance (ratio {metrics.class_imbalance_ratio}:1): -{penalty:.1f}%")
        confidence_factors += 1

    if metrics.duplicate_percent >= 5:
        penalty = min(8.0, metrics.duplicate_percent * 0.4)
        loss += penalty
        factors.append(f"Duplicates ({metrics.duplicate_percent}%): -{penalty:.1f}%")
        confidence_factors += 1

    if metrics.blur_percent >= 10:
        penalty = min(10.0, metrics.blur_percent * 0.3)
        loss += penalty
        factors.append(f"Blurry images ({metrics.blur_percent}%): -{penalty:.1f}%")
        confidence_factors += 1

    if metrics.missing_label_percent >= 5:
        penalty = min(20.0, metrics.missing_label_percent * 0.3)
        loss += penalty
        factors.append(f"Missing labels ({metrics.missing_label_percent}%): -{penalty:.1f}%")
        confidence_factors += 1

    if metrics.median_resolution < 224:
        penalty = 5.0 if metrics.median_resolution < 128 else 2.0
        loss += penalty
        factors.append(f"Low resolution (median {metrics.median_resolution}px): -{penalty:.1f}%")
        confidence_factors += 1

    if metrics.image_count < 500:
        penalty = 5.0 if metrics.image_count < 100 else 2.0
        loss += penalty
        factors.append(f"Small dataset ({metrics.image_count} images): -{penalty:.1f}%")
        confidence_factors += 1

    if not factors:
        factors.append("No significant quality issues detected")

    confidence = min(0.95, 0.5 + confidence_factors * 0.1) if confidence_factors else 0.6

    return AccuracyImpact(
        estimated_loss_percent=round(loss, 1),
        confidence=round(confidence, 2),
        factors=factors,
    )
