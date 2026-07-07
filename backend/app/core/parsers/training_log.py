"""Training log parser — reads CSV / JSON logs into EpochMetrics rows."""

from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any

from app.core.analyzers.training.models import EpochMetrics

_FIELD_ALIASES: dict[str, tuple[str, ...]] = {
    "epoch": ("epoch", "step", "e"),
    "train_loss": ("train_loss", "loss", "training_loss"),
    "val_loss": ("val_loss", "validation_loss", "valid_loss"),
    "accuracy": ("accuracy", "acc", "val_accuracy"),
    "gpu_utilization": ("gpu_utilization", "gpu_util", "gpu_usage"),
    "cpu_utilization": ("cpu_utilization", "cpu_util", "cpu_usage"),
    "vram_gb": ("vram_gb", "vram", "gpu_memory"),
    "vram_percent": ("vram_percent", "vram_usage"),
    "power_watts": ("power_watts", "power_w", "power", "gpu_power"),
}

_REQUIRED_FIELDS = ("epoch",)


class TrainingLogParser:
    """Parses training logs from CSV or JSON into a list of EpochMetrics."""

    def parse(self, path: Path) -> list[EpochMetrics]:
        path = Path(path)
        if not path.exists():
            raise FileNotFoundError(f"Training log not found: {path}")

        suffix = path.suffix.lower()
        if suffix == ".json":
            return self._parse_json(path)
        if suffix == ".csv":
            return self._parse_csv(path)

        raise ValueError(f"Unsupported training log format: {suffix or '(none)'}")

    def _parse_csv(self, path: Path) -> list[EpochMetrics]:
        with path.open(newline="", encoding="utf-8") as handle:
            reader = csv.DictReader(handle)
            if reader.fieldnames is None:
                raise ValueError(f"Training log has no header row: {path}")
            column_map = self._map_columns(reader.fieldnames)
            self._require_epoch_column(column_map, path)
            return [self._row_to_epoch(row, column_map) for row in reader]

    def _parse_json(self, path: Path) -> list[EpochMetrics]:
        raw = json.loads(path.read_text(encoding="utf-8"))

        if isinstance(raw, dict):
            entries = raw.get("epochs")
            if not isinstance(entries, list):
                raise ValueError(f"JSON training log must contain an 'epochs' list: {path}")
        elif isinstance(raw, list):
            entries = raw
        else:
            raise ValueError(f"Unsupported JSON training log structure: {path}")

        if not entries:
            return []

        column_map = self._map_columns(entries[0].keys())
        self._require_epoch_column(column_map, path)
        return [self._row_to_epoch(entry, column_map) for entry in entries]

    @staticmethod
    def _map_columns(columns: Any) -> dict[str, str]:
        """Map canonical field names to the actual column/key name present."""
        lower_lookup = {str(name).strip().lower(): name for name in columns}
        column_map: dict[str, str] = {}
        for canonical, aliases in _FIELD_ALIASES.items():
            for alias in aliases:
                if alias in lower_lookup:
                    column_map[canonical] = lower_lookup[alias]
                    break
        return column_map

    @staticmethod
    def _require_epoch_column(column_map: dict[str, str], path: Path) -> None:
        missing = [field for field in _REQUIRED_FIELDS if field not in column_map]
        if missing:
            raise ValueError(
                f"Training log {path} is missing required column(s): {', '.join(missing)}"
            )

    @staticmethod
    def _row_to_epoch(row: dict[str, Any], column_map: dict[str, str]) -> EpochMetrics:
        def get(field: str) -> Any:
            key = column_map.get(field)
            if key is None:
                return None
            value = row.get(key)
            if value in (None, ""):
                return None
            return value

        return EpochMetrics(
            epoch=int(float(get("epoch"))),
            train_loss=_to_float(get("train_loss")),
            val_loss=_to_float(get("val_loss")),
            accuracy=_to_float(get("accuracy")),
            gpu_utilization=_to_float(get("gpu_utilization")),
            cpu_utilization=_to_float(get("cpu_utilization")),
            vram_gb=_to_float(get("vram_gb")),
            vram_percent=_to_float(get("vram_percent")),
            power_watts=_to_float(get("power_watts")),
        )


def _to_float(value: Any) -> float | None:
    if value is None:
        return None
    return float(value)
