#!/usr/bin/env python3
"""
Enaya Agent - Plugin System
Extensible plugin architecture for tools, hooks, skills, and more.
"""

from __future__ import annotations

import importlib.util
import json
import os
import sys
from abc import ABC, abstractmethod
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

import yaml

from enaya.gateway.runner import GatewayRunner
from enaya.tools.registry import registry

# =============================================================================
# Plugin Manifest
# =============================================================================

@dataclass
class PluginManifest:
    """Plugin manifest (PLUGIN.yaml)."""
    schema_version: int = 2
    name: str = ""
    version: str = "1.0.0"
    description: str = ""
    author: str = ""
    license: str = "MIT"
    kind: str = "tool"  # tool, platform, model-provider, memory, context-engine, image-gen, video-gen, web-search, browser, terminal-environment
    capabilities: dict[str, bool] = field(default_factory=dict)
    dependencies: list[str] = field(default_factory=list)
    python_requires: str = ">=3.11"
    entry_point: str = "plugin_init"  # function to call on load

    @classmethod
    def from_file(cls, path: Path) -> PluginManifest:
        with open(path) as f:
            data = yaml.safe_load(f)
        return cls(**data)

    def to_file(self, path: Path) -> None:
        with open(path, "w") as f:
            yaml.dump(self.__dict__, f, default_flow_style=False)


# =============================================================================
# Plugin Context
# =============================================================================

class PluginContext:
    """Context provided to plugins for registration."""

    def __init__(self, plugin_dir: Path, plugin_name: str):
        self.plugin_dir = plugin_dir
        self.plugin_name = plugin_name
        self._state_dir = Path.home() / ".enaya" / "plugins" / plugin_name / "state"
        self._state_dir.mkdir(parents=True, exist_ok=True)
        self._data_dir = plugin_dir / "data"
        self._skills_dir = plugin_dir / "skills"

    @property
    def state_dir(self) -> Path:
        return self._state_dir

    def data_path(self, filename: str) -> Path:
        return self._data_dir / filename

    def register_tool(
        self,
        name: str,
        toolset: str,
        schema: dict,
        handler: Callable,
        check_fn: Callable[[], bool] = lambda: True,
        is_async: bool = False,
    ) -> None:
        """Register a tool."""
        registry.register(
            name=name,
            toolset=toolset,
            schema=schema,
            handler=handler,
            check_fn=check_fn,
            is_async=is_async,
        )

    def register_hook(self, event: str, handler: Callable) -> None:
        """Register a gateway hook."""
        # This would integrate with GatewayRunner's hook system
        pass

    def register_skill(self, name: str, skill_content: str) -> None:
        """Register a skill."""
        skill_dir = self._skills_dir / name
        skill_dir.mkdir(parents=True, exist_ok=True)
        (skill_dir / "SKILL.md").write_text(skill_content)

    def register_cli_command(self, command: Callable) -> None:
        """Register a CLI command."""
        # This would integrate with Click CLI
        pass

    def store_settings(self, key: str, value: Any) -> None:
        """Store plugin settings."""
        settings_file = self._state_dir / "settings.json"
        settings = {}
        if settings_file.exists():
            settings = json.loads(settings_file.read_text())
        settings[key] = value
        settings_file.write_text(json.dumps(settings, indent=2))

    def get_settings(self, key: str, default: Any = None) -> Any:
        """Get plugin settings."""
        settings_file = self._state_dir / "settings.json"
        if settings_file.exists():
            return json.loads(settings_file.read_text()).get(key, default)
        return default

    def get_or_create_shared(self, key: str, factory: Callable) -> Any:
        """Thread-safe lazy singleton."""
        # Simplified - real implementation would use threading.Lock
        return factory()


# =============================================================================
# Plugin Base Class
# =============================================================================

class PluginBase(ABC):
    """Base class for plugins."""

    def __init__(self, context: PluginContext):
        self.context = context
        self.name = context.plugin_name

    @abstractmethod
    def initialize(self) -> None:
        """Initialize plugin."""
        pass

    def shutdown(self) -> None:
        """Cleanup on shutdown."""
        pass


# =============================================================================
# Plugin Manager
# =============================================================================

