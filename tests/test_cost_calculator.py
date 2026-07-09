"""Tests for cost calculator."""

from __future__ import annotations

from pathlib import Path

import pytest

from app.core.calculators import CostCalculator, CostEstimateRequest
from app.core.calculators.cost.models import DeploymentType
from app.core.calculators.cost.pricing import PricingRegistry
from app.core.recommenders.gpu import GPURecommender, GPURecommendationRequest
from app.core.recommenders.gpu.benchmarks import BenchmarkRegistry
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


class TestBenchmarkRegistry:
    def test_loads_reference(self, knowledge_root: Path) -> None:
        registry = BenchmarkRegistry(knowledge_root=knowledge_root)
        assert registry.relative_throughput("a100-80gb") == 1.0

    def test_h100_faster_than_a100(self, knowledge_root: Path) -> None:
        registry = BenchmarkRegistry(knowledge_root=knowledge_root)
        assert registry.relative_throughput("h100-80gb") > registry.relative_throughput("a100-80gb")

    def test_unknown_gpu_returns_none(self, knowledge_root: Path) -> None:
        registry = BenchmarkRegistry(knowledge_root=knowledge_root)
        assert registry.relative_throughput("fake-gpu") is None


class TestBenchmarkCalibration:
    def test_measured_throughput_used_in_note(self, calculator: CostCalculator) -> None:
        result = calculator.estimate(
            CostEstimateRequest(
                parameter_count_billion=7.0,
                gpu_id="h100-80gb",
                epochs=1,
                deployment=DeploymentType.CLOUD,
                cloud_provider="lambda",
            )
        )
        assert any("benchmark" in n.lower() for n in result.notes)

    def test_h100_trains_faster_than_a100(self, calculator: CostCalculator) -> None:
        common = dict(parameter_count_billion=7.0, epochs=1, deployment=DeploymentType.LOCAL)
        h100 = calculator.estimate(CostEstimateRequest(gpu_id="h100-80gb", **common))
        a100 = calculator.estimate(CostEstimateRequest(gpu_id="a100-80gb", **common))
        assert h100.estimated_hours < a100.estimated_hours


class TestEmpiricalLinearModel:
    """Validates the linear performance model (linear in dataset, inverse in hardware)."""

    def _local(self, gpu_id: str, **kw) -> CostEstimateRequest:
        base = dict(parameter_count_billion=7.0, gpu_id=gpu_id, epochs=1, deployment=DeploymentType.LOCAL)
        base.update(kw)
        return CostEstimateRequest(**base)

    def test_time_linear_in_dataset(self, calculator: CostCalculator) -> None:
        small = calculator.estimate(self._local("a100-80gb", dataset_samples=10_000))
        large = calculator.estimate(self._local("a100-80gb", dataset_samples=20_000))
        ratio = large.seconds_per_epoch / small.seconds_per_epoch
        assert ratio == pytest.approx(2.0, rel=0.01)

    def test_batch_size_does_not_change_epoch_time(self, calculator: CostCalculator) -> None:
        b8 = calculator.estimate(self._local("a100-80gb", batch_size=8))
        b32 = calculator.estimate(self._local("a100-80gb", batch_size=32))
        assert b8.seconds_per_epoch == pytest.approx(b32.seconds_per_epoch, rel=1e-6)

    def test_more_gpus_reduce_wall_clock(self, calculator: CostCalculator) -> None:
        one = calculator.estimate(self._local("a100-80gb", gpu_count=1))
        four = calculator.estimate(self._local("a100-80gb", gpu_count=4))
        assert four.estimated_hours < one.estimated_hours
        # Sub-linear scaling: 4 GPUs give less than a perfect 4x speedup.
        assert four.estimated_hours > one.estimated_hours / 4

    def test_gpu_hours_exceed_wall_clock_for_multi_gpu(self, calculator: CostCalculator) -> None:
        four = calculator.estimate(self._local("a100-80gb", gpu_count=4))
        assert four.gpu_hours > four.estimated_hours
        assert four.gpu_hours == pytest.approx(four.estimated_hours * 4, rel=0.01)

    def test_single_gpu_hours_equal_wall_clock(self, calculator: CostCalculator) -> None:
        one = calculator.estimate(self._local("a100-80gb", gpu_count=1))
        assert one.gpu_hours == pytest.approx(one.estimated_hours, rel=1e-6)


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
