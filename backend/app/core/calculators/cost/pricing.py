"""Load pricing knowledge from YAML."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import yaml

logger = logging.getLogger(__name__)


class PricingRegistry:
    """Loads cloud pricing and defaults from knowledge/hardware/pricing.yaml."""

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

        pricing_file = self.knowledge_root / "hardware" / "pricing.yaml"
        if not pricing_file.exists():
            logger.warning("Pricing file not found: %s", pricing_file)
            self._data = {}
            self._loaded = True
            return self._data

        self._data = yaml.safe_load(pricing_file.read_text(encoding="utf-8")) or {}
        self._loaded = True
        return self._data

    @property
    def defaults(self) -> dict[str, float]:
        return self.load().get("defaults", {})

    @property
    def baseline(self) -> dict[str, Any]:
        return self.load().get("training_baseline", {})

    def cloud_hourly_rate(self, gpu_id: str, provider: str | None) -> float | None:
        rates = self.load().get("cloud_hourly_usd", {}).get(gpu_id, {})
        if not rates:
            return None
        if provider and provider in rates:
            return float(rates[provider])
        # fallback to cheapest listed provider with a positive rate
        numeric = [float(v) for v in rates.values() if isinstance(v, (int, float)) and v > 0]
        return min(numeric) if numeric else None

    def resolve_cloud_rate(
        self, gpu_id: str, provider: str | None
    ) -> tuple[float | None, str | None]:
        """Return (hourly_rate, provider_id_used). Falls back to cheapest listed rate."""
        rates = self.load().get("cloud_hourly_usd", {}).get(gpu_id, {})
        if not rates:
            return None, None
        if provider and provider in rates and float(rates[provider]) > 0:
            return float(rates[provider]), provider
        positive = {
            k: float(v) for k, v in rates.items() if isinstance(v, (int, float)) and float(v) > 0
        }
        if not positive:
            return None, None
        best = min(positive, key=positive.get)
        return positive[best], best
