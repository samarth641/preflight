"""Tests for flexible duration CSV loading."""

from __future__ import annotations

from pathlib import Path

import pytest

from app.core.calculators.cost.duration_loader import detect_column_map, load_duration_csv, load_duration_files
from app.core.recommenders.gpu.registry import GPURegistry


@pytest.fixture
def knowledge_root() -> Path:
    return Path(__file__).resolve().parents[1] / "knowledge"


@pytest.fixture
def known_gpu_ids(knowledge_root: Path) -> set[str]:
    return {g.id for g in GPURegistry(knowledge_root=knowledge_root).gpus}


@pytest.fixture
def fixtures_dir() -> Path:
    return Path(__file__).resolve().parent / "fixtures"


class TestDurationLoader:
    def test_native_schema(self, fixtures_dir: Path, known_gpu_ids: set[str]) -> None:
        report = load_duration_csv(fixtures_dir / "duration_runs.csv", known_gpu_ids=known_gpu_ids)
        assert len(report.runs) >= 20

    def test_mlperf_style_schema(self, fixtures_dir: Path, known_gpu_ids: set[str]) -> None:
        report = load_duration_csv(fixtures_dir / "duration_mlperf_style.csv", known_gpu_ids=known_gpu_ids)
        assert len(report.runs) == 4
        assert report.runs[0].gpu_id == "h100-80gb"
        assert report.runs[0].seconds_per_epoch == pytest.approx(3600)
        assert report.runs[2].model_type == "vision"

    def test_kaggle_style_schema(self, fixtures_dir: Path, known_gpu_ids: set[str]) -> None:
        report = load_duration_csv(fixtures_dir / "duration_kaggle_style.csv", known_gpu_ids=known_gpu_ids)
        assert len(report.runs) == 4
        assert report.runs[0].gpu_id == "rtx-4090"
        assert report.runs[0].seconds_per_epoch == pytest.approx(900)  # 60 min / 4 epochs
        assert report.runs[3].model_type == "vision"

    def test_merge_multiple_files(self, fixtures_dir: Path, known_gpu_ids: set[str]) -> None:
        paths = [
            fixtures_dir / "duration_mlperf_style.csv",
            fixtures_dir / "duration_kaggle_style.csv",
        ]
        report = load_duration_files(paths, known_gpu_ids=known_gpu_ids)
        assert len(report.runs) == 8

    def test_detect_column_map(self) -> None:
        headers = ["training_time", "gpu_type", "params_b", "num_samples"]
        mapping = detect_column_map(headers)
        assert mapping["total_time"] == "training_time"
        assert mapping["gpu_id"] == "gpu_type"
        assert mapping["parameter_count_billion"] == "params_b"
        assert mapping["dataset_samples"] == "num_samples"

    def test_param_size_text(self, fixtures_dir: Path, known_gpu_ids: set[str]) -> None:
        report = load_duration_csv(fixtures_dir / "duration_mlperf_style.csv", known_gpu_ids=known_gpu_ids)
        cnn = next(r for r in report.runs if r.model_type == "cnn")
        assert cnn.parameter_count_billion == pytest.approx(0.0035, rel=1e-2)
