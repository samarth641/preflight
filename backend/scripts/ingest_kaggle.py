"""Ingest Kaggle / HuggingFace experiment datasets for duration calibration.

Supports:
  1. Manual CSV drop-in (any path)
  2. Kaggle API download (if ~/.kaggle/kaggle.json exists)
  3. HuggingFace autoresearch-experiments fallback (public, no API key)

Usage:
    python backend/scripts/ingest_kaggle.py --path data/benchmarks/my.csv
    python backend/scripts/ingest_kaggle.py --kaggle yuvrajgarg004/global-ml-experiments-and-benchmark-tracker
    python backend/scripts/ingest_kaggle.py --huggingface autoresearch
    python backend/scripts/ingest_kaggle.py --kaggle ... --calibrate
"""

from __future__ import annotations

import argparse
import csv
import shutil
import subprocess
import sys
import urllib.request
import zipfile
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = BACKEND_ROOT.parent
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

DEFAULT_KAGGLE = "yuvrajgarg004/global-ml-experiments-and-benchmark-tracker"
HF_AUTORESEARCH_URL = (
    "https://huggingface.co/datasets/davegraham/autoresearch-experiments/"
    "resolve/main/data/experiments.parquet"
)
OUT_DIR = REPO_ROOT / "data" / "benchmarks"


def _has_kaggle_creds() -> bool:
    return (Path.home() / ".kaggle" / "kaggle.json").exists()


def _ensure_kaggle_cli() -> bool:
    if shutil.which("kaggle"):
        return True
    print("Installing kaggle CLI...", file=sys.stderr)
    return subprocess.call([sys.executable, "-m", "pip", "install", "kaggle", "-q"]) == 0


def download_kaggle_dataset(slug: str, out_dir: Path) -> list[Path]:
    if not _has_kaggle_creds():
        raise RuntimeError(
            "Kaggle credentials not found. Place kaggle.json in ~/.kaggle/ "
            "(see https://www.kaggle.com/docs/api#authentication)"
        )
    if not _ensure_kaggle_cli():
        raise RuntimeError("Failed to install kaggle CLI")

    out_dir.mkdir(parents=True, exist_ok=True)
    cmd = ["kaggle", "datasets", "download", "-d", slug, "-p", str(out_dir), "--unzip"]
    print(f"Running: {' '.join(cmd)}", file=sys.stderr)
    if subprocess.call(cmd) != 0:
        raise RuntimeError(f"kaggle download failed for {slug}")

    return sorted(out_dir.glob("**/*.csv"))


def download_huggingface_autoresearch(out_path: Path) -> Path:
    """Convert HF autoresearch parquet to a calibration-friendly CSV."""
    try:
        import pyarrow.parquet as pq  # type: ignore
    except ImportError:
        print("Installing pyarrow...", file=sys.stderr)
        if subprocess.call([sys.executable, "-m", "pip", "install", "pyarrow", "-q"]) != 0:
            raise RuntimeError("pyarrow required for HuggingFace parquet download")
        import pyarrow.parquet as pq  # type: ignore

    tmp = out_path.with_suffix(".parquet")
    print(f"Downloading {HF_AUTORESEARCH_URL}...", file=sys.stderr)
    urllib.request.urlretrieve(HF_AUTORESEARCH_URL, tmp)

    table = pq.read_table(tmp)
    rows = table.to_pylist()
    tmp.unlink(missing_ok=True)

    # 5-minute fixed training budget per experiment; treat as one epoch window.
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fields = [
        "training_time",
        "gpu_name",
        "model_size",
        "dataset_size",
        "task_type",
        "source",
    ]
    with out_path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            if row.get("status") == "crash":
                continue
            tok_sec = row.get("tok_sec") or 0
            steps = row.get("steps") or 0
            if not tok_sec or not steps:
                continue
            writer.writerow(
                {
                    "training_time": "300",
                    "gpu_name": row.get("gpu_name", ""),
                    "model_size": "1.3B",
                    "dataset_size": row.get("dataset", "10000"),
                    "task_type": "transformer",
                    "source": "hf:autoresearch-experiments",
                }
            )

    return out_path


def pick_largest_csv(paths: list[Path]) -> Path:
    if not paths:
        raise RuntimeError("no CSV files found after download")
    return max(paths, key=lambda p: p.stat().st_size)


def run_calibration(csv_paths: list[Path], write: bool) -> int:
    cmd = [sys.executable, str(BACKEND_ROOT / "scripts" / "calibrate_duration.py"), *[str(p) for p in csv_paths]]
    if write:
        cmd.append("--write")
    return subprocess.call(cmd)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--path", type=Path, help="existing CSV to use")
    parser.add_argument("--kaggle", nargs="?", const=DEFAULT_KAGGLE, help="download Kaggle dataset slug")
    parser.add_argument("--huggingface", choices=["autoresearch"], help="download public HF fallback dataset")
    parser.add_argument("--calibrate", action="store_true", help="run calibrate_duration.py after ingest")
    parser.add_argument("--write", action="store_true", help="promote calibration if quality gate passes")
    args = parser.parse_args()

    csv_paths: list[Path] = []

    if args.path:
        if not args.path.exists():
            print(f"error: {args.path} not found", file=sys.stderr)
            return 2
        csv_paths = [args.path]
    elif args.kaggle:
        try:
            downloaded = download_kaggle_dataset(args.kaggle, OUT_DIR / "kaggle" / args.kaggle.split("/")[-1])
            csv_paths = [pick_largest_csv(downloaded)]
            print(f"Using {csv_paths[0]}")
        except RuntimeError as exc:
            print(f"error: {exc}", file=sys.stderr)
            print("\nManual fallback:", file=sys.stderr)
            print(f"  1. Download from https://www.kaggle.com/datasets/{args.kaggle}", file=sys.stderr)
            print(f"  2. Place CSV in {OUT_DIR}/", file=sys.stderr)
            print(f"  3. python backend/scripts/ingest_kaggle.py --path {OUT_DIR}/your.csv --calibrate", file=sys.stderr)
            return 1
    elif args.huggingface == "autoresearch":
        out = OUT_DIR / "autoresearch_experiments.csv"
        download_huggingface_autoresearch(out)
        csv_paths = [out]
        print(f"Wrote {out}")
    else:
        parser.print_help()
        print("\nNo source selected. Examples:", file=sys.stderr)
        print("  python backend/scripts/ingest_kaggle.py --huggingface autoresearch --calibrate", file=sys.stderr)
        print(f"  python backend/scripts/ingest_kaggle.py --kaggle {DEFAULT_KAGGLE} --calibrate", file=sys.stderr)
        return 2

    if args.calibrate:
        return run_calibration(csv_paths, args.write)

    print("\nNext:")
    print(f"  python backend/scripts/calibrate_duration.py {' '.join(str(p) for p in csv_paths)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
