"""Train the XGBoost Training-Duration Predictor.

Target: log10(training hours). Why log?
  Durations span 6 minutes to 300 days (5 orders of magnitude). In raw hours,
  the loss would be dominated by the giant runs and being "off by 100h" on a
  30-minute job would look the same as on a 3-month job. In log space, errors
  are multiplicative: predicting 2x too long costs the same everywhere.

Evaluation metric: median (and p90) prediction ratio error, i.e.
  ratio = 10 ** |pred_log - true_log|
  "median 1.8x" means half of predictions are within 1.8x of the true time.
  For pre-execution estimates, within ~2x is genuinely useful.

Usage:
    python ml/prep_dataset.py --augment
    python ml/train_duration.py
Artifacts:
    backend/app/core/predictors/duration/artifacts/duration_xgb.json
    backend/app/core/predictors/duration/artifacts/metrics.json
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
import xgboost as xgb

REPO = Path(__file__).resolve().parents[1]
DATA = REPO / "data" / "processed" / "duration_train.csv"
ART = REPO / "backend" / "app" / "core" / "predictors" / "duration" / "artifacts"

FEATURES = [
    "log_params", "log_dataset", "log_flops", "log_n_gpu",
    "log_peak_flops", "theo_log_hours",
    # domain one-hots appended below
]
DOMAINS = ["language", "vision", "multimodal", "image generation", "biology", "other"]


def featurize(df: pd.DataFrame) -> pd.DataFrame:
    X = df[["log_params", "log_dataset", "log_flops", "log_n_gpu",
            "log_peak_flops", "theo_log_hours"]].copy()
    for d in DOMAINS:
        X[f"dom_{d.replace(' ', '_')}"] = (df["domain"] == d).astype(int)
    return X


def ratio_errors(y_true: np.ndarray, y_pred: np.ndarray) -> dict:
    r = 10 ** np.abs(y_pred - y_true)
    return {
        "median_ratio": float(np.median(r)),
        "p90_ratio": float(np.percentile(r, 90)),
        "within_2x_pct": float((r <= 2).mean() * 100),
        "within_3x_pct": float((r <= 3).mean() * 100),
    }


def main() -> None:
    df = pd.read_csv(DATA)
    X, y, w = featurize(df), df["target_log_hours"], df["weight"]

    # Hold out REAL rows only, split BY ORGANIZATION (grouped split): all runs
    # from one org stay on the same side. A random split leaks model-family
    # information (GPT-3 in train, GPT-3.5 in test) and reported ~2x-optimistic
    # p90 in our 2026-07-09 audit. Synthetic rows always train, never test.
    rng = np.random.default_rng(42)
    real = df[df["source"] == "epoch"]
    orgs = rng.permutation(real["org"].unique())
    test_orgs, count = set(), 0
    for org in orgs:
        test_orgs.add(org)
        count += int((real["org"] == org).sum())
        if count >= 0.2 * len(real):
            break
    idx_test = real.index[real["org"].isin(test_orgs)]
    idx_train = real.index.difference(idx_test).union(
        df.index[df["source"] == "synthetic"])

    # native xgboost API (no sklearn dependency needed)
    dtrain = xgb.DMatrix(X.loc[idx_train], label=y.loc[idx_train],
                         weight=w.loc[idx_train])
    dtest = xgb.DMatrix(X.loc[idx_test])
    params = {
        "max_depth": 4,        # shallow trees: ~400 real rows, deep trees overfit
        "eta": 0.05,
        "subsample": 0.8,
        "colsample_bytree": 0.8,
        "lambda": 2.0,
        "objective": "reg:squarederror",
        "seed": 42,
    }
    model = xgb.train(params, dtrain, num_boost_round=400)

    m = {
        "split": "grouped-by-organization (leak-resistant)",
        "n_train": int(len(idx_train)),
        "n_test_real": int(len(idx_test)),
        "test": ratio_errors(y.loc[idx_test].values, model.predict(dtest)),
        "features": list(X.columns),
    }

    # Baseline: pure physics formula (no ML) on the same test rows
    theo = df.loc[idx_test, "theo_log_hours"].values
    mask = ~np.isnan(theo)
    m["baseline_formula"] = ratio_errors(y.loc[idx_test].values[mask], theo[mask])
    m["model_on_same_subset"] = ratio_errors(
        y.loc[idx_test].values[mask], model.predict(dtest)[mask])

    ART.mkdir(parents=True, exist_ok=True)
    model.save_model(str(ART / "duration_xgb.json"))
    (ART / "metrics.json").write_text(json.dumps(m, indent=2))
    print(json.dumps(m, indent=2))
    print(f"\nsaved: {ART / 'duration_xgb.json'}")


if __name__ == "__main__":
    main()
