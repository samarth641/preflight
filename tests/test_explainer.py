"""Tests for the AI Explanation Engine (Core Objective #10)."""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.core.engine.models import EngineResult, Recommendation, Warning
from app.core.explainers import ExplanationEngine
from app.main import app

client = TestClient(app)


def _recommendation(**overrides) -> Recommendation:
    base = dict(
        rule_id="cuda-memory-fragmentation",
        title="Insufficient VRAM for Model Size",
        recommendation="Call torch.cuda.empty_cache() and reduce batch size.",
        reason="VRAM usage above 90% risks OOM errors during training.",
        confidence=0.9,
        priority=8,
        category="hardware",
        source="NVIDIA CUDA Documentation",
        documentation_url="https://example.com",
        score=0.85,
    )
    base.update(overrides)
    return Recommendation(**base)


def _warning(**overrides) -> Warning:
    base = dict(
        rule_id="training-loss-diverging",
        title="Training Loss Diverging",
        message="Loss increased for 3 consecutive epochs.",
        confidence=0.95,
        source="PyTorch Documentation",
        documentation_url="https://example.com",
    )
    base.update(overrides)
    return Warning(**base)


class TestExplanationEngineTemplateFallback:
    """No fine-tuned model artifact is present in this environment — every call
    here exercises the deterministic template fallback, which must always work."""

    def test_no_issues_detected(self) -> None:
        result = ExplanationEngine().explain(EngineResult())
        assert result.backend == "template"
        assert "No issues detected" in result.explanation

    def test_single_recommendation(self) -> None:
        engine_result = EngineResult(recommendations=[_recommendation()])
        result = ExplanationEngine().explain(engine_result)
        assert result.backend == "template"
        assert "because:" in result.explanation
        assert "Recommended actions:" in result.explanation
        assert "empty_cache" in result.explanation
        assert "Estimated impact:" in result.explanation

    def test_multiple_issues_pluralizes_opening(self) -> None:
        engine_result = EngineResult(
            recommendations=[_recommendation()],
            warnings=[_warning()],
        )
        result = ExplanationEngine().explain(engine_result)
        assert "2 related issues" in result.explanation

    def test_warning_only_still_produces_actions_line(self) -> None:
        engine_result = EngineResult(warnings=[_warning()])
        result = ExplanationEngine().explain(engine_result)
        assert "Review the warnings above" in result.explanation

    def test_context_is_accepted_but_optional(self) -> None:
        engine_result = EngineResult(recommendations=[_recommendation()])
        result = ExplanationEngine().explain(engine_result, context={"hardware": {"vram_usage_percent": 94}})
        assert result.backend == "template"
        assert result.explanation


def test_api_explain_endpoint() -> None:
    response = client.post(
        "/api/v1/explain",
        json={
            "engine_result": {
                "recommendations": [
                    {
                        "rule_id": "cuda-memory-fragmentation",
                        "title": "Insufficient VRAM for Model Size",
                        "recommendation": "Reduce batch size or enable gradient checkpointing.",
                        "reason": "VRAM usage above 90% risks OOM errors.",
                        "confidence": 0.9,
                        "priority": 8,
                        "category": "hardware",
                        "source": "NVIDIA CUDA Documentation",
                        "documentation_url": "https://example.com",
                        "score": 0.85,
                    }
                ],
                "warnings": [],
            },
            "context": {"hardware": {"vram_usage_percent": 94}},
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["backend"] == "template"
    assert "Recommended actions:" in body["explanation"]
