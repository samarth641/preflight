"""Tests for the ML Training-Duration Predictor."""
from __future__ import annotations

import pytest

from app.core.predictors import DurationPredictor, DurationRequest


def _req(**overrides) -> DurationRequest:
    base = dict(
        parameter_count_billion=7.0,
        dataset_tokens=100e9,
        gpu_id="a100-80gb",
        n_gpus=8,
        epochs=1,
        domain="language",
    )
    base.update(overrides)
    return DurationRequest(**base)


def test_predicts_positive_hours() -> None:
    result = DurationPredictor().predict(_req())
    assert result.estimated_hours > 0
    assert result.theoretical_hours > 0
    assert result.gpu_id == "a100-80gb"


def test_more_gpus_is_faster() -> None:
    p = DurationPredictor()
    one = p.predict(_req(n_gpus=1))
    eight = p.predict(_req(n_gpus=8))
    assert eight.estimated_hours < one.estimated_hours


def test_bigger_model_takes_longer() -> None:
    p = DurationPredictor()
    small = p.predict(_req(parameter_count_billion=1.0))
    big = p.predict(_req(parameter_count_billion=70.0))
    assert big.estimated_hours > small.estimated_hours


def test_amd_gpus_supported() -> None:
    p = DurationPredictor()
    for gpu in ("mi300x", "rx-7900-xtx"):
        result = p.predict(_req(gpu_id=gpu, n_gpus=1,
                                parameter_count_billion=1.0,
                                dataset_tokens=1e9))
        assert result.estimated_hours > 0, gpu


def test_unknown_gpu_raises() -> None:
    with pytest.raises(ValueError, match="unknown gpu_id"):
        DurationPredictor().predict(_req(gpu_id="not-a-gpu"))


def test_api_endpoint() -> None:
    from fastapi.testclient import TestClient

    from app.main import app

    client = TestClient(app)
    resp = client.post("/api/v1/predict/duration", json={
        "parameter_count_billion": 7,
        "dataset_tokens": 100e9,
        "gpu_id": "mi300x",
        "n_gpus": 4,
        "domain": "language",
    })
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["estimated_hours"] > 0
    assert body["model_version"].startswith("duration_xgb")
