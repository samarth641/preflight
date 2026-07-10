"""ML Training-Duration Predictor (XGBoost).

Loads the trained model artifact (duration_xgb.json, trained by
ml/train_duration.py) and predicts training duration in hours from the same
features used at training time. GPU peak-FLOPS comes from
knowledge/hardware/gpus.yaml so predictions cover exactly the GPUs the app
supports (including AMD MI300X / RX 7900 XTX).

Cost is derived as: predicted_hours x n_gpus x hourly rate ΓÇö reusing the
existing pricing knowledge (knowledge/hardware/pricing.yaml).
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

import yaml

_ARTIFACT = Path(__file__).parent / "artifacts" / "duration_xgb.json"
_REPO_ROOT = Path(__file__).resolve().parents[5]
_GPUS_YAML = _REPO_ROOT / "knowledge" / "hardware" / "gpus.yaml"

# must match ml/train_duration.py exactly (same order)
_DOMAINS = ["language", "vision", "multimodal", "image generation", "biology", "other"]
_ASSUMED_MFU = 0.35


@dataclass
class DurationRequest:
    parameter_count_billion: float
    dataset_tokens: float           # tokens (LLM) or samples x seq-equivalent
    gpu_id: str                     # id from knowledge/hardware/gpus.yaml
    n_gpus: int = 1
    epochs: int = 1
    domain: str = "language"


@dataclass
class DurationResult:
    estimated_hours: float
    theoretical_hours: float        # pure physics formula, for transparency
    gpu_id: str
    n_gpus: int
    model_version: str = "duration_xgb-v1"


@lru_cache(maxsize=1)
def _gpu_specs() -> dict[str, dict]:
    data = yaml.safe_load(_GPUS_YAML.read_text())
    return {g["id"]: g for g in data["gpus"] if "tflops_fp16" in g}


@lru_cache(maxsize=1)
def _booster():
    import xgboost as xgb

    booster = xgb.Booster()
    booster.load_model(str(_ARTIFACT))
    return booster


class DurationPredictor:
    """Predicts training duration; falls back to the physics formula if the
    ML artifact or xgboost is unavailable (keeps the app demoable always)."""

    def predict(self, req: DurationRequest) -> DurationResult:
        gpu = _gpu_specs().get(req.gpu_id)
        if gpu is None:
            raise ValueError(f"unknown gpu_id '{req.gpu_id}' (see knowledge/hardware/gpus.yaml)")

        params = req.parameter_count_billion * 1e9
        tokens = max(req.dataset_tokens, 1.0) * max(req.epochs, 1)
        flops = 6.0 * params * tokens                      # "6ND" rule
        peak = gpu["tflops_fp16"] * 1e12
        theo_hours = flops / (req.n_gpus * peak * _ASSUMED_MFU) / 3600.0

        try:
            est_hours = self._ml_hours(params, tokens, flops, peak, req, theo_hours)
        except Exception:
            est_hours = theo_hours                          # graceful fallback

        return DurationResult(
            estimated_hours=round(est_hours, 3),
            theoretical_hours=round(theo_hours, 3),
            gpu_id=req.gpu_id,
            n_gpus=req.n_gpus,
        )

    @staticmethod
    def _ml_hours(params: float, tokens: float, flops: float, peak: float,
                  req: DurationRequest, theo_hours: float) -> float:
        import numpy as np
        import xgboost as xgb

        row = [
            math.log10(params),
            math.log10(tokens),
            math.log10(flops),
            math.log10(max(req.n_gpus, 1)),
            math.log10(peak),
            math.log10(theo_hours),
        ]
        dom = req.domain.lower()
        row += [1.0 if dom == d else 0.0 for d in _DOMAINS]

        feature_names = [
            "log_params", "log_dataset", "log_flops", "log_n_gpu",
            "log_peak_flops", "theo_log_hours",
        ] + [f"dom_{d.replace(' ', '_')}" for d in _DOMAINS]

        dmat = xgb.DMatrix(np.array([row]), feature_names=feature_names)
        log_hours = float(_booster().predict(dmat)[0])
        return 10 ** log_hours
