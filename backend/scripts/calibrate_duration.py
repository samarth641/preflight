"""Calibrate the training-duration formula from measured runs.

The cost calculator estimates seconds-per-epoch with a purely *multiplicative*
formula (see ``CostCalculator._estimate_seconds_per_epoch``):

    seconds = ref_seconds
            * (params / ref_params) ** param_exp
            * (samples / ref_samples) ** dataset_exp
            * (ref_throughput / gpu_throughput) ** speed_exp
            * model_factor[model_type]

Taking logs turns this into a *linear* model, so fitting real data is just a
ridge regression in log-space. The current formula is one point in that
hypothesis space (param_exp=0.75, dataset_exp=1.0, speed_exp=1.0), so a fit can
only tie or beat it on the data. Batch size is intentionally excluded — at fixed
throughput it cancels out (steps x time/step = samples / samples-per-sec).

This harness:
  1. Loads a CSV of real runs.
  2. Builds the same log-features the formula uses (reusing BenchmarkRegistry
     + the training baseline from pricing.yaml).
  3. Reports the *existing formula's* error and the *calibrated fit's* error
     under k-fold cross-validation (fair, held-out comparison).
  4. Only recommends promotion if the calibrated fit beats the formula on CV.
  5. Emits calibrated constants ready to drop into
     ``knowledge/hardware/duration_calibration.yaml``.

Pure stdlib — no numpy/sklearn, so it runs anywhere the backend runs.

Usage:
    python backend/scripts/calibrate_duration.py runs.csv
    python backend/scripts/calibrate_duration.py runs.csv --write   # write the YAML if it wins
    python backend/scripts/calibrate_duration.py data/*.csv           # merge multiple schemas
    python backend/scripts/calibrate_duration.py runs.csv --inspect   # show column mapping

Accepts heterogeneous CSV schemas (MLPerf, Kaggle, FlexBench, custom). Column names are
auto-detected — see ``duration_loader.py`` for supported aliases. Minimum required concepts
per row: duration, parameter count, GPU name/id. Dataset samples and model type are inferred
when missing (defaults: 10k samples, transformer).
"""

from __future__ import annotations

import argparse
import csv
import glob
import math
import sys
from pathlib import Path
from typing import Any

# Make the backend package importable when run as a plain script.
BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.core.calculators.cost.calculator import MODEL_TYPE_FACTOR  # noqa: E402
from app.core.calculators.cost.duration_loader import (  # noqa: E402
    detect_column_map,
    load_duration_files,
)
from app.core.calculators.cost.pricing import PricingRegistry  # noqa: E402
from app.core.recommenders.gpu.benchmarks import BenchmarkRegistry  # noqa: E402
from app.core.recommenders.gpu.registry import GPURegistry  # noqa: E402

# Current formula constants (the baseline we must beat to justify calibration).
FORMULA_PARAM_EXP = 0.75
FORMULA_DATASET_EXP = 1.0
FORMULA_SPEED_EXP = 1.0
MAX_PROMOTION_MAPE = 0.35  # refuse --write if calibrated CV MAPE exceeds 35%

MODEL_TYPES_NON_REF = ["vision", "cnn"]  # "transformer" is the reference category
FEATURE_NAMES = ["intercept", "x_param", "x_data", "x_speed", "d_vision", "d_cnn"]


class Run:
    """One measured training run, reduced to the formula's feature space."""

    __slots__ = ("seconds", "x_param", "x_data", "x_speed", "model_type", "raw")

    def __init__(
        self,
        seconds: float,
        x_param: float,
        x_data: float,
        x_speed: float,
        model_type: str,
        raw: dict[str, str],
    ) -> None:
        self.seconds = seconds
        self.x_param = x_param
        self.x_data = x_data
        self.x_speed = x_speed
        self.model_type = model_type
        self.raw = raw

    def design_row(self) -> list[float]:
        return [
            1.0,
            self.x_param,
            self.x_data,
            self.x_speed,
            1.0 if self.model_type == "vision" else 0.0,
            1.0 if self.model_type == "cnn" else 0.0,
        ]

    def formula_log_seconds(self, ref_seconds: float) -> float:
        model_factor = MODEL_TYPE_FACTOR.get(self.model_type, 1.0)
        return (
            math.log(ref_seconds)
            + FORMULA_PARAM_EXP * self.x_param
            + FORMULA_DATASET_EXP * self.x_data
            + FORMULA_SPEED_EXP * self.x_speed
            + math.log(model_factor)
        )


