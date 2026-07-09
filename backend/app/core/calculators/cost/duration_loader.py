"""Load training-duration runs from heterogeneous CSV schemas.

Public benchmark datasets use many column names for the same concepts. This
module maps them into Preflight's internal feature space (seconds/epoch, params,
GPU, dataset size, model type) so calibration can ingest MLPerf, Kaggle, FlexBench,
and custom exports without manual reformatting.
"""

from __future__ import annotations

import csv
import math
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable

# --------------------------------------------------------------------------- #
# Field aliases — add new source columns here as you discover them
# --------------------------------------------------------------------------- #
DURATION_ALIASES = (
    "seconds_per_epoch",
    "epoch_time_seconds",
    "epoch_duration_sec",
    "time_per_epoch",
    "time_per_epoch_sec",
    "training_time_per_epoch",
    "avg_epoch_time",
    "epoch_time",
)

TOTAL_TIME_ALIASES = (
    "total_seconds",
    "training_time_seconds",
    "training_duration_seconds",
    "wall_clock_seconds",
    "runtime_seconds",
    "job_duration_seconds",
    "duration_seconds",
    "training_time",
    "train_time",
    "runtime",
    "duration",
    "wall_time",
    "elapsed_time",
)

TOTAL_TIME_MINUTES_ALIASES = (
    "training_time_minutes",
    "duration_minutes",
    "runtime_minutes",
    "wall_clock_minutes",
    "train_time_min",
)

TOTAL_TIME_HOURS_ALIASES = (
    "training_time_hours",
    "duration_hours",
    "runtime_hours",
    "wall_clock_hours",
    "train_time_hours",
    "gpu_hours",
)

EPOCHS_ALIASES = ("epochs", "num_epochs", "n_epochs", "epoch_count", "total_epochs")

PARAMS_B_ALIASES = (
    "parameter_count_billion",
    "params_billion",
    "params_b",
    "num_params_billion",
    "model_size_b",
    "parameters_b",
)

PARAMS_RAW_ALIASES = (
    "parameter_count",
    "num_parameters",
    "params",
    "parameters",
    "model_parameters",
    "total_params",
)

PARAMS_M_ALIASES = ("parameter_count_million", "params_million", "params_m", "num_params_million")

MODEL_SIZE_TEXT_ALIASES = ("model_size", "model", "architecture", "model_name", "benchmark_model")

GPU_ALIASES = (
    "gpu_id",
    "gpu",
    "gpu_type",
    "gpu_name",
    "accelerator",
    "hardware",
    "device",
    "gpu_model",
    "accelerator_type",
)

DATASET_ALIASES = (
    "dataset_samples",
    "num_samples",
    "samples",
    "training_samples",
    "dataset_size",
    "num_training_samples",
    "train_samples",
    "data_size",
)

MODEL_TYPE_ALIASES = ("model_type", "task_type", "modality", "domain", "workload_type")

# Substrings in GPU text -> internal gpu_id (longer / more specific first)
GPU_TEXT_TO_ID: list[tuple[str, str]] = [
    ("h100 80gb", "h100-80gb"),
    ("h100-80gb", "h100-80gb"),
    ("h100", "h100-80gb"),
    ("a100 80gb", "a100-80gb"),
    ("a100-80gb", "a100-80gb"),
    ("a100", "a100-80gb"),
    ("mi300x", "mi300x"),
    ("mi300", "mi300x"),
    ("rtx 5090", "rtx-5090"),
    ("rtx-5090", "rtx-5090"),
    ("5090", "rtx-5090"),
    ("rtx 4090", "rtx-4090"),
    ("rtx-4090", "rtx-4090"),
    ("4090", "rtx-4090"),
    ("rtx 4080", "rtx-4080"),
    ("rtx-4080", "rtx-4080"),
    ("4080", "rtx-4080"),
    ("rtx 4070", "rtx-4070"),
    ("rtx-4070", "rtx-4070"),
    ("4070", "rtx-4070"),
    ("rtx 4060 ti", "rtx-4060-ti"),
    ("rtx-4060-ti", "rtx-4060-ti"),
    ("4060 ti", "rtx-4060-ti"),
    ("rtx 4060", "rtx-4060"),
    ("rtx-4060", "rtx-4060"),
    ("4060", "rtx-4060"),
    ("rtx 3060", "rtx-3060"),
    ("rtx-3060", "rtx-3060"),
    ("3060", "rtx-3060"),
    ("7900 xtx", "rx-7900-xtx"),
    ("rx-7900-xtx", "rx-7900-xtx"),
    ("7900xtx", "rx-7900-xtx"),
]

