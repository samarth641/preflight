"""GPU recommender — ranks hardware based on model requirements."""

from __future__ import annotations

import logging

from app.core.engine.engine import KnowledgeEngine
from app.core.recommenders.gpu.estimator import estimate_vram_gb
from app.core.recommenders.gpu.models import (
    CloudOffering,
    GPUCandidate,
    GPURecommendationRequest,
    GPURecommendationResult,
)
from app.core.recommenders.gpu.registry import CloudRegistry, GPURegistry
from app.core.recommenders.gpu.scorer import score_gpu

logger = logging.getLogger(__name__)


class GPURecommender:
    """Recommends GPUs and cloud providers based on model training requirements."""

    def __init__(
        self,
        gpu_registry: GPURegistry | None = None,
        cloud_registry: CloudRegistry | None = None,
        engine: KnowledgeEngine | None = None,
    ) -> None:
        self._gpu_registry = gpu_registry or GPURegistry()
        self._cloud_registry = cloud_registry or CloudRegistry()
        self._engine = engine or KnowledgeEngine()

    def recommend(self, request: GPURecommendationRequest) -> GPURecommendationResult:
        required_vram = estimate_vram_gb(request)
        gpus = self._gpu_registry.gpus
        max_tflops = max((gpu.tflops_fp16 for gpu in gpus), default=1.0)

        candidates: list[GPUCandidate] = []
        for gpu in gpus:
            if request.preferred_vendor and gpu.vendor != request.preferred_vendor:
                continue
            candidate = score_gpu(gpu, required_vram, request, max_tflops)
            if candidate is not None:
                candidates.append(candidate)

        candidates.sort(key=lambda c: (-c.score, -c.gpu.vram_gb))

        eligible = [c for c in candidates if c.fit_rating.value != "insufficient"]
        ranked = eligible[: request.max_results]

        if not ranked and candidates:
            ranked = sorted(candidates, key=lambda c: c.headroom_gb, reverse=True)[:request.max_results]

        cloud_offerings = self._match_cloud(ranked, required_vram, request)

        context = {
            "hardware": {
                "required_vram_gb": required_vram,
                "vram_gb": ranked[0].gpu.vram_gb if ranked else 0,
                "gpu_vendor": request.preferred_vendor or (ranked[0].gpu.vendor if ranked else "nvidia"),
                "preferred_vendor": request.preferred_vendor,
                "parameter_count": request.parameter_count,
                "training_mode": request.training_mode.value,
            }
        }
        engine_result = self._engine.evaluate(context, categories=["hardware"])

        return GPURecommendationResult(
            required_vram_gb=required_vram,
            request=request,
            candidates=ranked,
            best_pick=ranked[0] if ranked else None,
            cloud_offerings=cloud_offerings,
            warnings=engine_result.warnings,
            knowledge_recommendations=engine_result.recommendations,
            sources=engine_result.sources,
        )

    def _match_cloud(
        self,
        candidates: list[GPUCandidate],
        required_vram_gb: float,
        request: GPURecommendationRequest,
    ) -> list[CloudOffering]:
        if not request.include_cloud:
            return []

        offerings = self._cloud_registry.load(self._gpu_registry)
        recommended_gpu_ids = {candidate.gpu.id for candidate in candidates[:3]}

        matched = [
            offering
            for offering in offerings
            if offering.gpu_id in recommended_gpu_ids and offering.vram_gb >= required_vram_gb
        ]

        if not matched and required_vram_gb > 24:
            matched = [
                offering for offering in offerings if offering.vram_gb >= required_vram_gb
            ]

        seen: set[str] = set()
        unique: list[CloudOffering] = []
        for offering in matched:
            key = f"{offering.provider_id}:{offering.gpu_id}"
            if key not in seen:
                seen.add(key)
                unique.append(offering)

        return unique[:5]
