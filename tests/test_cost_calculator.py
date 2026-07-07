"""Tests for cost calculator."""

from __future__ import annotations

from pathlib import Path

import pytest

from app.core.calculators import CostCalculator, CostEstimateRequest
from app.core.calculators.cost.models import DeploymentType
from app.core.calculators.cost.pricing import PricingRegistry
from app.core.recommenders.gpu import GPURecommender, GPURecommendationRequest
from app.core.recommenders.gpu.models import ModelType, TrainingMode


@pytest.fixture
def knowledge_root() -> Path:
    return Path(__file__).resolve().parents[1] / "knowledge"


@pytest.fixture
def calculator(knowledge_root: Path) -> CostCalculator:
    from app.core.recommenders.gpu.registry import GPURegistry

    return CostCalculator(
        gpu_registry=GPURegistry(knowledge_root=knowledge_root),
        pricing_registry=PricingRegistry(knowledge_root=knowledge_root),
    )


class TestPricingRegistry:
    def test_loads_cloud_rates(self, knowledge_root: Path) -> None:
        registry = PricingRegistry(knowledge_root=knowledge_root)
        rate = registry.cloud_hourly_rate("rtx-4090", "runpod")
        assert rate == 0.44


class TestCostCalculator:
    def test_cloud_cost(self, calculator: CostCalculator) -> None:
        request = CostEstimateRequest(
            parameter_count_billion=7.0,
            gpu_id="rtx-4090",
            epochs=10,
            deployment=DeploymentType.CLOUD,
            cloud_provider="runpod",
        )
        result = calculator.estimate(request)
        assert result.total_usd > 0
        assert result.breakdown.cloud_usd > 0
        assert result.estimated_hours > 0

    def test_local_cost(self, calculator: CostCalculator) -> None:
        request = CostEstimateRequest(
            parameter_count_billion=0.1,
            gpu_id="rtx-4060-ti",
            epochs=5,
            deployment=DeploymentType.LOCAL,
        )
        result = calculator.estimate(request)
        assert result.breakdown.cloud_usd == 0
        assert result.breakdown.electricity_usd >= 0

    def test_unknown_gpu_raises(self, calculator: CostCalculator) -> None:
        with pytest.raises(ValueError, match="Unknown GPU"):
            calculator.estimate(
                CostEstimateRequest(
                    parameter_count_billion=1.0,
                    gpu_id="fake-gpu",
                    epochs=1,
                )
            )


class TestGPURecommenderCostIntegration:
    def test_includes_cost_on_candidates(self, knowledge_root: Path) -> None:
        from app.core.recommenders.gpu.registry import CloudRegistry, GPURegistry

        recommender = GPURecommender(
            gpu_registry=GPURegistry(knowledge_root=knowledge_root),
            cloud_registry=CloudRegistry(knowledge_root=knowledge_root),
        )
        request = GPURecommendationRequest(
            parameter_count_billion=7.0,
            training_mode=TrainingMode.LORA,
            model_type=ModelType.TRANSFORMER,
            include_cost=True,
            epochs=5,
        )
        result = recommender.recommend(request)
        assert any(c.cost_estimate is not None for c in result.candidates)
        if result.cheapest_gpu:
            assert result.cheapest_gpu.cost_estimate is not None
