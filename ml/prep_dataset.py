"""Prepare the training dataset for the Duration Predictor.

Reads Epoch AI's all_ai_models.csv (real training runs) and produces a clean
feature table. Optionally augments with physics-derived synthetic rows so that
AMD + consumer GPUs (nearly absent from Epoch data) are represented.

Key idea (the "physics prior"):
    theoretical_hours = training_FLOPs / (n_gpu * peak_FLOPS * MFU)
  - training_FLOPs ~= 6 * params * tokens for transformers (the "6ND" rule)
  - MFU (Model FLOPs Utilization) is how much of the GPU's peak you actually
    get. Real-world MFU is ~0.2-0.45. The ML model's job is to learn the
    residual between this naive formula and reality.

Usage:
    python ml/prep_dataset.py            # real rows only
    python ml/prep_dataset.py --augment  # + synthetic AMD/consumer rows
"""
from __future__ import annotations

import argparse
import math
from pathlib import Path

import numpy as np
import pandas as pd

REPO = Path(__file__).resolve().parents[1]
RAW = REPO / "data" / "raw"
OUT = REPO / "data" / "processed"

# Fallback peak FP16 FLOPS (in FLOP/s) for hardware names appearing in Epoch
# data, used when ml_hardware.csv is not available. Sources: vendor datasheets.
FALLBACK_PEAK_FP16 = {
    "NVIDIA A100": 312e12,
    "NVIDIA A100 SXM4 40 GB": 312e12,
    "NVIDIA A100 SXM4 80 GB": 312e12,
    "NVIDIA V100": 125e12,
    "NVIDIA Tesla V100 DGXS 32 GB": 125e12,
    "NVIDIA Tesla V100S PCIe 32 GB": 130e12,
    "NVIDIA H100 SXM5 80GB": 990e12,   # dense FP16/BF16
    "NVIDIA H800 SXM5": 990e12,
    "NVIDIA GeForce GTX 1080 Ti": 11e12,   # no tensor cores; FP32-ish
    "NVIDIA GeForce RTX 3090": 71e12,
    "NVIDIA GeForce RTX 4090": 165e12,
    "NVIDIA P100": 19e12,
    "NVIDIA Quadro RTX 5000": 89e12,
    "Google TPU v2": 46e12,
    "Google TPU v3": 123e12,
    "Google TPU v4": 275e12,
    "Google TPU v5p": 459e12,
    "AMD Radeon Instinct MI250X": 383e12,
    "AMD Instinct MI300X": 1307e12,
}


def load_hardware_specs() -> dict[str, float]:
    """Peak FP16 FLOP/s per hardware name; ml_hardware.csv overrides fallback."""
    specs = dict(FALLBACK_PEAK_FP16)
    hw_csv = RAW / "gpu_specs" / "ml_hardware.csv"
    if hw_csv.exists():
        hw = pd.read_csv(hw_csv)
        # Prefer tensor-FP16/BF16 peak; fall back to plain FP16 then FP32.
        for _, r in hw.iterrows():
            peak = (
                r.get("Tensor-FP16/BF16 performance (FLOP/s)")
                or r.get("FP16 (half precision) performance (FLOP/s)")
                or r.get("FP32 (single precision) performance (FLOP/s)")
            )
            if pd.notna(peak) and peak:
                specs[str(r["Hardware name"]).strip()] = float(peak)
        print(f"hardware specs: {len(specs)} entries (ml_hardware.csv loaded)")
    else:
        print(f"hardware specs: {len(specs)} fallback entries "
              f"(ml_hardware.csv NOT found at {hw_csv})")
    return specs


