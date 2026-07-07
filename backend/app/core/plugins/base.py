"""Plugin base classes for extensible engine backends."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from pydantic import BaseModel, Field

from app.core.engine.models import EngineResult


class PluginMetadata(BaseModel):
    """Metadata describing a registered engine plugin."""

    name: str
    version: str
    description: str
    author: str = "Preflight"
    is_default: bool = False
    capabilities: list[str] = Field(default_factory=list)


class EnginePlugin(ABC):
    """Abstract base for knowledge engine backends.

    Implementations:
    - RuleBasedEnginePlugin (default, wraps KnowledgeEngine)
    - Future: LLMEnginePlugin for generative recommendations
    """

    @property
    @abstractmethod
    def metadata(self) -> PluginMetadata:
        """Return plugin metadata."""

    @abstractmethod
    def evaluate(self, context: dict[str, Any], **kwargs: Any) -> EngineResult:
        """Evaluate context and return recommendations."""

    @abstractmethod
    def reload(self) -> None:
        """Reload plugin resources (e.g. knowledge base)."""

    def health_check(self) -> dict[str, Any]:
        """Optional health check for doctor command."""
        return {"status": "ok", "plugin": self.metadata.name}
