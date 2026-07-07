"""Tests for the dataset analyzer."""

from __future__ import annotations

from pathlib import Path

import pytest
from PIL import Image, ImageFilter

from app.core.analyzers.dataset.analyzer import DatasetAnalyzer
from app.core.analyzers.dataset.metrics import compute_metrics, compute_score, estimate_accuracy_impact
from app.core.analyzers.dataset.models import DatasetLayout
from app.core.analyzers.dataset.scanner import DatasetScanner
from app.core.knowledge.loader import RuleLoader


def _save_image(path: Path, size: tuple[int, int] = (256, 256), *, blurry: bool = False) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    image = Image.new("RGB", size, color=(100, 150, 200))
    if blurry:
        image = image.filter(ImageFilter.GaussianBlur(radius=5))
    image.save(path)


def _save_duplicate(source: Path, target: Path) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(source.read_bytes())


@pytest.fixture
def knowledge_root() -> Path:
    return Path(__file__).resolve().parents[1] / "knowledge"


@pytest.fixture
def analyzer(knowledge_root: Path) -> DatasetAnalyzer:
    loader = RuleLoader(knowledge_root=knowledge_root)
    from app.core.engine.engine import KnowledgeEngine

    engine = KnowledgeEngine(loader=loader)
    return DatasetAnalyzer(engine=engine)


@pytest.fixture
def balanced_dataset(tmp_path: Path) -> Path:
    """Create a balanced class-folder dataset."""
    root = tmp_path / "balanced"
    for class_name in ("cats", "dogs", "birds"):
        for index in range(10):
            _save_image(root / class_name / f"{class_name}_{index}.png")
    return root


@pytest.fixture
def imbalanced_dataset(tmp_path: Path) -> Path:
    """Create an imbalanced dataset with duplicates and blur."""
    root = tmp_path / "imbalanced"
    for index in range(50):
        _save_image(root / "majority" / f"img_{index}.png")
    for index in range(3):
        _save_image(root / "minority" / f"img_{index}.png", size=(64, 64))
    _save_image(root / "majority" / "blurry.png", blurry=True)
    source = root / "majority" / "img_0.png"
    _save_duplicate(source, root / "majority" / "dup_img_0.png")
    return root


@pytest.fixture
def unlabeled_dataset(tmp_path: Path) -> Path:
    root = tmp_path / "unlabeled"
    for index in range(5):
        _save_image(root / f"image_{index}.png")
    return root


class TestDatasetScanner:
    def test_scans_class_folders(self, balanced_dataset: Path) -> None:
        scanner = DatasetScanner()
        samples, layout = scanner.scan(balanced_dataset)
        assert layout == DatasetLayout.CLASS_FOLDERS
        assert len(samples) == 30
        assert all(sample.has_label for sample in samples)

    def test_detects_duplicates(self, imbalanced_dataset: Path) -> None:
        scanner = DatasetScanner()
        samples, _ = scanner.scan(imbalanced_dataset)
        duplicate_count = sum(1 for sample in samples if sample.is_duplicate)
        assert duplicate_count >= 1

    def test_detects_blur(self, imbalanced_dataset: Path) -> None:
        scanner = DatasetScanner()
        samples, _ = scanner.scan(imbalanced_dataset)
        blurry = [sample for sample in samples if sample.is_blurry]
        assert len(blurry) >= 1

    def test_flat_layout_missing_labels(self, unlabeled_dataset: Path) -> None:
        scanner = DatasetScanner()
        samples, layout = scanner.scan(unlabeled_dataset)
        assert layout == DatasetLayout.FLAT
        assert all(not sample.has_label for sample in samples)


class TestDatasetMetrics:
    def test_imbalance_ratio(self, imbalanced_dataset: Path) -> None:
        scanner = DatasetScanner()
        samples, layout = scanner.scan(imbalanced_dataset)
        metrics = compute_metrics(samples, layout)
        assert metrics.class_imbalance_ratio > 5
        assert metrics.duplicate_percent > 0

    def test_score_degrades_with_issues(self, balanced_dataset: Path, imbalanced_dataset: Path) -> None:
        scanner = DatasetScanner()
        good_samples, good_layout = scanner.scan(balanced_dataset)
        bad_samples, bad_layout = scanner.scan(imbalanced_dataset)
        good_score = compute_score(compute_metrics(good_samples, good_layout))
        bad_score = compute_score(compute_metrics(bad_samples, bad_layout))
        assert good_score > bad_score

    def test_accuracy_impact(self, imbalanced_dataset: Path) -> None:
        scanner = DatasetScanner()
        samples, layout = scanner.scan(imbalanced_dataset)
        metrics = compute_metrics(samples, layout)
        impact = estimate_accuracy_impact(metrics)
        assert impact.estimated_loss_percent > 0
        assert len(impact.factors) > 1


class TestDatasetAnalyzer:
    def test_full_analysis(self, analyzer: DatasetAnalyzer, balanced_dataset: Path) -> None:
        result = analyzer.analyze(balanced_dataset)
        assert result.score > 0
        assert result.grade in ("A", "B", "C", "D", "F")
        assert result.metrics.image_count == 30
        assert result.metrics.class_count == 3

    def test_imbalanced_triggers_recommendations(
        self, analyzer: DatasetAnalyzer, imbalanced_dataset: Path
    ) -> None:
        result = analyzer.analyze(imbalanced_dataset)
        assert result.metrics.class_imbalance_ratio >= 5
        rec_titles = {rec.title for rec in result.recommendations}
        assert "Address Class Imbalance" in rec_titles

    def test_missing_labels_warning(
        self, analyzer: DatasetAnalyzer, unlabeled_dataset: Path
    ) -> None:
        result = analyzer.analyze(unlabeled_dataset)
        assert result.metrics.missing_label_percent == 100.0

    def test_analyze_metrics_directly(self, analyzer: DatasetAnalyzer) -> None:
        from app.core.analyzers.dataset.models import DatasetMetrics

        metrics = DatasetMetrics(
            image_count=50,
            class_count=2,
            class_imbalance_ratio=12.0,
            duplicate_percent=10.0,
            blur_percent=15.0,
            missing_label_percent=0.0,
            median_resolution=128,
        )
        result = analyzer.analyze_metrics(metrics)
        assert result.score < 70
        assert result.accuracy_impact.estimated_loss_percent > 0

    def test_nonexistent_path_raises(self, analyzer: DatasetAnalyzer) -> None:
        with pytest.raises(FileNotFoundError):
            analyzer.analyze("/nonexistent/dataset/path")
