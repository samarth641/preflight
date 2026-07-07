"""Default rule-based engine plugin."""

from __future__ import annotations

from typing import Any

from app.core.engine.engine import KnowledgeEngine
from app.core.engine.models import EngineResult
from app.core.knowledge.loader import RuleLoader
from app.core.plugins.base import EnginePlugin, PluginMetadata


class RuleBasedEnginePlugin(EnginePlugin):
    """Wraps the YAML knowledge engine as a pluggable backend."""

    def __init__(self, loader: RuleLoader | None = None) -> None:
        self._loader = loader or RuleLoader()
        self._engine = KnowledgeEngine(loader=self._loader)

    @property
    def metadata(self) -> PluginMetadata:
        return PluginMetadata(
            name="rule-based",
            version="0.1.0",
            description="Rule-based expert system using YAML knowledge base",
            is_default=True,
            capabilities=["evaluate", "explain", "reload"],
        )

    def evaluate(self, context: dict[str, Any], **kwargs: Any) -> EngineResult:
        return self._engine.evaluate(context, **kwargs)

    def reload(self) -> None:
        self._engine.reload()

    def health_check(self) -> dict[str, Any]:
        base = super().health_check()
        base["rule_count"] = self._engine.knowledge_base.rule_count
        base["categories"] = self._engine.knowledge_base.categories
        base["load_errors"] = self._engine.knowledge_base.load_errors
        return base

    def explain(self, rule_id: str):
        return self._engine.explain(rule_id)
