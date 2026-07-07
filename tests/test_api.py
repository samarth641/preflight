"""Tests for FastAPI endpoints."""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


@pytest.fixture
def fixtures_root() -> Path:
    return Path(__file__).resolve().parent / "fixtures"


def test_root_health() -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_api_health() -> None:
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    assert response.json()["version"]


def test_gpu_recommend() -> None:
    response = client.post(
        "/api/v1/gpu/recommend",
        json={
            "parameter_count_billion": 7.0,
            "training_mode": "lora",
            "model_type": "transformer",
            "epochs": 5,
            "include_cost": True,
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["required_vram_gb"] > 0
    assert len(data["candidates"]) > 0
    assert data["candidates"][0]["cost_estimate"] is not None


def test_cost_estimate() -> None:
    response = client.post(
        "/api/v1/cost/estimate",
        json={
            "parameter_count_billion": 7.0,
            "gpu_id": "rtx-4090",
            "epochs": 10,
            "cloud_provider": "runpod",
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["total_usd"] > 0
    assert data["breakdown"]["cloud_usd"] > 0


def test_training_analyze(fixtures_root: Path) -> None:
    log_path = fixtures_root / "training" / "healthy.csv"
    response = client.post(
        "/api/v1/training/analyze",
        json={"path": str(log_path)},
    )
    assert response.status_code == 200
    assert response.json()["score"] > 0


def test_dataset_analyze_not_found() -> None:
    response = client.post(
        "/api/v1/dataset/analyze",
        json={"path": "/nonexistent/dataset"},
    )
    assert response.status_code == 404