# Model name / task hints -> model_type
VISION_HINTS = ("resnet", "vit", "vision", "image", "imagenet", "yolo", "efficientnet", "clip")
CNN_HINTS = ("cnn", "conv", "mobilenet", "vgg")
TRANSFORMER_HINTS = (
    "transformer",
    "llm",
    "gpt",
    "bert",
    "llama",
    "mistral",
    "bloom",
    "t5",
    "language",
    "nlp",
    "bert",
)


@dataclass
class NormalizedRun:
    """One row reduced to Preflight's calibration feature space."""

    seconds_per_epoch: float
    parameter_count_billion: float
    gpu_id: str
    dataset_samples: float
    model_type: str
    source_row: int
    source_file: str
    raw: dict[str, str] = field(default_factory=dict)


@dataclass
class LoadReport:
    runs: list[NormalizedRun]
    skipped: list[str]
    files_read: list[str]
    column_map: dict[str, str]  # internal field -> matched header


def _norm_key(key: str) -> str:
    return re.sub(r"[\s\-\.]+", "_", key.strip().lower())


def _build_header_index(headers: list[str]) -> dict[str, str]:
    return {_norm_key(h): h for h in headers if h}


def _pick(row: dict[str, str], index: dict[str, str], aliases: tuple[str, ...]) -> str | None:
    for alias in aliases:
        original = index.get(_norm_key(alias))
        if original is not None:
            val = row.get(original)
            if val not in (None, ""):
                return val.strip()
    return None


def _parse_float(text: str | None) -> float | None:
    if text is None or text == "":
        return None
    cleaned = text.strip().replace(",", "")
    try:
        return float(cleaned)
    except ValueError:
        return None


def _parse_param_size(text: str | None) -> float | None:
    """Parse 7, 7B, 7billion, 7000000000, 1300M, etc. -> billions."""
    if text is None or text == "":
        return None
    raw = text.strip().replace(",", "").lower()
    direct = _parse_float(raw)
    if direct is not None and direct > 1_000_000:
        return direct / 1_000_000_000
    if direct is not None and direct > 0 and direct < 1000:
        return direct

    m = re.match(r"^([\d.]+)\s*([bkm])?(?:illion|params?)?$", raw)
    if m:
        val = float(m.group(1))
        unit = m.group(2) or ""
        if unit == "b":
            return val
        if unit == "m":
            return val / 1000
        if unit == "k":
            return val / 1_000_000
        if val > 1_000_000:
            return val / 1_000_000_000
        return val
    return None


def _resolve_gpu_id(gpu_text: str | None, known_ids: set[str]) -> str | None:
    if not gpu_text:
        return None
    cleaned = gpu_text.strip().lower()
    if cleaned in known_ids:
        return cleaned
    normalized = cleaned.replace("nvidia ", "").replace("amd ", "")
    if normalized in known_ids:
        return normalized
    for needle, gpu_id in GPU_TEXT_TO_ID:
        if needle in normalized:
            return gpu_id
    return None


def _infer_model_type(model_type_text: str | None, model_name_text: str | None) -> str:
    if model_type_text:
        mt = model_type_text.strip().lower()
        if mt in ("transformer", "vision", "cnn", "llm", "nlp", "language"):
            if mt in ("llm", "nlp", "language"):
                return "transformer"
            return mt
        if "vision" in mt or "image" in mt:
            return "vision"
        if "cnn" in mt or "conv" in mt:
            return "cnn"

    blob = (model_name_text or "").lower()
    if any(h in blob for h in VISION_HINTS):
        return "vision"
    if any(h in blob for h in CNN_HINTS):
        return "cnn"
    if any(h in blob for h in TRANSFORMER_HINTS):
        return "transformer"
    return "transformer"


def _resolve_seconds(row: dict[str, str], index: dict[str, str]) -> float | None:
    direct = _parse_float(_pick(row, index, DURATION_ALIASES))
    if direct and direct > 0:
        return direct

    epochs = _parse_float(_pick(row, index, EPOCHS_ALIASES))
    total = _parse_float(_pick(row, index, TOTAL_TIME_ALIASES))
    if total and total > 0:
        if epochs and epochs > 0:
            return total / epochs
        return total  # single-epoch / time-to-train benchmarks

    total_min = _parse_float(_pick(row, index, TOTAL_TIME_MINUTES_ALIASES))
    if total_min and total_min > 0:
        total_sec = total_min * 60
        return total_sec / epochs if epochs and epochs > 0 else total_sec

    total_hr = _parse_float(_pick(row, index, TOTAL_TIME_HOURS_ALIASES))
    if total_hr and total_hr > 0:
        total_sec = total_hr * 3600
        return total_sec / epochs if epochs and epochs > 0 else total_sec

    return None


