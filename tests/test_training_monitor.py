"""Tests for rule-based training monitor and dashboard."""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.core.monitors import TrainingMonitor
from app.main import app

client = TestClient(app)


@pytest.fixture
def fixtures_dir() -> Path:
    return Path(__file__).resolve().parent / "fixtures" / "experiments"


@pytest.fixture
def monitor(fixtures_dir: Path) -> TrainingMonitor:
    return TrainingMonitor(fixtures_dir=fixtures_dir)


def test_dashboard_stats(monitor: TrainingMonitor) -> None:
    stats = monitor.dashboard_stats()
    assert stats.total_experiments == 5
    assert stats.running == 1
    assert stats.completed == 3
    assert stats.failed == 1
    assert stats.experiments_100m == 4
    assert stats.best_accuracy == pytest.approx(0.892)
    assert stats.active_experiment_id == "exp-live-100m"


def test_experiment_history(monitor: TrainingMonitor) -> None:
    history = monitor.list_experiments()
    assert len(history.experiments) == 5
    live = next(e for e in history.experiments if e.id == "exp-live-100m")
    assert live.status == "running"
    assert live.params_million == 100
    assert live.epochs_completed == 8


def test_live_monitor_convergence(monitor: TrainingMonitor) -> None:
    live = monitor.live_monitor()
    assert live.experiment_id == "exp-live-100m"
    assert live.epoch == 8
    assert live.total_epochs == 20
    assert live.params_million == 100
    assert live.accuracy == pytest.approx(0.74)
    assert live.convergence_status in {"training", "converged", "plateau", "stagnant", "diverging"}
    assert len(live.curve) == 8
    assert live.health_score > 0


def test_api_dashboard_stats() -> None:
    r = client.get("/api/v1/dashboard/stats")
    assert r.status_code == 200
    data = r.json()
    assert data["total_experiments"] == 5
    assert data["running"] == 1


def test_api_experiments() -> None:
    r = client.get("/api/v1/experiments")
    assert r.status_code == 200
    data = r.json()
    assert len(data["experiments"]) == 5
    assert data["active_experiment_id"] == "exp-live-100m"


def test_api_live_monitor() -> None:
    r = client.get("/api/v1/training/monitor")
    assert r.status_code == 200
    data = r.json()
    assert data["experiment_name"].startswith("ViT-Base")
    assert data["epoch"] == 8
    assert len(data["curve"]) == 8
    assert "convergence_status" in data
