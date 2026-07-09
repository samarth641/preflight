"""Training cost calculator."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import TYPE_CHECKING, Any

import yaml

from app.core.calculators.cost.models import (
    CostBreakdown,
    CostEstimateRequest,
    CostEstimateResult,
    DeploymentType,
)
from app.core.calculators.cost.pricing import PricingRegistry

if TYPE_CHECKING:
    from app.core.recommenders.gpu.benchmarks import BenchmarkRegistry
    from app.core.recommenders.gpu.registry import GPURegistry

logger = logging.getLogger(__name__)

MODEL_TYPE_FACTOR = {"transformer": 1.0, "vision": 0.4, "cnn": 0.3}
HARDWARE_LIFETIME_HOURS = 20_000  # amortization over ~2.3 years heavy use

# Default duration-formula exponents. These are the hand-tuned baseline that
# ships out of the box; scripts/calibrate_duration.py can fit better ones from
# real runs and drop them into knowledge/hardware/duration_calibration.yaml,
# which overrides these without any code change. Batch size is intentionally
# excluded (it cancels out at fixed throughput), matching the linear perf model.
DEFAULT_PARAM_EXPONENT = 0.75
DEFAULT_DATASET_EXPONENT = 1.0  # linear in dataset size
DEFAULT_SPEED_EXPONENT = 1.0


class DurationCalibration:
    """Optional data-fitted overrides for the duration formula constants.

    When knowledge/hardware/duration_calibration.yaml exists it supplies
    calibrated exponents / model factors; otherwise every accessor returns the
    shipped default, so the formula behaves exactly as before.
    """

    def __init__(self, data: dict[str, Any] | None = None) -> None:
        self._data = data or {}

    @classmethod
    def load(cls, knowledge_root: Path | str) -> "DurationCalibration":
        path = Path(knowledge_root) / "hardware" / "duration_calibration.yaml"
        if not path.exists():
            return cls(None)
        try:
            return cls(yaml.safe_load(path.read_text(encoding="utf-8")) or {})
        except Exception:  # pragma: no cover - defensive: never break estimation
            logger.warning("Failed to read %s; using default duration constants.", path)
            return cls(None)

    @property
    def active(self) -> bool:
        return bool(self._data)

    @property
    def param_exponent(self) -> float:
        return float(self._data.get("param_exponent", DEFAULT_PARAM_EXPONENT))

    @property
    def dataset_exponent(self) -> float:
        return float(self._data.get("dataset_exponent", DEFAULT_DATASET_EXPONENT))

    @property
    def speed_exponent(self) -> float:
        return float(self._data.get("speed_exponent", DEFAULT_SPEED_EXPONENT))

    def reference_seconds(self, formula_default: float) -> float:
        return float(self._data.get("reference_seconds_per_epoch", formula_default))

    def model_factor(self, model_type: str) -> float:
        factors = self._data.get("model_type_factor")
        if factors and model_type in factors:
            return float(factors[model_type])
        return MODEL_TYPE_FACTOR.get(model_type, 1.0)

# Multi-GPU wall-clock scaling. Data-parallel training is sub-linear because of
# gradient-sync communication, so N GPUs give ~N**0.95 effective parallelism
# (1->1.0, 2->1.93, 8->7.2), not a perfect Nx speedup.
MULTI_GPU_SCALING_EXP = 0.95


class CostCalculator:
    """Estimates cloud, electricity, storage, bandwidth, and training time."""

    def __init__(
        self,
        gpu_registry: "GPURegistry | None" = None,
        pricing_registry: PricingRegistry | None = None,
        benchmark_registry: "BenchmarkRegistry | None" = None,
    ) -> None:
        # Lazy imports break the recommenders <-> calculators import cycle.
        from app.core.recommenders.gpu.benchmarks import BenchmarkRegistry
        from app.core.recommenders.gpu.registry import GPURegistry

        self._gpu_registry = gpu_registry or GPURegistry()
        self._pricing = pricing_registry or PricingRegistry()
        self._benchmarks = benchmark_registry or BenchmarkRegistry(self._gpu_registry.knowledge_root)
        self._calibration = DurationCalibration.load(self._gpu_registry.knowledge_root)

    def estimate(self, request: CostEstimateRequest) -> CostEstimateResult:
        gpu = self._gpu_registry.get(request.gpu_id)
        if gpu is None:
            raise ValueError(f"Unknown GPU id: {request.gpu_id}")

        defaults = self._pricing.defaults
        baseline = self._pricing.baseline
        electricity_rate = request.electricity_usd_per_kwh or defaults.get("electricity_usd_per_kwh", 0.12)

        # Single-GPU wall-clock per epoch, then reduce by (sub-linear) GPU parallelism.
        single_gpu_seconds, speed_note = self._estimate_seconds_per_epoch(request, gpu, baseline)
        parallelism = request.gpu_count ** MULTI_GPU_SCALING_EXP
        seconds_per_epoch = single_gpu_seconds / parallelism

        wall_clock_hours = (seconds_per_epoch * request.epochs) / 3600
        gpu_hours = wall_clock_hours * request.gpu_count  # billing / energy basis
        total_days = round(wall_clock_hours / 24, 2)

        dataset_gb = request.dataset_size_gb or self._estimate_dataset_gb(request.dataset_samples)
        storage_rate = defaults.get("storage_usd_per_gb_month", 0.023)
        bandwidth_rate = defaults.get("bandwidth_usd_per_gb", 0.09)

        storage_usd = round(dataset_gb * storage_rate, 2)
        bandwidth_usd = round(dataset_gb * bandwidth_rate, 2) if request.deployment == DeploymentType.CLOUD else 0.0

        notes: list[str] = [speed_note]
        if request.gpu_count > 1:
            notes.append(
                f"{request.gpu_count} GPUs at ~{MULTI_GPU_SCALING_EXP:g} scaling — "
                f"wall-clock {wall_clock_hours:.1f}h, billed as {gpu_hours:.1f} GPU-hours."
            )
        hourly_rate: float | None = None
        cloud_usd = 0.0
        electricity_usd = 0.0
        hardware_amortization_usd = 0.0

        if request.deployment == DeploymentType.CLOUD:
            hourly_rate = self._pricing.cloud_hourly_rate(request.gpu_id, request.cloud_provider)
            if hourly_rate is None:
                notes.append("No cloud pricing for this GPU — using electricity estimate only.")
                # Per-GPU power over total GPU-hours (energy scales with GPU count).
                electricity_usd = round((gpu.power_watts / 1000) * gpu_hours * electricity_rate, 2)
            else:
                # Per-GPU hourly rate billed over total GPU-hours.
                cloud_usd = round(hourly_rate * gpu_hours, 2)
        else:
            electricity_usd = round((gpu.power_watts / 1000) * gpu_hours * electricity_rate, 2)
            if gpu.msrp_usd:
                hardware_amortization_usd = round(
                    (gpu.msrp_usd / HARDWARE_LIFETIME_HOURS) * gpu_hours, 2
                )
            notes.append("Local deployment — cloud cost is zero.")

        breakdown = CostBreakdown(
            cloud_usd=cloud_usd,
            electricity_usd=electricity_usd,
            storage_usd=storage_usd,
            bandwidth_usd=bandwidth_usd,
            hardware_amortization_usd=hardware_amortization_usd,
        )
        total = round(
            breakdown.cloud_usd
            + breakdown.electricity_usd
            + breakdown.storage_usd
            + breakdown.bandwidth_usd
            + breakdown.hardware_amortization_usd,
            2,
        )

        return CostEstimateResult(
            gpu_id=gpu.id,
            gpu_name=gpu.name,
            deployment=request.deployment,
            cloud_provider=request.cloud_provider,
            estimated_hours=round(wall_clock_hours, 2),
            estimated_days=total_days,
            gpu_hours=round(gpu_hours, 2),
            seconds_per_epoch=round(seconds_per_epoch, 1),
            breakdown=breakdown,
            total_usd=total,
            hourly_rate_usd=hourly_rate,
            notes=notes,
        )

    def _estimate_seconds_per_epoch(
        self,
        request: CostEstimateRequest,
        gpu,
        baseline: dict,
    ) -> tuple[float, str]:
        """Empirical single-GPU wall-clock seconds per epoch.

        Follows the linear performance model validated in the literature
        (~80% accuracy): one epoch is one full pass over the data, so time is
        LINEAR in dataset size and inversely proportional to hardware throughput.
        Batch size cancels out at fixed throughput (steps x time/step = samples /
        samples-per-sec), so it is intentionally not a factor here. Utilization
        (MFU) is already baked into the measured throughput term.
        """
        ref_params = baseline.get("parameter_count_billion", 7.0)
        ref_tflops = baseline.get("reference_tflops_fp16", 312)
        ref_samples = baseline.get("dataset_samples", 10_000)
        ref_gpu_id = baseline.get("reference_gpu_id", "a100-80gb")

        cal = self._calibration
        ref_seconds = cal.reference_seconds(baseline.get("seconds_per_epoch", 3600))

        params_b = request.parameter_count / 1_000_000_000
        param_factor = (params_b / ref_params) ** cal.param_exponent  # sub-linear: compute/sample vs params
        dataset_factor = (request.dataset_samples / ref_samples) ** cal.dataset_exponent  # LINEAR by default
        model_factor = cal.model_factor(request.model_type)

        speed_factor_raw, speed_note = self._speed_factor(gpu, ref_gpu_id, ref_tflops)
        speed_factor = speed_factor_raw ** cal.speed_exponent

        seconds = ref_seconds * param_factor * dataset_factor * model_factor * speed_factor
        if cal.active:
            speed_note += " Duration constants data-calibrated."
        return seconds, speed_note

    def _speed_factor(self, gpu, ref_gpu_id: str, ref_tflops: float) -> tuple[float, str]:
        """Prefer measured relative throughput; fall back to peak TFLOPS ratio."""
        gpu_throughput = self._benchmarks.relative_throughput(gpu.id)
        ref_throughput = self._benchmarks.relative_throughput(ref_gpu_id) or self._benchmarks.reference_throughput

        if gpu_throughput and ref_throughput:
            # Higher throughput -> fewer seconds. Reference (A100) throughput anchors ref_seconds.
            factor = ref_throughput / gpu_throughput
            qualifier = "approx. " if self._benchmarks.is_approximate(gpu.id) else ""
            source = self._benchmarks.source(gpu.id) or "benchmark data"
            return factor, f"Training speed from {qualifier}benchmark ({source})."

        factor = ref_tflops / max(gpu.tflops_fp16, 1.0)
        return factor, "Training speed estimated from peak TFLOPS (no benchmark data)."

    @staticmethod
    def _estimate_dataset_gb(samples: int, avg_mb_per_image: float = 0.5) -> float:
        return round(samples * avg_mb_per_image / 1024, 2)