class PluginManager:
    """Manages plugin discovery, loading, and lifecycle."""

    def __init__(self, profile: str = "default"):
        self.profile = profile
        self.plugins: dict[str, PluginBase] = {}
        self._plugin_dirs = [
            Path.home() / ".enaya" / "plugins",           # User plugins
            Path.cwd() / ".enaya" / "plugins",             # Project plugins
            Path(__file__).parent.parent / "plugins",      # Bundled plugins
        ]

    def discover_plugins(self) -> list[Path]:
        """Discover all plugin directories."""
        plugins = []
        for base_dir in self._plugin_dirs:
            if base_dir.exists():
                for plugin_dir in base_dir.iterdir():
                    if plugin_dir.is_dir() and (plugin_dir / "PLUGIN.yaml").exists():
                        plugins.append(plugin_dir)
        return plugins

    def load_plugin(self, plugin_dir: Path) -> PluginBase | None:
        """Load a single plugin."""
        try:
            manifest = PluginManifest.from_file(plugin_dir / "PLUGIN.yaml")

            # Check if already loaded
            if manifest.name in self.plugins:
                print(f"Plugin {manifest.name} already loaded, skipping")
                return self.plugins[manifest.name]

            # Create context
            context = PluginContext(plugin_dir, manifest.name)

            # Load plugin module
            entry_file = plugin_dir / "plugin.py"
            if not entry_file.exists():
                # Try __init__.py
                entry_file = plugin_dir / "__init__.py"

            if not entry_file.exists():
                print(f"Plugin {manifest.name} has no entry point")
                return None

            spec = importlib.util.spec_from_file_location(manifest.name, entry_file)
            module = importlib.util.module_from_spec(spec)
            sys.modules[manifest.name] = module
            spec.loader.exec_module(module)

            # Call entry point
            if hasattr(module, manifest.entry_point):
                plugin_instance = getattr(module, manifest.entry_point)(context)
            elif hasattr(module, "Plugin"):
                plugin_instance = module.Plugin(context)
            else:
                print(f"Plugin {manifest.name} has no valid entry point")
                return None

            # Initialize
            plugin_instance.initialize()

            self.plugins[manifest.name] = plugin_instance
            print(f"Loaded plugin: {manifest.name} v{manifest.version}")
            return plugin_instance

        except Exception as e:
            print(f"Failed to load plugin {plugin_dir}: {e}")
            return None

    def load_all(self) -> list[PluginBase]:
        """Load all discovered plugins."""
        loaded = []
        for plugin_dir in self.discover_plugins():
            plugin = self.load_plugin(plugin_dir)
            if plugin:
                loaded.append(plugin)
        return loaded

    def unload_plugin(self, name: str) -> bool:
        """Unload a plugin."""
        if name in self.plugins:
            self.plugins[name].shutdown()
            del self.plugins[name]
            return True
        return False

    def get_plugin(self, name: str) -> PluginBase | None:
        return self.plugins.get(name)

    def list_plugins(self) -> list[dict]:
        return [
            {"name": p.name, "version": getattr(p, "version", "unknown")}
            for p in self.plugins.values()
        ]


# =============================================================================
# Built-in Plugin Types
# =============================================================================

# Tool Plugin
class ToolPlugin(PluginBase):
    """Plugin that registers tools."""

    def initialize(self) -> None:
        # Override in subclass
        pass

    def register_tool(self, name: str, toolset: str, schema: dict, handler: Callable, check_fn: Callable = lambda: True) -> None:
        self.context.register_tool(name, toolset, schema, handler, check_fn)


# Hook Plugin
class HookPlugin(PluginBase):
    """Plugin that registers gateway hooks."""

    def initialize(self) -> None:
        pass

    def register_hook(self, event: str, handler: Callable) -> None:
        self.context.register_hook(event, handler)


# Skill Plugin
class SkillPlugin(PluginBase):
    """Plugin that bundles skills."""

    def initialize(self) -> None:
        pass

    def register_skill(self, name: str, skill_content: str) -> None:
        self.context.register_skill(name, skill_content)


