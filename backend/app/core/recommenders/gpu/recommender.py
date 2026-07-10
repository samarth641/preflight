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
from app.core.recommenders.gpu.benchmarks import BenchmarkRegistry
from app.core.recommenders.gpu.registry import CloudRegistry, GPURegistry
from app.core.recommenders.gpu.scorer import score_gpu

logger = logging.getLogger(__name__)

# A100 80GB peak FP16 TFLOPS — anchors the TFLOPS->throughput fallback scale.
REFERENCE_TFLOPS_FP16 = 312.0


class GPURecommender:
    """Recommends GPUs and cloud providers based on model training requirements."""

    def __init__(
        self,
        gpu_registry: GPURegistry | None = None,
        cloud_registry: CloudRegistry | None = None,
        engine: KnowledgeEngine | None = None,
        benchmark_registry: BenchmarkRegistry | None = None,
    ) -> None:
        self._gpu_registry = gpu_registry or GPURegistry()
        self._cloud_registry = cloud_registry or CloudRegistry()
        self._engine = engine or KnowledgeEngine()
        self._benchmarks = benchmark_registry or BenchmarkRegistry(self._gpu_registry.knowledge_root)
        self._cost_calculator = None

    @property
    def cost_calculator(self):
        if self._cost_calculator is None:
            from app.core.calculators.cost.calculator import CostCalculator

            self._cost_calculator = CostCalculator(gpu_registry=self._gpu_registry)
        return self._cost_calculator

    def recommend(self, request: GPURecommendationRequest) -> GPURecommendationResult:
        required_vram = estimate_vram_gb(request)
        gpus = self._gpu_registry.gpus
        perf_by_id = self._perf_by_id(gpus)
        max_perf = max((v for v, _ in perf_by_id.values()), default=1.0)

        candidates: list[GPUCandidate] = []
        for gpu in gpus:
            if request.preferred_vendor and gpu.vendor != request.preferred_vendor:
                continue
            perf_value, from_benchmark = perf_by_id[gpu.id]
            candidate = score_gpu(
                gpu, required_vram, request, perf_value, max_perf, perf_from_benchmark=from_benchmark
            )
            if candidate is not None:
                candidates.append(candidate)

        candidates.sort(key=lambda c: (-c.score, -c.gpu.vram_gb))

        eligible = [c for c in candidates if c.fit_rating.value != "insufficient"]
        ranked = eligible[: request.max_results]

        if not ranked and candidates:
            ranked = sorted(candidates, key=lambda c: c.headroom_gb, reverse=True)[:request.max_results]

        if request.include_cost:
            ranked = self._attach_cost_estimates(ranked, request)
            ranked = self._apply_cost_value_boost(ranked)

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

        cheapest = None
        if request.include_cost and ranked:
            with_cost = [c for c in ranked if c.cost_estimate is not None]
            if with_cost:
                cheapest = min(with_cost, key=lambda c: c.cost_estimate.total_usd)  # type: ignore[union-attr]

        return GPURecommendationResult(
            required_vram_gb=required_vram,
            request=request,
            candidates=ranked,
            best_pick=ranked[0] if ranked else None,
            cheapest_gpu=cheapest,
            cloud_offerings=cloud_offerings,
            warnings=engine_result.warnings,
            knowledge_recommendations=engine_result.recommendations,
            sources=engine_result.sources,
        )

    def _perf_by_id(self, gpus) -> dict[str, tuple[float, bool]]:
        """Map gpu_id -> (performance metric, is_from_benchmark).

        Uses measured relative training throughput (A100 = 1.0) when available;
        otherwise converts peak FP16 TFLOPS to the same reference scale so all
        GPUs are comparable.
        """
        perf: dict[str, tuple[float, bool]] = {}
        for gpu in gpus:
            measured = self._benchmarks.relative_throughput(gpu.id)
            if measured is not None:
                perf[gpu.id] = (measured, True)
            else:
                perf[gpu.id] = (gpu.tflops_fp16 / REFERENCE_TFLOPS_FP16, False)
        return perf

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

    def _attach_cost_estimates(
        self,
        candidates: list[GPUCandidate],
        request: GPURecommendationRequest,
    ) -> list[GPUCandidate]:
        from app.core.calculators.cost.models import CostEstimateRequest, DeploymentType

        deployment = DeploymentType(request.deployment)
        updated: list[GPUCandidate] = []

        for candidate in candidates:
            cost_request = CostEstimateRequest(
                parameter_count=request.parameter_count,
                gpu_id=candidate.gpu.id,
                epochs=request.epochs,
                dataset_samples=request.dataset_samples,
                dataset_size_gb=request.dataset_size_gb,
                batch_size=request.batch_size,
                model_type=request.model_type.value,
                deployment=deployment,
                cloud_provider=self._default_provider_for_gpu(candidate.gpu.id),
            )
            try:
                cost = self.cost_calculator.estimate(cost_request)
                candidate.cost_estimate = cost
                candidate.reasons.append(f"Est. cost: ${cost.total_usd:.2f} ({cost.estimated_hours:.1f}h)")
            except Exception as exc:
                logger.warning("Cost estimate failed for %s: %s", candidate.gpu.id, exc)
            updated.append(candidate)

        return updated

    @staticmethod
    def _apply_cost_value_boost(candidates: list[GPUCandidate]) -> list[GPUCandidate]:
        """Blend cloud/local cost into score so cheaper capable GPUs can beat expensive ones."""
        with_cost = [c for c in candidates if c.cost_estimate is not None]
        if len(with_cost) < 2:
            return candidates

        totals = [c.cost_estimate.total_usd for c in with_cost]  # type: ignore[union-attr]
        min_c, max_c = min(totals), max(totals)
        if max_c <= min_c:
            return candidates

        for candidate in with_cost:
            total = candidate.cost_estimate.total_usd  # type: ignore[union-attr]
            cost_norm = 1.0 - (total - min_c) / (max_c - min_c)
            candidate.score = round(min(1.0, candidate.score * 0.7 + cost_norm * 0.3), 3)
            candidate.reasons.append(f"Value-adjusted for est. training cost ${total:.2f}")

        return sorted(candidates, key=lambda c: (-c.score, c.cost_estimate.total_usd if c.cost_estimate else 1e9))

    @staticmethod
    def _default_provider_for_gpu(gpu_id: str) -> str | None:
        defaults = {
            "rtx-3090": "runpod",
            "rtx-4090": "runpod",
            "rtx-4080": "runpod",
            "rtx-5080": "runpod",
            "rtx-5090": "runpod",
            "rx-7900-xt": "runpod",
            "rx-7900-xtx": "runpod",
            "l40s": "runpod",
            "a40": "runpod",
            "rtx-a6000": "lambda",
            "a100-40gb": "runpod",
            "a100-80gb": "runpod",
            "h100-80gb": "runpod",
            "h200": "coreweave",
            "b200": "coreweave",
            "mi210": "azure",
            "mi250x": "azure",
            "mi300x": "azure",
            "mi325x": "azure",
            "mi350x": "tensorwave",
            "mi355x": "tensorwave",
            "t4": "gcp",
            "l4": "gcp",
            "gh200": "coreweave",
            "b300": "coreweave",
            "gb200": "coreweave",
            "h100-nvl": "runpod",
            "rtx-pro-6000": "runpod",
            "l40": "runpod",
            "rtx-a5000": "runpod",
            "rtx-6000-ada": "runpod",
            "rtx-5070-ti": "runpod",
            "w7900": "runpod",
        }
        return defaults.get(gpu_id)
