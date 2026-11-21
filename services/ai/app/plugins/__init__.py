"""Plugin registry with auto-discovery.

Every module in this package that defines a concrete `Plugin` subclass is loaded at import
time. Files starting with "_" and `base.py` are helpers and are skipped.
"""

from __future__ import annotations

import importlib
import inspect
import pkgutil

from .base import Plugin, PluginFinding, PluginResult

__all__ = ["Plugin", "PluginFinding", "PluginResult", "discover", "get_plugins"]

_PLUGINS: dict[str, Plugin] | None = None


def discover() -> dict[str, Plugin]:
    found: dict[str, Plugin] = {}
    for info in pkgutil.iter_modules(__path__):
        if info.name.startswith("_") or info.name == "base":
            continue
        module = importlib.import_module(f"{__name__}.{info.name}")
        for _, cls in inspect.getmembers(module, inspect.isclass):
            if issubclass(cls, Plugin) and cls is not Plugin and cls.__module__ == module.__name__:
                if not cls.id:
                    raise ValueError(f"plugin {cls.__name__} has no id")
                if cls.id in found:
                    raise ValueError(f"duplicate plugin id {cls.id}")
                found[cls.id] = cls()
    return dict(sorted(found.items(), key=lambda kv: (kv[1].module is None, kv[1].module or 0, kv[0])))


def get_plugins() -> dict[str, Plugin]:
    global _PLUGINS
    if _PLUGINS is None:
        _PLUGINS = discover()
    return _PLUGINS