# Platform Plugin
class PlatformPlugin(PluginBase):
    """Plugin that adds a messaging platform adapter."""

    def initialize(self) -> None:
        pass

    def register_adapter(self, runner, adapter_class) -> None:
        # This would be called by the runner
        pass


# Memory Provider Plugin
class MemoryProviderPlugin(PluginBase):
    """Plugin that provides a memory backend."""

    def initialize(self) -> None:
        pass


# Context Engine Plugin
class ContextEnginePlugin(PluginBase):
    """Plugin that provides a context compression engine."""

    def initialize(self) -> None:
        pass


# =============================================================================
# Plugin CLI Commands
# =============================================================================

def plugin_doctor(plugin_path: str) -> dict:
    """Validate a plugin."""
    path = Path(plugin_path)
    result = {
        "valid": False,
        "errors": [],
        "warnings": [],
    }

    if not path.exists():
        result["errors"].append("Plugin directory does not exist")
        return result

    manifest_path = path / "PLUGIN.yaml"
    if not manifest_path.exists():
        result["errors"].append("PLUGIN.yaml not found")
        return result

    try:
        manifest = PluginManifest.from_file(manifest_path)

        # Check required fields
        if not manifest.name:
            result["errors"].append("Plugin name is required")
        if not manifest.version:
            result["errors"].append("Plugin version is required")
        if not manifest.description:
            result["warnings"].append("Description is recommended")

        # Check entry point
        entry_file = path / "plugin.py"
        if not entry_file.exists():
            entry_file = path / "__init__.py"
        if not entry_file.exists():
            result["errors"].append("No entry point (plugin.py or __init__.py)")

        # Check dependencies
        for dep in manifest.dependencies:
            result["warnings"].append(f"Dependency: {dep}")

        result["valid"] = len(result["errors"]) == 0

    except Exception as e:
        result["errors"].append(f"Failed to parse manifest: {e}")

    return result


def create_plugin_skeleton(plugin_dir: Path, name: str, kind: str = "tool") -> None:
    """Create a new plugin skeleton."""
    plugin_dir.mkdir(parents=True, exist_ok=True)

    # Manifest
    manifest = PluginManifest(
        name=name,
        version="1.0.0",
        description=f"{name} plugin",
        kind=kind,
        capabilities={
            "tools": kind == "tool",
            "hooks": kind == "hook",
            "skills": kind == "skill",
        },
    )
    manifest.to_file(plugin_dir / "PLUGIN.yaml")

    # Entry point
    (plugin_dir / "plugin.py").write_text(f'''#!/usr/bin/env python3
"""
{name} Plugin
"""

from enaya.plugins import PluginBase, PluginContext

class Plugin(PluginBase):
    def initialize(self):
        """Initialize plugin."""
        print(f"{name} plugin initialized")
        # Register tools, hooks, skills here
''')

    # README
    (plugin_dir / "README.md").write_text(f"# {name}\n\n{name} plugin for Enaya Agent.\n")

    print(f"Created plugin skeleton at {plugin_dir}")


# =============================================================================
# Global Plugin Manager Instance
# =============================================================================

_plugin_manager: PluginManager | None = None


def get_plugin_manager(profile: str = "default") -> PluginManager:
    """Get global plugin manager instance."""
    global _plugin_manager
    if _plugin_manager is None:
        _plugin_manager = PluginManager(profile)
    return _plugin_manager


def load_plugins(profile: str = "default") -> list:
    """Load all plugins for a profile."""
    manager = get_plugin_manager(profile)
    return manager.load_all()


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1:
        if sys.argv[1] == "doctor":
            path = sys.argv[2] if len(sys.argv) > 2 else "."
            result = plugin_doctor(path)
            print(json.dumps(result, indent=2))
        elif sys.argv[1] == "create":
            name = sys.argv[2] if len(sys.argv) > 2 else "my-plugin"
            kind = sys.argv[3] if len(sys.argv) > 3 else "tool"
            create_plugin_skeleton(Path.cwd() / name, name, kind)
        else:
            print("Usage: python -m enaya.plugins [doctor|create] [args]")
    else:
        manager = PluginManager()
        plugins = manager.load_all()
        print(f"Loaded {len(plugins)} plugins")
        for p in plugins:
            print(f"  - {p.name}")
