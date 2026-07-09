"""Download and normalize public GPU benchmark data for Preflight calibration.

Currently ingests MLPerf Training submission logs (v4.0, v4.1, v5.0) from GitHub,
parses MLLog result files, and writes a unified CSV that ``calibrate_duration.py``
can consume via the flexible ``duration_loader``.

Usage:
    python backend/scripts/ingest_benchmarks.py
    python backend/scripts/ingest_benchmarks.py --calibrate          # ingest + run calibration
    python backend/scripts/ingest_benchmarks.py --calibrate --write # promote if CV wins
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import subprocess
import sys
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

MLPERF_REPOS = (
    "training_results_v5.0",
    "training_results_v4.1",
    "training_results_v4.0",
)

MULTI_GPU_SCALING_EXP = 0.95
MAX_TRAIN_SAMPLES = 50_000_000
MIN_TRAIN_SAMPLES = 100
MAX_TRAINING_SECONDS = 7 * 24 * 3600
MIN_TRAINING_SECONDS = 1.0

# MLPerf benchmark -> approximate model metadata
BENCHMARK_META: dict[str, dict[str, Any]] = {
    "bert": {"parameter_count_billion": 0.11, "model_type": "transformer"},
    "resnet": {"parameter_count_billion": 0.025, "model_type": "vision"},
    "resnet50": {"parameter_count_billion": 0.025, "model_type": "vision"},
    "ssd": {"parameter_count_billion": 0.034, "model_type": "vision"},
    "retinanet": {"parameter_count_billion": 0.037, "model_type": "vision"},
    "llama2_70b_lora": {"parameter_count_billion": 70.0, "model_type": "transformer"},
    "llama2_70b": {"parameter_count_billion": 70.0, "model_type": "transformer"},
    "stable_diffusion": {"parameter_count_billion": 0.9, "model_type": "vision"},
    "dlrm_dcnv2": {"parameter_count_billion": 0.05, "model_type": "cnn"},
    "dlrm": {"parameter_count_billion": 0.05, "model_type": "cnn"},
    "gnn": {"parameter_count_billion": 0.025, "model_type": "cnn"},
    "rgat": {"parameter_count_billion": 0.025, "model_type": "cnn"},
    "gpt3": {"parameter_count_billion": 175.0, "model_type": "transformer"},
    "llama31_405b": {"parameter_count_billion": 405.0, "model_type": "transformer"},
}

GPU_ID_BY_TOKEN: list[tuple[str, str]] = [
    ("h100", "h100-80gb"),
    ("a100", "a100-80gb"),
    ("mi325x", "mi300x"),
    ("mi300x", "mi300x"),
    ("4090", "rtx-4090"),
    ("4080", "rtx-4080"),
    ("7900", "rx-7900-xtx"),
]


def _extract_gpu_count(blob: str, gpu_token: str) -> int:
    patterns = [
        rf"(\d+)\s*x\s*(?:nvidia\s+)?(?:dgx\s+)?{gpu_token}",
        rf"(\d+)\s*x\s*{gpu_token}",
        rf"(\d+)\s*{gpu_token}",
        rf"{gpu_token}.*?x(\d+)",
        rf"x(\d+)\s*(?:nvidia\s+)?(?:dgx\s+)?{gpu_token}",
    ]
    for pat in patterns:
        m = re.search(pat, blob, re.I)
        if m:
            return max(1, int(m.group(1)))
    return 1


def _fetch_json(url: str) -> Any:
    req = urllib.request.Request(url, headers={"User-Agent": "preflight-ingest/1.0"})
    with urllib.request.urlopen(req, timeout=60) as resp:
        return json.loads(resp.read().decode())


def _fetch_text(url: str) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": "preflight-ingest/1.0"})
    with urllib.request.urlopen(req, timeout=60) as resp:
        return resp.read().decode("utf-8", errors="replace")


def list_mlperf_result_files(repo: str) -> list[str]:
    data = _fetch_json(f"https://api.github.com/repos/mlcommons/{repo}/git/trees/main?recursive=1")
    return sorted(
        t["path"]
        for t in data.get("tree", [])
        if re.search(r"/results/.+/result_0\.txt$", t["path"])
    )


def _parse_gpu_count(platform: str, system_path: str) -> tuple[str | None, int]:
    blob = f"{platform} {system_path}".replace("_", " ")
    for token, gpu_id in GPU_ID_BY_TOKEN:
        if re.search(token, blob, re.I):
            return gpu_id, _extract_gpu_count(blob, token)
    return None, 1


def _parse_mllog(text: str) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for line in text.splitlines():
        if not line.startswith(":::MLLOG"):
            continue
        try:
            event = json.loads(line[9:])
        except json.JSONDecodeError:
            continue
        key = event.get("key")
        if key in {
            "submission_benchmark",
            "submission_platform",
            "train_samples",
            "global_batch_size",
            "run_start",
            "run_stop",
        }:
            out[key] = event.get("value")
            if key in {"run_start", "run_stop"}:
                out[f"{key}_ms"] = event.get("time_ms")
    return out


def parse_mlperf_result(repo: str, path: str, text: str) -> dict[str, str] | None:
    log = _parse_mllog(text)
    start_ms = log.get("run_start_ms")
    stop_ms = log.get("run_stop_ms")
    if not start_ms or not stop_ms or stop_ms <= start_ms:
        return None

    benchmark = str(log.get("submission_benchmark") or "")
    benchmark_key = benchmark.lower().replace("-", "_")
    meta = BENCHMARK_META.get(benchmark_key)
    if not meta:
        return None

    platform = str(log.get("submission_platform") or "")
    system_path = path.split("/results/", 1)[-1].rsplit("/", 1)[0] if "/results/" in path else path
    gpu_id, gpu_count = _parse_gpu_count(platform, system_path)
    if not gpu_id:
        return None

    wall_seconds = (float(stop_ms) - float(start_ms)) / 1000.0
    if wall_seconds < MIN_TRAINING_SECONDS or wall_seconds > MAX_TRAINING_SECONDS:
        return None

    single_gpu_seconds = wall_seconds * (gpu_count ** MULTI_GPU_SCALING_EXP)
    samples = log.get("train_samples")
    if samples is None:
        dataset_samples = 10_000
    else:
        dataset_samples = int(float(samples))
        if dataset_samples < MIN_TRAIN_SAMPLES or dataset_samples > MAX_TRAIN_SAMPLES:
            return None

    return {
        "source": f"mlperf:{repo}",
        "benchmark": benchmark,
        "training_time": f"{single_gpu_seconds:.3f}",
        "accelerator": gpu_id,
        "num_parameters": str(meta["parameter_count_billion"]),
        "train_samples": str(dataset_samples),
        "workload_type": meta["model_type"],
        "gpu_count": str(gpu_count),
        "submission_platform": platform,
        "system_path": system_path,
    }


def download_and_parse(repo: str, path: str) -> dict[str, str] | None:
    url = f"https://raw.githubusercontent.com/mlcommons/{repo}/main/{path}"
    try:
        text = _fetch_text(url)
    except (urllib.error.URLError, TimeoutError):
        return None
    return parse_mlperf_result(repo, path, text)


def ingest_mlperf(max_workers: int = 16) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    tasks: list[tuple[str, str]] = []
    for repo in MLPERF_REPOS:
        print(f"Listing {repo}...", file=sys.stderr)
        for path in list_mlperf_result_files(repo):
            tasks.append((repo, path))

    print(f"Downloading {len(tasks)} MLPerf result logs...", file=sys.stderr)
    with ThreadPoolExecutor(max_workers=max_workers) as pool:
        futures = {pool.submit(download_and_parse, repo, path): (repo, path) for repo, path in tasks}
        done = 0
        for fut in as_completed(futures):
            done += 1
            try:
                row = fut.result()
            except Exception as exc:  # noqa: BLE001 — keep ingest resilient per-file
                print(f"  [warn] failed: {futures[fut]} ({exc})", file=sys.stderr)
                continue
            if row:
                rows.append(row)
            if done % 25 == 0 or done == len(tasks):
                print(f"  parsed {done}/{len(tasks)} ({len(rows)} usable)", file=sys.stderr)
    return rows


def write_csv(rows: list[dict[str, str]], out_path: Path) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fields = [
        "source",
        "benchmark",
        "training_time",
        "accelerator",
        "num_parameters",
        "train_samples",
        "workload_type",
        "gpu_count",
        "submission_platform",
        "system_path",
    ]
    with out_path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument(
        "--out",
        type=Path,
        default=Path("data/benchmarks/mlperf_training_runs.csv"),
        help="output CSV path",
    )
    parser.add_argument("--calibrate", action="store_true", help="run calibrate_duration.py after ingest")
    parser.add_argument("--write", action="store_true", help="pass --write to calibration if it wins")
    parser.add_argument("--workers", type=int, default=16, help="parallel download workers")
    parser.add_argument(
        "--update-benchmarks",
        action="store_true",
        help="also update knowledge/hardware/benchmarks.yaml from ingested MLPerf data",
    )
    args = parser.parse_args()

    rows = ingest_mlperf(max_workers=args.workers)
    if not rows:
        print("error: no usable rows ingested", file=sys.stderr)
        return 1

    write_csv(rows, args.out)
    print(f"\nWrote {len(rows)} rows to {args.out}")

    # Quick breakdown
    by_gpu: dict[str, int] = {}
    for r in rows:
        by_gpu[r["accelerator"]] = by_gpu.get(r["accelerator"], 0) + 1
    print("Rows by GPU:", ", ".join(f"{k}={v}" for k, v in sorted(by_gpu.items())))

    if args.update_benchmarks:
        cmd = [sys.executable, str(BACKEND_ROOT / "scripts" / "update_benchmarks_yaml.py"), "--csv", str(args.out)]
        print("\nUpdating benchmarks.yaml...")
        subprocess.call(cmd)

    if args.calibrate:
        cmd = [sys.executable, str(BACKEND_ROOT / "scripts" / "calibrate_duration.py"), str(args.out)]
        if args.write:
            cmd.append("--write")
        print("\nRunning calibration...\n")
        return subprocess.call(cmd)

    print("\nNext: python backend/scripts/calibrate_duration.py", args.out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
