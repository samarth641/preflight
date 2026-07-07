"""GPU scoring and ranking logic."""

from __future__ import annotations

from app.core.recommenders.gpu.models import (
    BudgetTier,
    FitRating,
    GPUCandidate,
    GPURecommendationRequest,
    GPUSpec,
)

TIER_ORDER = ["entry", "mid", "high", "enthusiast", "datacenter"]


def score_gpu(
    gpu: GPUSpec,
    required_vram_gb: float,
    request: GPURecommendationRequest,
    max_tflops: float,
) -> GPUCandidate | None:
    """Score a GPU against requirements. Returns None if VRAM is insufficient."""
    headroom = gpu.vram_gb - required_vram_gb
    if headroom < 0:
        return GPUCandidate(
            gpu=gpu,
            score=0.0,
            fit_rating=FitRating.INSUFFICIENT,
            vram_utilization=round(required_vram_gb / gpu.vram_gb, 2),
            headroom_gb=round(headroom, 1),
            reasons=[f"Insufficient VRAM: needs {required_vram_gb}GB, has {gpu.vram_gb}GB"],
        )

    utilization = required_vram_gb / gpu.vram_gb
    fit_rating = _fit_rating(utilization, headroom)
    reasons: list[str] = []

    # VRAM fit score: sweet spot is 50-85% utilization
    if 0.5 <= utilization <= 0.85:
        vram_score = 1.0
        reasons.append("Good VRAM fit — efficient utilization")
    elif utilization < 0.5:
        vram_score = 0.7 - (0.5 - utilization) * 0.4
        reasons.append("More VRAM than needed — consider a cheaper GPU")
    else:
        vram_score = 0.8 - (utilization - 0.85) * 2
        reasons.append("Tight VRAM fit — limited headroom for larger batches")

    perf_score = gpu.tflops_fp16 / max_tflops if max_tflops > 0 else 0.5
    efficiency_score = perf_score / max(gpu.power_watts / 200, 0.5)

    vendor_score = 1.0
    if request.preferred_vendor:
        vendor_score = 1.0 if gpu.vendor == request.preferred_vendor else 0.6
        if gpu.vendor != request.preferred_vendor:
            reasons.append(f"Not preferred vendor ({request.preferred_vendor})")

    tier_score = _tier_score(gpu.training_speed_tier, request.budget_tier)
    if request.budget_tier and tier_score < 0.8:
        reasons.append(f"Tier '{gpu.training_speed_tier}' may exceed budget '{request.budget_tier.value}'")

    if gpu.vendor == "nvidia":
        reasons.append("Full CUDA ecosystem support")
    elif gpu.vendor == "amd":
        reasons.append("ROCm support — verify framework compatibility")

    score = (
        vram_score * 0.40
        + perf_score * 0.25
        + efficiency_score * 0.10
        + vendor_score * 0.10
        + tier_score * 0.15
    )

    if fit_rating == FitRating.INSUFFICIENT:
        score = 0.0

    return GPUCandidate(
        gpu=gpu,
        score=round(min(1.0, max(0.0, score)), 3),
        fit_rating=fit_rating,
        vram_utilization=round(utilization, 2),
        headroom_gb=round(headroom, 1),
        reasons=reasons,
    )


def _fit_rating(utilization: float, headroom_gb: float) -> FitRating:
    if headroom_gb < 0:
        return FitRating.INSUFFICIENT
    if utilization > 0.9:
        return FitRating.TIGHT
    if utilization < 0.35:
        return FitRating.OVERKILL
    if 0.5 <= utilization <= 0.85:
        return FitRating.EXCELLENT
    return FitRating.GOOD


def _tier_score(gpu_tier: str, budget: BudgetTier | None) -> float:
    if budget is None:
        return 0.8

    budget_index = TIER_ORDER.index(budget.value) if budget.value in TIER_ORDER else 2
    gpu_index = TIER_ORDER.index(gpu_tier) if gpu_tier in TIER_ORDER else 2
    distance = abs(gpu_index - budget_index)

    if distance == 0:
        return 1.0
    if distance == 1:
        return 0.75
    if distance == 2:
        return 0.5
    return 0.25