def _resolve_params_b(row: dict[str, str], index: dict[str, str]) -> float | None:
    val = _parse_float(_pick(row, index, PARAMS_B_ALIASES))
    if val and val > 0:
        return val

    raw_text = _pick(row, index, PARAMS_RAW_ALIASES)
    if raw_text:
        parsed = _parse_param_size(raw_text)
        if parsed and parsed > 0:
            return parsed
        raw_num = _parse_float(raw_text)
        if raw_num and raw_num > 0:
            return raw_num / 1_000_000_000 if raw_num > 1_000_000 else raw_num

    millions = _parse_float(_pick(row, index, PARAMS_M_ALIASES))
    if millions and millions > 0:
        return millions / 1000

    return _parse_param_size(_pick(row, index, MODEL_SIZE_TEXT_ALIASES))


def _resolve_samples(row: dict[str, str], index: dict[str, str], default: float) -> float:
    val = _parse_float(_pick(row, index, DATASET_ALIASES))
    if val and val > 0:
        return val
    return default


def detect_column_map(headers: list[str]) -> dict[str, str]:
    """Show which headers map to each internal field (for debugging)."""
    index = _build_header_index(headers)
    mapping: dict[str, str] = {}
    checks = [
        ("seconds_per_epoch", DURATION_ALIASES),
        ("total_time", TOTAL_TIME_ALIASES + TOTAL_TIME_MINUTES_ALIASES + TOTAL_TIME_HOURS_ALIASES),
        ("epochs", EPOCHS_ALIASES),
        ("parameter_count_billion", PARAMS_B_ALIASES + PARAMS_RAW_ALIASES + PARAMS_M_ALIASES),
        ("model_size_text", MODEL_SIZE_TEXT_ALIASES),
        ("gpu_id", GPU_ALIASES),
        ("dataset_samples", DATASET_ALIASES),
        ("model_type", MODEL_TYPE_ALIASES),
    ]
    for field_name, aliases in checks:
        for alias in aliases:
            original = index.get(_norm_key(alias))
            if original:
                mapping[field_name] = original
                break
    return mapping


def load_duration_csv(
    csv_path: Path | str,
    *,
    known_gpu_ids: set[str] | None = None,
    default_dataset_samples: float = 10_000,
    default_epochs: float | None = None,
) -> LoadReport:
    """Load one CSV with flexible schema detection."""
    path = Path(csv_path)
    known_gpu_ids = known_gpu_ids or set()
    runs: list[NormalizedRun] = []
    skipped: list[str] = []
    column_map: dict[str, str] = {}

    with path.open(newline="", encoding="utf-8-sig") as fh:
        reader = csv.DictReader(fh)
        if not reader.fieldnames:
            return LoadReport([], [f"{path}: empty or no header"], [str(path)], {})

        index = _build_header_index(list(reader.fieldnames))
        column_map = detect_column_map(list(reader.fieldnames))

        for i, row in enumerate(reader, start=2):
            seconds = _resolve_seconds(row, index)
            if not seconds or seconds <= 0:
                skipped.append(f"{path.name} row {i}: no duration (need seconds_per_epoch or total_time)")
                continue

            params_b = _resolve_params_b(row, index)
            if not params_b or params_b <= 0:
                skipped.append(f"{path.name} row {i}: no parameter count")
                continue

            gpu_text = _pick(row, index, GPU_ALIASES)
            gpu_id = _resolve_gpu_id(gpu_text, known_gpu_ids)
            if not gpu_id:
                skipped.append(f"{path.name} row {i}: unrecognized GPU '{gpu_text}'")
                continue

            samples = _resolve_samples(row, index, default_dataset_samples)
            model_type = _infer_model_type(
                _pick(row, index, MODEL_TYPE_ALIASES),
                _pick(row, index, MODEL_SIZE_TEXT_ALIASES),
            )

            runs.append(
                NormalizedRun(
                    seconds_per_epoch=seconds,
                    parameter_count_billion=params_b,
                    gpu_id=gpu_id,
                    dataset_samples=samples,
                    model_type=model_type,
                    source_row=i,
                    source_file=path.name,
                    raw={k: v for k, v in row.items() if v},
                )
            )

    return LoadReport(runs, skipped, [str(path)], column_map)


def load_duration_files(
    paths: Iterable[Path | str],
    *,
    known_gpu_ids: set[str] | None = None,
    default_dataset_samples: float = 10_000,
) -> LoadReport:
    """Load and merge multiple CSV files."""
    all_runs: list[NormalizedRun] = []
    all_skipped: list[str] = []
    files_read: list[str] = []
    column_map: dict[str, str] = {}

    for path in paths:
        report = load_duration_csv(
            path,
            known_gpu_ids=known_gpu_ids,
            default_dataset_samples=default_dataset_samples,
        )
        all_runs.extend(report.runs)
        all_skipped.extend(report.skipped)
        files_read.extend(report.files_read)
        column_map.update(report.column_map)

    return LoadReport(all_runs, all_skipped, files_read, column_map)
