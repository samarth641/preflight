"""Training cost calculator."""

from __future__ import annotations

from app.core.calculators.cost.models import (
    CostBreakdown,
    CostEstimateRequest,
    CostEstimateResult,
    DeploymentType,
)
from app.core.calculators.cost.pricing import PricingRegistry
from app.core.recommenders.gpu.registry import GPURegistry

MODEL_TYPE_FACTOR = {"transformer": 1.0, "vision": 0.4, "cnn": 0.3}
HARDWARE_LIFETIME_HOURS = 20_000  # amortization over ~2.3 years heavy use


class CostCalculator:
    """Estimates cloud, electricity, storage, bandwidth, and training time."""

    def __init__(
        self,
        gpu_registry: GPURegistry | None = None,
        pricing_registry: PricingRegistry | None = None,
    ) -> None:
        self._gpu_registry = gpu_registry or GPURegistry()
        self._pricing = pricing_registry or PricingRegistry()

    def estimate(self, request: CostEstimateRequest) -> CostEstimateResult:
        gpu = self._gpu_registry.get(request.gpu_id)
        if gpu is None:
            raise ValueError(f"Unknown GPU id: {request.gpu_id}")

        defaults = self._pricing.defaults
        baseline = self._pricing.baseline
        electricity_rate = request.electricity_usd_per_kwh or defaults.get("electricity_usd_per_kwh", 0.12)

        seconds_per_epoch = self._estimate_seconds_per_epoch(request, gpu.tflops_fp16, baseline)
        total_hours = (seconds_per_epoch * request.epochs * request.gpu_count) / 3600
        total_days = round(total_hours / 24, 2)

        dataset_gb = request.dataset_size_gb or self._estimate_dataset_gb(request.dataset_samples)
        storage_rate = defaults.get("storage_usd_per_gb_month", 0.023)
        bandwidth_rate = defaults.get("bandwidth_usd_per_gb", 0.09)

        storage_usd = round(dataset_gb * storage_rate, 2)
        bandwidth_usd = round(dataset_gb * bandwidth_rate, 2) if request.deployment == DeploymentType.CLOUD else 0.0

        notes: list[str] = []
        hourly_rate: float | None = None
        cloud_usd = 0.0
        electricity_usd = 0.0
        hardware_amortization_usd = 0.0

        if request.deployment == DeploymentType.CLOUD:
            hourly_rate = self._pricing.cloud_hourly_rate(request.gpu_id, request.cloud_provider)
            if hourly_rate is None:
                notes.append("No cloud pricing for this GPU — using electricity estimate only.")
                power_kw = (gpu.power_watts * request.gpu_count) / 1000
                electricity_usd = round(power_kw * total_hours * electricity_rate, 2)
            else:
                cloud_usd = round(hourly_rate * total_hours, 2)
        else:
            power_kw = (gpu.power_watts * request.gpu_count) / 1000
            electricity_usd = round(power_kw * total_hours * electricity_rate, 2)
            if gpu.msrp_usd:
                hardware_amortization_usd = round(
                    (gpu.msrp_usd * request.gpu_count / HARDWARE_LIFETIME_HOURS) * total_hours, 2
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
            estimated_hours=round(total_hours, 2),
            estimated_days=total_days,
            seconds_per_epoch=round(seconds_per_epoch, 1),
            breakdown=breakdown,
            total_usd=total,
            hourly_rate_usd=hourly_rate,
            notes=notes,
        )

    @staticmethod
    def _estimate_seconds_per_epoch(
        request: CostEstimateRequest,
        gpu_tflops: float,
        baseline: dict,
    ) -> float:
        ref_params = baseline.get("parameter_count_billion", 7.0)
        ref_tflops = baseline.get("reference_tflops_fp16", 312)
        ref_seconds = baseline.get("seconds_per_epoch", 3600)
        ref_samples = baseline.get("dataset_samples", 10_000)
        ref_batch = baseline.get("batch_size", 8)

        params_b = request.parameter_count / 1_000_000_000
        param_factor = (params_b / ref_params) ** 0.75
        speed_factor = ref_tflops / max(gpu_tflops, 1.0)
        dataset_factor = max(1.0, request.dataset_samples / ref_samples) ** 0.35
        batch_factor = ref_batch / request.batch_size
        model_factor = MODEL_TYPE_FACTOR.get(request.model_type, 1.0)

        return ref_seconds * param_factor * speed_factor * dataset_factor * batch_factor * model_factor

    @staticmethod
    def _estimate_dataset_gb(samples: int, avg_mb_per_image: float = 0.5) -> float:
        return round(samples * avg_mb_per_image / 1024, 2)
