"""Dataset analyzer — scans images and produces quality assessment."""

from __future__ import annotations

import logging
from pathlib import Path

from app.core.analyzers.dataset.metrics import (
    compute_metrics,
    compute_score,
    estimate_accuracy_impact,
    score_to_grade,
)
from app.core.analyzers.dataset.models import DatasetAnalysisResult, DatasetMetrics
from app.core.analyzers.dataset.scanner import DatasetScanner
from app.core.engine.engine import KnowledgeEngine

logger = logging.getLogger(__name__)


class DatasetAnalyzer:
    """Analyzes image datasets for quality issues and training readiness.

    Scans a directory (class-folder layout), computes metrics for:
    images, classes, duplicates, blur, missing labels, resolution, class balance.

    Feeds metrics into the knowledge engine for rule-based recommendations.
    """

    def __init__(
        self,
        engine: KnowledgeEngine | None = None,
        scanner: DatasetScanner | None = None,
    ) -> None:
        self._engine = engine or KnowledgeEngine()
        self._scanner = scanner or DatasetScanner()

    def analyze(
        self,
        path: Path | str,
        *,
        max_images: int | None = None,
    ) -> DatasetAnalysisResult:
        """Scan a dataset directory and return full analysis."""
        root = Path(path)
        samples, layout = self._scanner.scan(root, max_images=max_images)
        metrics = compute_metrics(samples, layout)
        return self._build_result(metrics, dataset_path=root)

    def analyze_metrics(self, metrics: DatasetMetrics) -> DatasetAnalysisResult:
        """Analyze pre-computed metrics (for API / programmatic use)."""
        return self._build_result(metrics)

    def _build_result(
        self,
        metrics: DatasetMetrics,
        dataset_path: Path | None = None,
    ) -> DatasetAnalysisResult:
        score = compute_score(metrics)
        engine_result = self._engine.evaluate(
            {"dataset": metrics.to_context()},
            categories=["dataset"],
        )

        accuracy_impact = estimate_accuracy_impact(metrics)

        return DatasetAnalysisResult(
            dataset_path=dataset_path,
            metrics=metrics,
            score=score,
            grade=score_to_grade(score),
            warnings=engine_result.warnings,
            recommendations=engine_result.recommendations,
            accuracy_impact=accuracy_impact,
            sources=engine_result.sources,
        )
