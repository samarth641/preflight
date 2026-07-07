"""VRAM requirement estimation heuristics."""

from __future__ import annotations

from app.core.recommenders.gpu.models import GPURecommendationRequest, ModelType, TrainingMode

# Approximate bytes per parameter for different training modes and precisions.
# Sources: PyTorch memory profiling guides, Hugging Face performance docs.
BYTES_PER_PARAM: dict[str, dict[TrainingMode, float]] = {
    "fp32": {
        TrainingMode.FULL: 16.0,
        TrainingMode.LORA: 4.0,
        TrainingMode.INFERENCE: 4.0,
    },
    "fp16": {
        TrainingMode.FULL: 10.0,
        TrainingMode.LORA: 2.5,
        TrainingMode.INFERENCE: 2.0,
    },
    "int8": {
        TrainingMode.FULL: 6.0,
        TrainingMode.LORA: 1.5,
        TrainingMode.INFERENCE: 1.0,
    },
}

ACTIVATION_FACTOR: dict[ModelType, float] = {
    ModelType.VISION: 0.5,
    ModelType.CNN: 0.3,
    ModelType.TRANSFORMER: 2.0,
}


def estimate_vram_gb(request: GPURecommendationRequest) -> float:
    """Estimate VRAM required for training/inference.

    Uses parameter count, precision, training mode, and activation memory heuristics.
    """
    assert request.parameter_count is not None

    precision = request.precision
    mode = request.training_mode
    bytes_per_param = BYTES_PER_PARAM.get(precision, BYTES_PER_PARAM["fp16"])[mode]

    model_memory_gb = (request.parameter_count * bytes_per_param) / (1024**3)

    activation_gb = _estimate_activation_memory(request)
    overhead_gb = 1.5

    if mode == TrainingMode.LORA:
        overhead_gb += 0.5

    total = model_memory_gb + activation_gb + overhead_gb
    return round(max(total, 0.5), 2)


def _estimate_activation_memory(request: GPURecommendationRequest) -> float:
    """Estimate activation memory based on model type and batch size."""
    batch = request.batch_size
    factor = ACTIVATION_FACTOR[request.model_type]

    if request.model_type == ModelType.TRANSFORMER:
        seq = request.sequence_length
        hidden_estimate = min(request.parameter_count / seq / 1000, 8192)
        activation_bytes = batch * seq * hidden_estimate * factor * 4
    elif request.model_type == ModelType.VISION:
        pixels = request.image_size**2
        activation_bytes = batch * pixels * 3 * factor * 4 / 1_000_000
    else:
        activation_bytes = batch * request.image_size * request.image_size * factor * 4 / 2_000_000

    return activation_bytes / (1024**3)