def load_runs(
    csv_paths: list[Path],
    benchmarks: BenchmarkRegistry,
    baseline: dict[str, Any],
    gpu_registry: GPURegistry,
) -> list[Run]:
    ref_params = float(baseline.get("parameter_count_billion", 7.0))
    ref_samples = float(baseline.get("dataset_samples", 10_000))
    ref_gpu_id = baseline.get("reference_gpu_id", "a100-80gb")
    ref_throughput = benchmarks.relative_throughput(ref_gpu_id) or benchmarks.reference_throughput

    known_gpu_ids = {g.id for g in gpu_registry.gpus}
    report = load_duration_files(
        csv_paths,
        known_gpu_ids=known_gpu_ids,
        default_dataset_samples=ref_samples,
    )

    if report.skipped:
        print(f"[warn] skipped {len(report.skipped)} row(s):", file=sys.stderr)
        for msg in report.skipped:
            print(f"       - {msg}", file=sys.stderr)

    runs: list[Run] = []
    for row in report.runs:
        gpu_throughput = benchmarks.relative_throughput(row.gpu_id)
        if not gpu_throughput:
            print(f"[warn] no benchmark throughput for {row.gpu_id} ({row.source_file} row {row.source_row})", file=sys.stderr)
            continue

        speed_factor = ref_throughput / gpu_throughput
        runs.append(
            Run(
                seconds=row.seconds_per_epoch,
                x_param=math.log(row.parameter_count_billion / ref_params),
                x_data=math.log(row.dataset_samples / ref_samples),
                x_speed=math.log(speed_factor),
                model_type=row.model_type,
                raw=row.raw,
            )
        )

    return runs


def _expand_paths(patterns: list[str]) -> list[Path]:
    paths: list[Path] = []
    for pattern in patterns:
        matches = [Path(p) for p in glob.glob(pattern)]
        if matches:
            paths.extend(sorted(matches))
        elif Path(pattern).exists():
            paths.append(Path(pattern))
    return paths


def _inspect_columns(csv_path: Path) -> None:
    with csv_path.open(newline="", encoding="utf-8-sig") as fh:
        reader = csv.DictReader(fh)
        headers = list(reader.fieldnames or [])
    mapping = detect_column_map(headers)
    print(f"\n{csv_path.name} — {len(headers)} columns")
    print(f"{'internal field':<24}{'matched header':<24}")
    print("-" * 48)
    for field, header in mapping.items():
        print(f"{field:<24}{header:<24}")
    unmatched = [h for h in headers if h not in mapping.values()]
    if unmatched:
        print(f"\nUnmapped columns (kept for reference): {', '.join(unmatched)}")


# --------------------------------------------------------------------------- #
# Pure-Python ridge regression
# --------------------------------------------------------------------------- #
def _solve(matrix: list[list[float]], vector: list[float]) -> list[float]:
    """Solve A x = b via Gauss-Jordan elimination with partial pivoting."""
    n = len(matrix)
    aug = [row[:] + [vector[i]] for i, row in enumerate(matrix)]
    for col in range(n):
        pivot = max(range(col, n), key=lambda r: abs(aug[r][col]))
        if abs(aug[pivot][col]) < 1e-12:
            raise ValueError("singular matrix — not enough feature variation to fit")
        aug[col], aug[pivot] = aug[pivot], aug[col]
        pivot_val = aug[col][col]
        aug[col] = [v / pivot_val for v in aug[col]]
        for r in range(n):
            if r == col:
                continue
            factor = aug[r][col]
            if factor:
                aug[r] = [a - factor * b for a, b in zip(aug[r], aug[col])]
    return [aug[i][n] for i in range(n)]


