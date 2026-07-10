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
    perf_value: float,
    max_perf: float,
    perf_from_benchmark: bool = False,
) -> GPUCandidate | None:
    """Score a GPU against requirements. Returns None if VRAM is insufficient.

    ``perf_value`` is the GPU's performance metric on a shared scale (measured
    relative training throughput when available, else TFLOPS converted to the same
    reference scale). ``max_perf`` is the best value across candidates.
    """
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

    # VRAM fit: sweet spot 40-85%. Extra VRAM is headroom, not a hard penalty —
    # otherwise high-VRAM AMD cards (MI300X, 7900 XTX) lose to smaller NVIDIA GPUs.
    if 0.4 <= utilization <= 0.85:
        vram_score = 1.0
        reasons.append("Good VRAM fit — efficient utilization")
    elif utilization < 0.4:
        # Soft floor so large-VRAM value GPUs stay competitive
        vram_score = max(0.65, 0.95 - (0.4 - utilization) * 0.6)
        if utilization < 0.15:
            reasons.append("Large VRAM headroom — useful for bigger batches; check cloud $/hr vs smaller GPUs")
        else:
            reasons.append("Extra VRAM headroom — room to grow batch size")
    else:
        vram_score = max(0.45, 0.8 - (utilization - 0.85) * 2)
        reasons.append("Tight VRAM fit — limited headroom for larger batches")

    perf_score = perf_value / max_perf if max_perf > 0 else 0.5
    if perf_from_benchmark:
        reasons.append("Ranked on measured training throughput (benchmark)")
    efficiency_score = min(1.0, perf_score / max(gpu.power_watts / 200, 0.5))

    vendor_score = 1.0
    if request.preferred_vendor:
        vendor_score = 1.0 if gpu.vendor == request.preferred_vendor else 0.6
        if gpu.vendor != request.preferred_vendor:
            reasons.append(f"Not preferred vendor ({request.preferred_vendor})")

    tier_score = _tier_score(gpu.training_speed_tier, request.budget_tier)
    if request.budget_tier and tier_score < 0.8:
        reasons.append(f"Tier '{gpu.training_speed_tier}' may exceed budget '{request.budget_tier.value}'")

    # Light MSRP value signal so cheaper cards aren't buried by peak TFLOPS alone
    value_score = _msrp_value_score(gpu.msrp_usd)

    if gpu.vendor == "nvidia":
        reasons.append("Full CUDA ecosystem support")
    elif gpu.vendor == "amd":
        reasons.append("ROCm support — verify framework compatibility")

    score = (
        vram_score * 0.35
        + perf_score * 0.20
        + efficiency_score * 0.10
        + vendor_score * 0.10
        + tier_score * 0.10
        + value_score * 0.15
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
    # Only extreme under-use is "overkill" (was 0.35 — punished AMD 192GB unfairly)
    if utilization < 0.12:
        return FitRating.OVERKILL
    if 0.4 <= utilization <= 0.85:
        return FitRating.EXCELLENT
    return FitRating.GOOD


def _msrp_value_score(msrp_usd: float | None) -> float:
    """Map purchase price to 0–1 where cheaper is better. Unknown MSRP → neutral."""
    if not msrp_usd or msrp_usd <= 0:
        return 0.7
    # Log-ish curve: $500 → ~1.0, $2000 → ~0.7, $15000 → ~0.35, $30000 → ~0.25
    if msrp_usd <= 500:
        return 1.0
    if msrp_usd <= 2000:
        return 1.0 - (msrp_usd - 500) / 1500 * 0.3
    if msrp_usd <= 15000:
        return 0.7 - (msrp_usd - 2000) / 13000 * 0.35
    return max(0.2, 0.35 - (msrp_usd - 15000) / 30000 * 0.15)


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
