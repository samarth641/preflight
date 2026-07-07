"""Training log analyzer — parses logs and produces a rule-based health assessment."""

from __future__ import annotations

import logging
from pathlib import Path

from app.core.analyzers.training.metrics import (
    compute_health_score,
    compute_training_metrics,
    detect_trends,
    score_to_grade,
)
from app.core.analyzers.training.models import (
    EpochMetrics,
    TrainingAnalysisResult,
    TrainingMetrics,
)
from app.core.engine.engine import KnowledgeEngine
from app.core.parsers.training_log import TrainingLogParser

logger = logging.getLogger(__name__)


class TrainingAnalyzer:
    """Analyzes training logs for health issues and produces rule-based recommendations.

    Parses a CSV/JSON training log into per-epoch metrics, computes derived
    trend signals (overfitting, stagnation, divergence, resource bottlenecks),
    scores overall training health, and feeds signals into the knowledge
    engine for rule-based recommendations.
    """

    def __init__(
        self,
        engine: KnowledgeEngine | None = None,
        parser: TrainingLogParser | None = None,
    ) -> None:
        self._engine = engine or KnowledgeEngine()
        self._parser = parser or TrainingLogParser()

    def analyze(self, path: Path | str) -> TrainingAnalysisResult:
        """Parse a training log file and return full analysis."""
        resolved_path = Path(path)
        epochs = self._parser.parse(resolved_path)
        return self.analyze_epochs(epochs, log_path=resolved_path)

    def analyze_epochs(
        self,
        epochs: list[EpochMetrics],
        *,
        log_path: Path | None = None,
    ) -> TrainingAnalysisResult:
        """Analyze pre-parsed epoch data (for API / programmatic use)."""
        metrics = compute_training_metrics(epochs)
        return self._build_result(metrics, epochs, log_path=log_path)

    def _build_result(
        self,
        metrics: TrainingMetrics,
        epochs: list[EpochMetrics],
        log_path: Path | None = None,
    ) -> TrainingAnalysisResult:
        score = compute_health_score(metrics)
        trends = detect_trends(metrics, epochs)

        engine_result = self._engine.evaluate(
            {"training": metrics.to_context()},
            categories=["training", "optimization"],
        )

        return TrainingAnalysisResult(
            log_path=log_path,
            metrics=metrics,
            trends=trends,
            score=score,
            grade=score_to_grade(score),
            warnings=engine_result.warnings,
            recommendations=engine_result.recommendations,
            sources=engine_result.sources,
        )
