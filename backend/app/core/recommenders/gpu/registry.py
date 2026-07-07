"""Load GPU and cloud provider knowledge from YAML."""

from __future__ import annotations

import logging
from pathlib import Path

import yaml

from app.core.recommenders.gpu.models import CloudOffering, GPUSpec

logger = logging.getLogger(__name__)


class GPURegistry:
    """Loads GPU specifications from knowledge/hardware/gpus.yaml."""

    def __init__(self, knowledge_root: Path | str | None = None) -> None:
        self.knowledge_root = self._resolve_root(knowledge_root)
        self._gpus: list[GPUSpec] = []
        self._loaded = False

    @staticmethod
    def _resolve_root(knowledge_root: Path | str | None) -> Path:
        if knowledge_root is not None:
            return Path(knowledge_root).resolve()
        backend_root = Path(__file__).resolve().parents[4]
        return backend_root.parent / "knowledge"

    def load(self) -> list[GPUSpec]:
        if self._loaded:
            return self._gpus

        gpu_file = self.knowledge_root / "hardware" / "gpus.yaml"
        if not gpu_file.exists():
            logger.warning("GPU knowledge file not found: %s", gpu_file)
            return []

        raw = yaml.safe_load(gpu_file.read_text(encoding="utf-8"))
        gpu_payloads = raw.get("gpus", []) if isinstance(raw, dict) else []

        self._gpus = [GPUSpec.model_validate(payload) for payload in gpu_payloads]
        self._loaded = True
        logger.info("Loaded %d GPU specs", len(self._gpus))
        return self._gpus

    @property
    def gpus(self) -> list[GPUSpec]:
        return self.load()

    def get(self, gpu_id: str) -> GPUSpec | None:
        for gpu in self.gpus:
            if gpu.id == gpu_id:
                return gpu
        return None

    def by_vendor(self, vendor: str) -> list[GPUSpec]:
        return [gpu for gpu in self.gpus if gpu.vendor == vendor]

    def by_tier(self, tier: str) -> list[GPUSpec]:
        return [gpu for gpu in self.gpus if gpu.training_speed_tier == tier]


class CloudRegistry:
    """Loads cloud provider offerings from knowledge/hardware/cloud.yaml."""

    def __init__(self, knowledge_root: Path | str | None = None) -> None:
        self.knowledge_root = self._resolve_root(knowledge_root)
        self._offerings: list[CloudOffering] = []
        self._loaded = False

    @staticmethod
    def _resolve_root(knowledge_root: Path | str | None) -> Path:
        if knowledge_root is not None:
            return Path(knowledge_root).resolve()
        backend_root = Path(__file__).resolve().parents[4]
        return backend_root.parent / "knowledge"

    def load(self, gpu_registry: GPURegistry | None = None) -> list[CloudOffering]:
        if self._loaded:
            return self._offerings

        cloud_file = self.knowledge_root / "hardware" / "cloud.yaml"
        if not cloud_file.exists():
            logger.warning("Cloud knowledge file not found: %s", cloud_file)
            return []

        registry = gpu_registry or GPURegistry(self.knowledge_root)
        raw = yaml.safe_load(cloud_file.read_text(encoding="utf-8"))
        providers = raw.get("providers", []) if isinstance(raw, dict) else []

        offerings: list[CloudOffering] = []
        for provider in providers:
            for item in provider.get("offerings", []):
                gpu = registry.get(item["gpu_id"])
                offerings.append(
                    CloudOffering(
                        provider_id=provider["id"],
                        provider_name=provider["name"],
                        provider_url=provider.get("url", ""),
                        gpu_id=item["gpu_id"],
                        gpu_name=gpu.name if gpu else item["gpu_id"],
                        instance_type=item["instance_type"],
                        vram_gb=item.get("vram_gb", gpu.vram_gb if gpu else 0),
                        gpu_count=item.get("gpu_count", 1),
                        notes=item.get("notes", ""),
                    )
                )

        self._offerings = offerings
        self._loaded = True
        return self._offerings

    @property
    def offerings(self) -> list[CloudOffering]:
        return self.load()
