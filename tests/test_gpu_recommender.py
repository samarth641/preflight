"""Tests for the GPU recommender."""

from __future__ import annotations

from pathlib import Path

import pytest

from app.core.engine.engine import KnowledgeEngine
from app.core.knowledge.loader import RuleLoader
from app.core.recommenders.gpu.estimator import estimate_vram_gb
from app.core.recommenders.gpu.models import (
    BudgetTier,
    GPURecommendationRequest,
    ModelType,
    TrainingMode,
)
from app.core.recommenders.gpu.registry import CloudRegistry, GPURegistry
from app.core.recommenders.gpu.recommender import GPURecommender


@pytest.fixture
def knowledge_root() -> Path:
    return Path(__file__).resolve().parents[1] / "knowledge"


@pytest.fixture
def gpu_registry(knowledge_root: Path) -> GPURegistry:
    return GPURegistry(knowledge_root=knowledge_root)


@pytest.fixture
def recommender(knowledge_root: Path) -> GPURecommender:
    loader = RuleLoader(knowledge_root=knowledge_root)
    engine = KnowledgeEngine(loader=loader)
    return GPURecommender(
        gpu_registry=GPURegistry(knowledge_root=knowledge_root),
        cloud_registry=CloudRegistry(knowledge_root=knowledge_root),
        engine=engine,
    )


class TestGPURegistry:
    def test_loads_all_gpus(self, gpu_registry: GPURegistry) -> None:
        gpus = gpu_registry.load()
        assert len(gpus) >= 11
        ids = {gpu.id for gpu in gpus}
        assert "rtx-4090" in ids
        assert "h100-80gb" in ids
        assert "mi300x" in ids

    def test_get_by_id(self, gpu_registry: GPURegistry) -> None:
        gpu = gpu_registry.get("rtx-3060")
        assert gpu is not None
        assert gpu.vram_gb == 12


class TestCloudRegistry:
    def test_loads_providers(self, knowledge_root: Path, gpu_registry: GPURegistry) -> None:
        cloud = CloudRegistry(knowledge_root=knowledge_root)
        offerings = cloud.load(gpu_registry)
        assert len(offerings) >= 5
        providers = {offering.provider_name for offering in offerings}
        assert "AWS" in providers
        assert "RunPod" in providers


class TestVRAMEstimator:
    def test_small_vision_model(self) -> None:
        request = GPURecommendationRequest(
            parameter_count_billion=0.05,
            model_type=ModelType.VISION,
            batch_size=32,
        )
        vram = estimate_vram_gb(request)
        assert 0.5 <= vram <= 8

    def test_large_transformer_full(self) -> None:
        request = GPURecommendationRequest(
            parameter_count_billion=7.0,
            model_type=ModelType.TRANSFORMER,
            training_mode=TrainingMode.FULL,
            batch_size=4,
        )
        vram = estimate_vram_gb(request)
        assert vram > 40

    def test_lora_uses_less_vram(self) -> None:
        full = GPURecommendationRequest(
            parameter_count_billion=7.0,
            model_type=ModelType.TRANSFORMER,
            training_mode=TrainingMode.FULL,
        )
        lora = GPURecommendationRequest(
            parameter_count_billion=7.0,
            model_type=ModelType.TRANSFORMER,
            training_mode=TrainingMode.LORA,
        )
        assert estimate_vram_gb(lora) < estimate_vram_gb(full)


class TestGPURecommender:
    def test_recommends_for_small_model(self, recommender: GPURecommender) -> None:
        request = GPURecommendationRequest(
            parameter_count_billion=0.1,
            model_type=ModelType.VISION,
            budget_tier=BudgetTier.MID,
        )
        result = recommender.recommend(request)
        assert result.required_vram_gb < 16
        assert len(result.candidates) > 0
        assert result.best_pick is not None
        assert result.best_pick.fit_rating.value != "insufficient"

    def test_large_model_recommends_datacenter(self, recommender: GPURecommender) -> None:
        request = GPURecommendationRequest(
            parameter_count_billion=13.0,
            model_type=ModelType.TRANSFORMER,
            training_mode=TrainingMode.FULL,
            batch_size=2,
        )
        result = recommender.recommend(request)
        assert result.required_vram_gb > 40
        gpu_ids = {candidate.gpu.id for candidate in result.candidates}
        assert "a100-80gb" in gpu_ids or "h100-80gb" in gpu_ids or "mi300x" in gpu_ids

    def test_vendor_filter(self, recommender: GPURecommender) -> None:
        request = GPURecommendationRequest(
            parameter_count_billion=1.0,
            preferred_vendor="amd",
        )
        result = recommender.recommend(request)
        assert all(candidate.gpu.vendor == "amd" for candidate in result.candidates)

    def test_cloud_offerings(self, recommender: GPURecommender) -> None:
        request = GPURecommendationRequest(
            parameter_count_billion=7.0,
            model_type=ModelType.TRANSFORMER,
            training_mode=TrainingMode.LORA,
            include_cloud=True,
        )
        result = recommender.recommend(request)
        assert len(result.cloud_offerings) > 0

    def test_knowledge_recommendations_for_large_model(self, recommender: GPURecommender) -> None:
        request = GPURecommendationRequest(
            parameter_count_billion=30.0,
            model_type=ModelType.TRANSFORMER,
        )
        result = recommender.recommend(request)
        rec_titles = {rec.title for rec in result.knowledge_recommendations}
        assert "Use Multi-GPU or Model Parallelism" in rec_titles
