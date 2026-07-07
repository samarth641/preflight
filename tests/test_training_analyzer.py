"""Tests for the training log analyzer."""

from __future__ import annotations

from pathlib import Path

import pytest

from app.core.analyzers.training.analyzer import TrainingAnalyzer
from app.core.analyzers.training.metrics import (
    compute_health_score,
    compute_training_metrics,
    is_diverging,
    is_loss_increasing,
    is_stagnant,
)
from app.core.analyzers.training.models import EpochMetrics
from app.core.engine.engine import KnowledgeEngine
from app.core.knowledge.loader import RuleLoader
from app.core.parsers.training_log import TrainingLogParser


@pytest.fixture
def knowledge_root() -> Path:
    return Path(__file__).resolve().parents[1] / "knowledge"


@pytest.fixture
def fixtures_dir() -> Path:
    return Path(__file__).resolve().parent / "fixtures" / "training"


@pytest.fixture
def analyzer(knowledge_root: Path) -> TrainingAnalyzer:
    loader = RuleLoader(knowledge_root=knowledge_root)
    engine = KnowledgeEngine(loader=loader)
    return TrainingAnalyzer(engine=engine)


class TestIsLossIncreasing:
    def test_true_when_rising(self) -> None:
        assert is_loss_increasing([1.8, 1.9, 2.1, 2.4]) is True

    def test_false_when_too_short(self) -> None:
        assert is_loss_increasing([1.0, 1.1]) is False

    def test_false_when_not_monotonic(self) -> None:
        assert is_loss_increasing([2.0, 1.5, 1.8, 1.6]) is False


class TestIsStagnant:
    def test_true_when_barely_changing(self) -> None:
        assert is_stagnant([1.000, 1.001, 1.002, 1.003, 1.004, 1.005]) is True

    def test_false_when_changing_a_lot(self) -> None:
        assert is_stagnant([2.0, 1.8, 1.5, 1.2, 1.0, 0.7]) is False


class TestIsDiverging:
    def test_true_when_doubled(self) -> None:
        assert is_diverging([1.0, 0.8, 0.6, 1.5]) is True

    def test_false_when_stable(self) -> None:
        assert is_diverging([1.0, 0.9, 0.8, 0.85]) is False


class TestTrainingLogParser:
    def test_parse_csv(self, fixtures_dir: Path) -> None:
        epochs = TrainingLogParser().parse(fixtures_dir / "healthy.csv")
        assert len(epochs) == 5
        assert epochs[0].epoch == 1
        assert epochs[0].train_loss == 2.0
        assert epochs[-1].val_loss == 0.8

    def test_json_format(self, fixtures_dir: Path) -> None:
        epochs = TrainingLogParser().parse(fixtures_dir / "healthy.json")
        assert len(epochs) == 3
        assert epochs[0].epoch == 1
        assert epochs[-1].train_loss == 1.0

    def test_missing_file_raises(self) -> None:
        with pytest.raises(FileNotFoundError):
            TrainingLogParser().parse(Path("/nonexistent/log.csv"))

    def test_missing_required_column_raises(self, tmp_path: Path) -> None:
        bad_csv = tmp_path / "bad.csv"
        bad_csv.write_text("loss,accuracy\n1.0,0.5\n", encoding="utf-8")
        with pytest.raises(ValueError):
            TrainingLogParser().parse(bad_csv)


class TestComputeTrainingMetrics:
    def test_overfitting_detected(self, fixtures_dir: Path) -> None:
        epochs = TrainingLogParser().parse(fixtures_dir / "overfitting.csv")
        metrics = compute_training_metrics(epochs)
        assert metrics.validation_loss_increasing is True
        assert metrics.overfitting_detected is True

    def test_healthy_log_no_issues(self, fixtures_dir: Path) -> None:
        epochs = TrainingLogParser().parse(fixtures_dir / "healthy.csv")
        metrics = compute_training_metrics(epochs)
        assert metrics.validation_loss_increasing is False
        assert metrics.overfitting_detected is False

    def test_gpu_bottleneck_signals(self, fixtures_dir: Path) -> None:
        epochs = TrainingLogParser().parse(fixtures_dir / "gpu_bottleneck.csv")
        metrics = compute_training_metrics(epochs)
        assert metrics.avg_gpu_utilization is not None
        assert metrics.avg_gpu_utilization < 70
        assert metrics.cpu_utilization is not None
        assert metrics.cpu_utilization < 50


class TestComputeHealthScore:
    def test_healthy_scores_higher_than_overfitting(self, fixtures_dir: Path) -> None:
        healthy = compute_training_metrics(TrainingLogParser().parse(fixtures_dir / "healthy.csv"))
        overfitting = compute_training_metrics(
            TrainingLogParser().parse(fixtures_dir / "overfitting.csv")
        )
        assert compute_health_score(healthy) > compute_health_score(overfitting)


class TestTrainingAnalyzer:
    def test_overfitting_recommendation(self, analyzer: TrainingAnalyzer, fixtures_dir: Path) -> None:
        result = analyzer.analyze(fixtures_dir / "overfitting.csv")
        assert any("early stopping" in rec.recommendation.lower() for rec in result.recommendations)

    def test_healthy_log_high_score(self, analyzer: TrainingAnalyzer, fixtures_dir: Path) -> None:
        result = analyzer.analyze(fixtures_dir / "healthy.csv")
        assert result.score >= 80

    def test_gpu_bottleneck_triggers_dataloader_rule(
        self, analyzer: TrainingAnalyzer, fixtures_dir: Path
    ) -> None:
        result = analyzer.analyze(fixtures_dir / "gpu_bottleneck.csv")
        rec_titles = {rec.title for rec in result.recommendations}
        assert "Increase DataLoader Workers" in rec_titles

    def test_json_format(self, analyzer: TrainingAnalyzer, fixtures_dir: Path) -> None:
        result = analyzer.analyze(fixtures_dir / "healthy.json")
        assert result.metrics.epoch_count == 3

    def test_missing_file_raises(self, analyzer: TrainingAnalyzer) -> None:
        with pytest.raises(FileNotFoundError):
            analyzer.analyze("/nonexistent/log.csv")

    def test_analyze_epochs_directly(self, analyzer: TrainingAnalyzer) -> None:
        epochs = [
            EpochMetrics(epoch=1, train_loss=2.0, val_loss=2.1),
            EpochMetrics(epoch=2, train_loss=1.5, val_loss=2.5),
            EpochMetrics(epoch=3, train_loss=1.0, val_loss=2.8),
        ]
        result = analyzer.analyze_epochs(epochs)
        assert result.metrics.epoch_count == 3
        assert result.grade in ("A", "B", "C", "D", "F")
