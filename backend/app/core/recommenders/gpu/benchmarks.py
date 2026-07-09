"""Load GPU training benchmark knowledge from YAML."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import yaml

logger = logging.getLogger(__name__)


class BenchmarkRegistry:
    """Loads measured relative training throughput from knowledge/hardware/benchmarks.yaml.

    Real training speed is calibrated from published benchmarks (MLPerf, Lambda,
    Exxact, CoreWeave) rather than raw peak TFLOPS, since utilization varies widely
    across architectures and software stacks.
    """

    def __init__(self, knowledge_root: Path | str | None = None) -> None:
        self.knowledge_root = self._resolve_root(knowledge_root)
        self._data: dict[str, Any] = {}
        self._loaded = False

    @staticmethod
    def _resolve_root(knowledge_root: Path | str | None) -> Path:
        if knowledge_root is not None:
            return Path(knowledge_root).resolve()
        backend_root = Path(__file__).resolve().parents[4]
        return backend_root.parent / "knowledge"

    def load(self) -> dict[str, Any]:
        if self._loaded:
            return self._data

        benchmark_file = self.knowledge_root / "hardware" / "benchmarks.yaml"
        if not benchmark_file.exists():
            logger.warning("Benchmark file not found: %s", benchmark_file)
            self._data = {}
            self._loaded = True
            return self._data

        self._data = yaml.safe_load(benchmark_file.read_text(encoding="utf-8")) or {}
        self._loaded = True
        return self._data

    @property
    def metadata(self) -> dict[str, Any]:
        return self.load().get("metadata", {})

    @property
    def reference_throughput(self) -> float:
        return float(self.metadata.get("reference_throughput", 1.0))

    def entry(self, gpu_id: str) -> dict[str, Any] | None:
        return self.load().get("gpus", {}).get(gpu_id)

    def relative_throughput(self, gpu_id: str) -> float | None:
        """Return measured relative training throughput (A100 = 1.0), or None."""
        entry = self.entry(gpu_id)
        if not entry:
            return None
        value = entry.get("relative_training_throughput")
        return float(value) if value else None

    def is_approximate(self, gpu_id: str) -> bool:
        entry = self.entry(gpu_id)
        return bool(entry.get("approximate", True)) if entry else True

    def source(self, gpu_id: str) -> str | None:
        entry = self.entry(gpu_id)
        return entry.get("source") if entry else None
