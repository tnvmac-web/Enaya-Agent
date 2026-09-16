"""
Enaya Agent - Configuration
load_cli_config(), defaults, setup wizard.
Mirrors Hermes Agent's hermes_cli/config.py exactly.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import yaml

# =============================================================================
# Config Defaults
# =============================================================================

CONFIG_DEFAULTS = {
    "model": "openrouter:anthropic/claude-3.5-sonnet",
    "provider": "openrouter",
    "max_turns": 500,
    "temperature": 0.7,
    "top_p": 1.0,
    "toolsets": ["core", "research", "planning", "delegation", "synthesis"],
    "disabled_tools": [],
    "fallback_providers": [],
    "compression_threshold": 0.50,
    "compression_protect_last_n": 20,
    "prompt_caching": True,
    "prompt_caching_ttl": "5m",
    "agent_identity": "enaya",
}


# Optional environment variables for setup wizard
OPTIONAL_ENV_VARS = {
    "OPENROUTER_API_KEY": "OpenRouter API key",
    "ANTHROPIC_TOKEN": "Anthropic API token (or CLAUDE_CODE_OAUTH_TOKEN)",
    "OPENAI_API_KEY": "OpenAI API key",
    "NVIDIA_API_KEY": "NVIDIA NIM API key",
    "GOOGLE_API_KEY": "Google/Gemini API key",
    "GEMINI_API_KEY": "Gemini API key (alternative)",
    "OLLAMA_HOST": "Ollama host (default: http://localhost:11434)",
    "LMSTUDIO_HOST": "LM Studio host (default: http://localhost:1234)",
    "CUSTOM_API_KEY": "Custom OpenAI-compatible API key",
    "CUSTOM_BASE_URL": "Custom OpenAI-compatible base URL",
}


# =============================================================================
# Config Loading
# =============================================================================


def load_config(profile: str = "default") -> dict[str, Any]:
    """
    Load configuration for a profile.
    Returns merged config: defaults + config.yaml + env vars.
    """
    config = CONFIG_DEFAULTS.copy()

    # Load from config.yaml
    enaya_home = Path(os.environ.get("ENAYA_HOME", Path.home() / ".enaya"))
    if profile != "default":
        enaya_home = enaya_home / "profiles" / profile

    config_file = enaya_home / "config.yaml"
    if config_file.exists():
        try:
            with open(config_file) as f:
                file_config = yaml.safe_load(f) or {}
                config.update(file_config)
        except Exception:
            pass

    # Load from .env (environment variables take precedence)
    env_file = enaya_home / ".env"
    if env_file.exists():
        _load_env_file(env_file)

    # Environment variables override everything
    _apply_env_overrides(config)

    return config


def _load_env_file(env_file: Path) -> None:
    """Load environment variables from .env file."""
    try:
        for line in env_file.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, value = line.split("=", 1)
                key = key.strip()
                value = value.strip().strip('"').strip("'")
                if key not in os.environ:
                    os.environ[key] = value
    except Exception:
        pass


def _apply_env_overrides(config: dict[str, Any]) -> None:
    """Apply environment variable overrides to config."""
    env_mappings = {
        "ENAYA_MODEL": "model",
        "ENAYA_PROVIDER": "provider",
        "ENAYA_MAX_TURNS": ("max_turns", int),
        "ENAYA_TEMPERATURE": ("temperature", float),
        "ENAYA_TOOLSETS": ("toolsets", lambda x: x.split(",")),
        "ENAYA_DISABLED_TOOLS": ("disabled_tools", lambda x: x.split(",")),
    }

    for env_key, config_spec in env_mappings.items():
        value = os.environ.get(env_key)
        if value is not None:
            if isinstance(config_spec, tuple):
                key, converter = config_spec
                config[key] = converter(value)
            else:
                config[config_spec] = value


def save_config(profile: str, config: dict[str, Any]) -> None:
    """Save configuration to config.yaml."""
    enaya_home = Path(os.environ.get("ENAYA_HOME", Path.home() / ".enaya"))
    if profile != "default":
        enaya_home = enaya_home / "profiles" / profile

    enaya_home.mkdir(parents=True, exist_ok=True)
    config_file = enaya_home / "config.yaml"

    # Only save non-default values
    to_save = {k: v for k, v in config.items() if v != CONFIG_DEFAULTS.get(k)}

    with open(config_file, "w") as f:
        yaml.dump(to_save, f, default_flow_style=False, sort_keys=False)


def get_config_path(profile: str = "default") -> Path:
    """Get config file path for profile."""
    enaya_home = Path(os.environ.get("ENAYA_HOME", Path.home() / ".enaya"))
    if profile != "default":
        enaya_home = enaya_home / "profiles" / profile
    return enaya_home / "config.yaml"


def get_env_path(profile: str = "default") -> Path:
    """Get .env file path for profile."""
    enaya_home = Path(os.environ.get("ENAYA_HOME", Path.home() / ".enaya"))
    if profile != "default":
        enaya_home = enaya_home / "profiles" / profile
    return enaya_home / ".env"
