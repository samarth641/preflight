"""Plugin system for extensible engine backends."""

from app.core.plugins.base import EnginePlugin, PluginMetadata
from app.core.plugins.registry import PluginRegistry

__all__ = ["EnginePlugin", "PluginMetadata", "PluginRegistry"]
