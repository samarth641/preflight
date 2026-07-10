"""Load demo experiment history from YAML fixtures."""

from __future__ import annotations

from pathlib import Path

import yaml

from app.core.monitors.training.models import ExperimentRecord

_REPO_ROOT = Path(__file__).resolve().parents[5]
DEFAULT_FIXTURES = _REPO_ROOT / "tests" / "fixtures" / "experiments"


def default_fixtures_dir() -> Path:
    return DEFAULT_FIXTURES


def load_demo_history(fixtures_dir: Path | None = None) -> tuple[list[ExperimentRecord], str | None]:
    root = fixtures_dir or default_fixtures_dir()
    path = root / "history.yaml"
    if not path.is_file():
        raise FileNotFoundError(f"Demo experiment history not found: {path}")

    raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    active_id = raw.get("active_experiment_id")
    records: list[ExperimentRecord] = []

    for item in raw.get("experiments", []):
        log_file = item.get("log_file")
        epochs_completed = item.get("epochs_completed") or 0
        if item.get("status") == "running" and not epochs_completed and log_file:
            csv_path = root / log_file
            if csv_path.is_file():
                epochs_completed = _count_epochs(csv_path)
        records.append(
            ExperimentRecord(
                id=item["id"],
                name=item["name"],
                model=item["model"],
                params_million=item["params_million"],
                dataset=item["dataset"],
                status=item["status"],
                gpu=item["gpu"],
                total_epochs=item["total_epochs"],
                epochs_completed=epochs_completed,
                final_accuracy=item.get("final_accuracy"),
                best_val_loss=item.get("best_val_loss"),
                convergence=item.get("convergence"),
                duration_hours=item.get("duration_hours"),
                started_at=item.get("started_at", ""),
                target_accuracy=item.get("target_accuracy"),
            )
        )

    return records, active_id


def resolve_log_path(experiment_id: str, fixtures_dir: Path | None = None) -> Path | None:
    root = fixtures_dir or default_fixtures_dir()
    path = root / "history.yaml"
    raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    for item in raw.get("experiments", []):
        if item.get("id") == experiment_id:
            log_file = item.get("log_file")
            if log_file:
                return root / log_file
    return None


def _count_epochs(csv_path: Path) -> int:
    lines = csv_path.read_text(encoding="utf-8").strip().splitlines()
    return max(0, len(lines) - 1)
