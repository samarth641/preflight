"""Plugin registry for engine backend discovery and selection."""

from __future__ import annotations

import importlib
import logging
import pkgutil
from typing import Any

from app.core.plugins.base import EnginePlugin, PluginMetadata

logger = logging.getLogger(__name__)


class PluginRegistry:
    """Registry for engine plugins with auto-discovery support."""

    def __init__(self) -> None:
        self._plugins: dict[str, EnginePlugin] = {}
        self._default_plugin: str | None = None

    def register(self, plugin: EnginePlugin, *, set_default: bool = False) -> None:
        name = plugin.metadata.name
        self._plugins[name] = plugin

        if set_default or plugin.metadata.is_default:
            self._default_plugin = name

        logger.info("Registered engine plugin: %s v%s", name, plugin.metadata.version)

    def get(self, name: str) -> EnginePlugin:
        if name not in self._plugins:
            available = ", ".join(self._plugins.keys()) or "(none)"
            raise KeyError(f"Plugin '{name}' not found. Available: {available}")
        return self._plugins[name]

    def get_default(self) -> EnginePlugin:
        if self._default_plugin is None:
            if not self._plugins:
                raise RuntimeError("No plugins registered")
            self._default_plugin = next(iter(self._plugins))
        return self._plugins[self._default_plugin]

    def list_plugins(self) -> list[PluginMetadata]:
        return [plugin.metadata for plugin in self._plugins.values()]

    def evaluate(self, context: dict[str, Any], plugin_name: str | None = None, **kwargs: Any):
        plugin = self.get(plugin_name) if plugin_name else self.get_default()
        return plugin.evaluate(context, **kwargs)

    def discover(self, package_name: str = "app.core.plugins.implementations") -> int:
        """Auto-discover and register plugins from a package."""
        discovered = 0

        try:
            package = importlib.import_module(package_name)
        except ImportError:
            logger.debug("Plugin package not found: %s", package_name)
            return 0

        if not hasattr(package, "__path__"):
            return 0

        for module_info in pkgutil.iter_modules(package.__path__, package.__name__ + "."):
            try:
                module = importlib.import_module(module_info.name)
            except Exception as exc:
                logger.warning("Failed to import plugin module %s: %s", module_info.name, exc)
                continue

            for attr_name in dir(module):
                attr = getattr(module, attr_name)
                if (
                    isinstance(attr, type)
                    and issubclass(attr, EnginePlugin)
                    and attr is not EnginePlugin
                ):
                    plugin = attr()
                    self.register(plugin, set_default=plugin.metadata.is_default)
                    discovered += 1

        return discovered


# Global singleton registry
registry = PluginRegistry()
