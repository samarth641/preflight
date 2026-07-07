"""Initialize and configure the plugin registry."""

from app.core.plugins.implementations.rule_based import RuleBasedEnginePlugin
from app.core.plugins.registry import registry


def setup_plugins() -> None:
    """Register built-in plugins. Call once at application startup."""
    if "rule-based" not in registry._plugins:
        registry.register(RuleBasedEnginePlugin(), set_default=True)
    registry.discover()