def ridge_fit(rows: list[list[float]], targets: list[float], alpha: float) -> list[float]:
    """Ridge regression: beta = (XtX + alpha*I')^-1 Xt y. Intercept not penalized."""
    n_features = len(rows[0])
    xt_x = [[0.0] * n_features for _ in range(n_features)]
    xt_y = [0.0] * n_features
    for row, y in zip(rows, targets):
        for i in range(n_features):
            xt_y[i] += row[i] * y
            for j in range(n_features):
                xt_x[i][j] += row[i] * row[j]
    for i in range(1, n_features):  # skip intercept (index 0)
        xt_x[i][i] += alpha
    return _solve(xt_x, xt_y)


def predict_log(beta: list[float], row: list[float]) -> float:
    return sum(b * x for b, x in zip(beta, row))


# --------------------------------------------------------------------------- #
# Evaluation
# --------------------------------------------------------------------------- #
def _errors(actual: list[float], predicted: list[float]) -> dict[str, float]:
    ape = [abs(p - a) / a for a, p in zip(actual, predicted)]
    ape_sorted = sorted(ape)
    n = len(ape_sorted)
    median = ape_sorted[n // 2] if n % 2 else (ape_sorted[n // 2 - 1] + ape_sorted[n // 2]) / 2
    return {"mape": sum(ape) / n, "median_ape": median, "max_ape": max(ape)}


def cross_validate(runs: list[Run], ref_seconds: float, alpha: float, folds: int) -> dict[str, Any]:
    n = len(runs)
    folds = min(folds, n)  # leave-one-out when data is tiny
    formula_pred: list[float] = []
    calibrated_pred: list[float] = []
    actual: list[float] = []

    for fold in range(folds):
        test_idx = [i for i in range(n) if i % folds == fold]
        train_idx = [i for i in range(n) if i % folds != fold]
        if not test_idx or not train_idx:
            continue
        train_rows = [runs[i].design_row() for i in train_idx]
        train_y = [math.log(runs[i].seconds) for i in train_idx]
        try:
            beta = ridge_fit(train_rows, train_y, alpha)
        except ValueError:
            continue
        for i in test_idx:
            actual.append(runs[i].seconds)
            formula_pred.append(math.exp(runs[i].formula_log_seconds(ref_seconds)))
            calibrated_pred.append(math.exp(predict_log(beta, runs[i].design_row())))

    return {
        "formula": _errors(actual, formula_pred),
        "calibrated": _errors(actual, calibrated_pred),
        "n_evaluated": len(actual),
    }


def calibrated_constants(beta: list[float]) -> dict[str, Any]:
    idx = {name: i for i, name in enumerate(FEATURE_NAMES)}
    return {
        "reference_seconds_per_epoch": round(math.exp(beta[idx["intercept"]]), 2),
        "param_exponent": round(beta[idx["x_param"]], 4),
        "dataset_exponent": round(beta[idx["x_data"]], 4),
        "speed_exponent": round(beta[idx["x_speed"]], 4),
        "model_type_factor": {
            "transformer": 1.0,
            "vision": round(math.exp(beta[idx["d_vision"]]), 4),
            "cnn": round(math.exp(beta[idx["d_cnn"]]), 4),
        },
    }


def _pct(x: float) -> str:
    return f"{x * 100:.1f}%"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("csv_paths", nargs="+", help="CSV file(s) or glob pattern(s)")
    parser.add_argument("--alpha", type=float, default=0.1, help="ridge regularization strength")
    parser.add_argument("--folds", type=int, default=5, help="cross-validation folds")
    parser.add_argument("--knowledge-root", type=Path, default=None, help="override knowledge/ root")
    parser.add_argument("--write", action="store_true", help="write calibration YAML if the fit wins")
    parser.add_argument("--inspect", action="store_true", help="show column mapping and exit")
    args = parser.parse_args()

    paths = _expand_paths(args.csv_paths)
    if not paths:
        print(f"error: no files matched: {args.csv_paths}", file=sys.stderr)
        return 2

    if args.inspect:
        for path in paths:
            _inspect_columns(path)
        return 0

    pricing = PricingRegistry(knowledge_root=args.knowledge_root)
    benchmarks = BenchmarkRegistry(knowledge_root=args.knowledge_root)
    gpu_registry = GPURegistry(knowledge_root=args.knowledge_root)
    baseline = pricing.baseline
    ref_seconds = float(baseline.get("seconds_per_epoch", 3600))

    runs = load_runs(paths, benchmarks, baseline, gpu_registry)
    if len(runs) < 6:
        print(
            f"error: only {len(runs)} usable run(s). Need >= 6 for a meaningful fit; "
            "keep using the formula until you have more.",
            file=sys.stderr,
        )
        return 1

    result = cross_validate(runs, ref_seconds, args.alpha, args.folds)
    formula = result["formula"]
    calibrated = result["calibrated"]

    print(f"\nLoaded {len(runs)} usable runs; evaluated {result['n_evaluated']} under CV.\n")
    print(f"{'metric':<14}{'formula':>12}{'calibrated':>14}")
    print("-" * 40)
    for key, label in [("mape", "MAPE"), ("median_ape", "median APE"), ("max_ape", "max APE")]:
        print(f"{label:<14}{_pct(formula[key]):>12}{_pct(calibrated[key]):>14}")

    improvement = formula["mape"] - calibrated["mape"]
    wins = calibrated["mape"] < formula["mape"]
    promotable = wins and calibrated["mape"] <= MAX_PROMOTION_MAPE
    print()
    if wins:
        rel = improvement / formula["mape"] if formula["mape"] else 0.0
        print(f"==> Calibration WINS: MAPE {_pct(formula['mape'])} -> {_pct(calibrated['mape'])} "
              f"({_pct(rel)} relative reduction).")
        if not promotable:
            print(f"==> Not promotable: calibrated MAPE {_pct(calibrated['mape'])} exceeds "
                  f"{_pct(MAX_PROMOTION_MAPE)} quality ceiling.")
    else:
        print("==> Calibration does NOT beat the formula on held-out data. "
              "Keep the formula (safe fallback). More/cleaner data may change this.")

    # Fit final constants on ALL data for reporting/promotion.
    all_rows = [r.design_row() for r in runs]
    all_y = [math.log(r.seconds) for r in runs]
    beta = ridge_fit(all_rows, all_y, args.alpha)
    constants = calibrated_constants(beta)

    print("\nCalibrated constants (fit on all data):")
    for key, val in constants.items():
        print(f"  {key}: {val}")

    if args.write:
        if not promotable:
            reason = "did not beat the formula" if not wins else f"MAPE exceeds {_pct(MAX_PROMOTION_MAPE)} ceiling"
            print(f"\n[skip] --write ignored: calibration {reason}.", file=sys.stderr)
            return 0
        out_path = _write_yaml(constants, result, len(runs), pricing.knowledge_root)
        print(f"\nWrote calibration to {out_path}")
        print("The cost calculator will now use these constants automatically.")

    return 0


def _write_yaml(constants: dict[str, Any], result: dict[str, Any], n_runs: int, knowledge_root: Path) -> Path:
    import yaml

    out_path = Path(knowledge_root) / "hardware" / "duration_calibration.yaml"
    payload = {
        "metadata": {
            "note": "Data-calibrated duration-formula constants. Delete this file to revert to defaults.",
            "n_runs": n_runs,
            "cv_mape_formula": round(result["formula"]["mape"], 4),
            "cv_mape_calibrated": round(result["calibrated"]["mape"], 4),
        },
        **constants,
    }
    out_path.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")
    return out_path


if __name__ == "__main__":
    raise SystemExit(main())
