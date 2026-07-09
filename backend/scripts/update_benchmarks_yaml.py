"""Update benchmarks.yaml GPU throughput from ingested MLPerf training data.

Uses same-benchmark, single-node (1x) submissions only. Throughput ratio
relative to A100 is derived as:

    ratio_gpu = ratio_h100 * (median_time_h100 / median_time_gpu)

when direct A100 pairs are unavailable, using the existing H100/A100 anchor.

Usage:
    python backend/scripts/update_benchmarks_yaml.py
    python backend/scripts/update_benchmarks_yaml.py --csv data/benchmarks/mlperf_training_runs.csv
"""

from __future__ import annotations

import argparse
import csv
import re
import statistics
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

BACKEND_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = BACKEND_ROOT.parent
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

import yaml  # noqa: E402

H100_A100_ANCHOR = 2.3  # existing published anchor when no direct A100 pair exists
REFERENCE_GPU = "a100-80gb"


def _fair_rows(csv_path: Path) -> list[dict[str, str]]:
    rows = list(csv.DictReader(csv_path.open(encoding="utf-8")))
    return [
        r
        for r in rows
        if int(r["gpu_count"]) == 1
        and re.match(r"^1x", (r.get("submission_platform") or "").strip(), re.I)
    ]


def compute_throughput_ratios(rows: list[dict[str, str]]) -> dict[str, float]:
    by_bench_gpu: dict[tuple[str, str], list[float]] = defaultdict(list)
    for row in rows:
        by_bench_gpu[(row["benchmark"], row["accelerator"])].append(float(row["training_time"]))

    medians = {key: statistics.median(vals) for key, vals in by_bench_gpu.items()}

    # Direct A100 head-to-head per benchmark
    vs_a100: dict[str, list[float]] = defaultdict(list)
    for (bench, gpu), gpu_time in medians.items():
        a100_time = medians.get((bench, REFERENCE_GPU))
        if a100_time and gpu != REFERENCE_GPU:
            vs_a100[gpu].append(a100_time / gpu_time)

    ratios: dict[str, float] = {REFERENCE_GPU: 1.0}
    for gpu, samples in vs_a100.items():
        ratios[gpu] = statistics.median(samples)

    # Anchor H100/MI300X through H100/A100 when no direct A100 data
    h100_time = medians.get(("llama2_70b_lora", "h100-80gb"))
    if h100_time:
        ratios.setdefault("h100-80gb", H100_A100_ANCHOR)
        for gpu in ("h100-80gb", "mi300x"):
            gpu_time = medians.get(("llama2_70b_lora", gpu))
            if gpu_time and gpu not in ratios:
                ratios[gpu] = H100_A100_ANCHOR * (h100_time / gpu_time)

    return ratios


def apply_to_yaml(ratios: dict[str, float], benchmarks_path: Path, n_fair_rows: int) -> None:
    data = yaml.safe_load(benchmarks_path.read_text(encoding="utf-8")) or {}
    gpus: dict[str, Any] = data.setdefault("gpus", {})
    metadata = data.setdefault("metadata", {})
    metadata["updated"] = "2026-07"
    metadata["note"] = (
        "Throughput ratios blend published anchors with MLPerf Training ingest "
        f"({n_fair_rows} fair single-node runs)."
    )

    for gpu_id, ratio in ratios.items():
        if gpu_id == REFERENCE_GPU:
            continue
        entry = gpus.setdefault(gpu_id, {})
        entry["relative_training_throughput"] = round(ratio, 2)
        entry["approximate"] = gpu_id not in gpus or gpus[gpu_id].get("approximate", True)
        if gpu_id == "h100-80gb":
            entry["source"] = (
                f"MLPerf Training ingest (llama2_70b_lora 1-node median); "
                f"anchored at {H100_A100_ANCHOR}x A100."
            )
        elif gpu_id == "mi300x":
            entry["source"] = (
                "MLPerf v5.0 llama2_70b_lora 1-node median — parity with H100 "
                f"({round(ratio, 2)}x A100 via ingest)."
            )
        else:
            entry["source"] = f"MLPerf Training ingest median vs A100 ({round(ratio, 2)}x)."

    benchmarks_path.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument(
        "--csv",
        type=Path,
        default=REPO_ROOT / "data" / "benchmarks" / "mlperf_training_runs.csv",
    )
    parser.add_argument(
        "--yaml",
        type=Path,
        default=REPO_ROOT / "knowledge" / "hardware" / "benchmarks.yaml",
    )
    args = parser.parse_args()

    if not args.csv.exists():
        print(f"error: missing {args.csv} — run ingest_benchmarks.py first", file=sys.stderr)
        return 1

    fair = _fair_rows(args.csv)
    ratios = compute_throughput_ratios(fair)
    print("Computed relative throughput (A100 = 1.0):")
    for gpu, ratio in sorted(ratios.items()):
        print(f"  {gpu}: {ratio:.2f}")

    apply_to_yaml(ratios, args.yaml, len(fair))
    print(f"\nUpdated {args.yaml}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
