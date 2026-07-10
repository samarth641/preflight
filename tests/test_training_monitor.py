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


def test_api_dashboard_stats() -> None:
    r = client.get("/api/v1/dashboard/stats")
    assert r.status_code == 200
    assert r.json()["total_experiments"] == 5


def test_api_live_monitor() -> None:
    r = client.get("/api/v1/training/monitor")
    assert r.status_code == 200
    assert r.json()["epoch"] == 8