def build_real_rows(specs: dict[str, float]) -> pd.DataFrame:
    df = pd.read_csv(RAW / "epoch_ai" / "all_ai_models.csv")

    # some numeric columns arrive as strings (mixed-type CSV) — coerce hard
    for col in ["Parameters", "Training dataset size (total)",
                "Training compute (FLOP)", "Training time (hours)",
                "Hardware quantity"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    df = df[df["Training time (hours)"].notna() & df["Parameters"].notna()].copy()

    df["peak_flops"] = df["Training hardware"].map(specs)
    df["n_gpu"] = df["Hardware quantity"]

    # Label sanity filter: drop rows whose implied MFU (Model FLOPs Utilization
    # = achieved / peak throughput) exceeds 1.0 — physically impossible, so the
    # reported time, hardware count, or compute must be wrong. ~28 rows (~11%
    # of rows where computable) fail this. Audit 2026-07-09.
    flops_tmp = df["Training compute (FLOP)"].fillna(
        6.0 * df["Parameters"] * df["Training dataset size (total)"])
    implied_mfu = flops_tmp / (df["Training time (hours)"] * 3600.0
                               * df["n_gpu"] * df["peak_flops"])
    df = df[~(implied_mfu > 1.0).fillna(False)].copy()

    # training FLOPs: prefer reported, else 6 * params * tokens
    six_nd = 6.0 * df["Parameters"] * df["Training dataset size (total)"]
    df["flops"] = df["Training compute (FLOP)"].fillna(six_nd)

    dom = df["Domain"].fillna("").str.split(",").str[0].str.strip().str.lower()
    df["domain"] = dom.where(dom.isin(["language", "vision", "multimodal",
                                       "image generation", "biology"]), "other")

    out = pd.DataFrame({
        "log_params": np.log10(df["Parameters"]),
        "log_dataset": np.log10(df["Training dataset size (total)"]),
        "log_flops": np.log10(df["flops"]),
        "log_n_gpu": np.log10(df["n_gpu"]),
        "log_peak_flops": np.log10(df["peak_flops"]),
        "domain": df["domain"],
        "target_log_hours": np.log10(df["Training time (hours)"]),
        "source": "epoch",
        "weight": 1.0,
        # organization: used for GROUPED train/test splits (all runs from one
        # org stay on the same side, else model families leak across the split)
        "org": df["Organization"].fillna("unknown").str.split(",").str[0],
    })
    # theoretical duration feature where computable (MFU assumed 0.35)
    out["theo_log_hours"] = (
        out["log_flops"]
        - out["log_n_gpu"]
        - out["log_peak_flops"]
        - math.log10(0.35)
        - math.log10(3600.0)
    )
    print(f"real rows: {len(out)} "
          f"(with full physics feature: {out['theo_log_hours'].notna().sum()})")
    return out


def build_synthetic_rows(n: int = 600, seed: int = 42) -> pd.DataFrame:
    """Physics-derived rows over the app's GPU vocabulary (gpus.yaml specs).

    Covers AMD + consumer GPUs and the small-model regime that Epoch data
    lacks. Duration = FLOPs / (n_gpu * peak * MFU) with noisy MFU in [0.2, 0.45]
    so the model doesn't learn a fake perfect formula.
    """
    import yaml

    rng = np.random.default_rng(seed)
    gpus = yaml.safe_load((REPO / "knowledge" / "hardware" / "gpus.yaml").read_text())
    gpu_rows = [g for g in gpus["gpus"] if "tflops_fp16" in g]

    recs = []
    for _ in range(n):
        g = gpu_rows[rng.integers(len(gpu_rows))]
        peak = g["tflops_fp16"] * 1e12
        params = 10 ** rng.uniform(6.5, 10.5)        # 3M .. 30B params
        tokens = params * 10 ** rng.uniform(0.5, 2)  # 3x .. 100x params (tokens)
        n_gpu = float(rng.choice([1, 1, 1, 2, 4, 8]))  # skew to single-GPU
        flops = 6.0 * params * tokens
        mfu = rng.uniform(0.20, 0.45)
        hours = flops / (n_gpu * peak * mfu) / 3600.0
        if not (0.05 <= hours <= 20000):
            continue
        recs.append({
            "log_params": math.log10(params),
            "log_dataset": math.log10(tokens),
            "log_flops": math.log10(flops),
            "log_n_gpu": math.log10(n_gpu),
            "log_peak_flops": math.log10(peak),
            "domain": rng.choice(["language", "vision", "other"]),
            "target_log_hours": math.log10(hours),
            "source": "synthetic",
            "weight": 0.3,   # real rows count ~3x more in training
            "org": "synthetic",
        })
    df = pd.DataFrame(recs)
    df["theo_log_hours"] = (
        df["log_flops"] - df["log_n_gpu"] - df["log_peak_flops"]
        - math.log10(0.35) - math.log10(3600.0)
    )
    print(f"synthetic rows: {len(df)}")
    return df


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--augment", action="store_true")
    args = ap.parse_args()

    specs = load_hardware_specs()
    parts = [build_real_rows(specs)]
    if args.augment:
        parts.append(build_synthetic_rows())

    full = pd.concat(parts, ignore_index=True)
    OUT.mkdir(parents=True, exist_ok=True)
    dest = OUT / "duration_train.csv"
    full.to_csv(dest, index=False)
    print(f"wrote {dest} ({len(full)} rows)")


if __name__ == "__main__":
    main()
