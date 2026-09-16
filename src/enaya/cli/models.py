"""
Enaya Agent - Model Catalog
Model catalog, aliases, context windows.
Mirrors Hermes Agent's hermes_cli/models.py exactly.
"""

from __future__ import annotations

from typing import Any


# =============================================================================
# Provider Model Catalogs
# =============================================================================

_PROVIDER_MODELS: dict[str, dict[str, dict[str, Any]]] = {
    "openrouter": {
        "anthropic/claude-3.5-sonnet": {"context_window": 200000, "supports_tools": True, "supports_vision": True},
        "anthropic/claude-3.5-haiku": {"context_window": 200000, "supports_tools": True, "supports_vision": True},
        "anthropic/claude-3-opus": {"context_window": 200000, "supports_tools": True, "supports_vision": True},
        "google/gemini-1.5-pro": {"context_window": 2000000, "supports_tools": True, "supports_vision": True},
        "google/gemini-1.5-flash": {"context_window": 1000000, "supports_tools": True, "supports_vision": True},
        "openai/gpt-4o": {"context_window": 128000, "supports_tools": True, "supports_vision": True},
        "openai/gpt-4o-mini": {"context_window": 128000, "supports_tools": True, "supports_vision": True},
        "openai/gpt-4-turbo": {"context_window": 128000, "supports_tools": True, "supports_vision": True},
        "meta-llama/llama-3.1-405b-instruct": {"context_window": 128000, "supports_tools": True, "supports_vision": False},
        "meta-llama/llama-3.1-70b-instruct": {"context_window": 128000, "supports_tools": True, "supports_vision": False},
        "mistralai/mistral-large": {"context_window": 128000, "supports_tools": True, "supports_vision": False},
        "nvidia/nemotron-3-ultra": {"context_window": 128000, "supports_tools": True, "supports_vision": False},
        "nvidia/nemotron-3-ultra-550b-a55b:free": {"context_window": 128000, "supports_tools": True, "supports_vision": False},
    },

    "openai": {
        "gpt-4o": {"context_window": 128000, "supports_tools": True, "supports_vision": True},
        "gpt-4o-mini": {"context_window": 128000, "supports_tools": True, "supports_vision": True},
        "gpt-4-turbo": {"context_window": 128000, "supports_tools": True, "supports_vision": True},
        "gpt-4": {"context_window": 8192, "supports_tools": True, "supports_vision": False},
        "gpt-3.5-turbo": {"context_window": 16384, "supports_tools": True, "supports_vision": False},
        "o1-preview": {"context_window": 128000, "supports_tools": False, "supports_vision": False},
        "o1-mini": {"context_window": 128000, "supports_tools": False, "supports_vision": False},
    },

    "anthropic": {
        "claude-3-5-sonnet-20241022": {"context_window": 200000, "supports_tools": True, "supports_vision": True},
        "claude-3-5-haiku-20241022": {"context_window": 200000, "supports_tools": True, "supports_vision": True},
        "claude-3-opus-20240229": {"context_window": 200000, "supports_tools": True, "supports_vision": True},
        "claude-3-sonnet-20240229": {"context_window": 200000, "supports_tools": True, "supports_vision": True},
        "claude-3-haiku-20240307": {"context_window": 200000, "supports_tools": True, "supports_vision": True},
    },

    "nvidia": {
        "nvidia/nemotron-3-ultra": {"context_window": 128000, "supports_tools": True, "supports_vision": False},
        "nvidia/llama-3.1-nemotron-70b-instruct": {"context_window": 128000, "supports_tools": True, "supports_vision": False},
        "nvidia/nemotron-3-ultra-550b-a55b": {"context_window": 128000, "supports_tools": True, "supports_vision": False},
    },

    "google": {
        "gemini-1.5-pro": {"context_window": 2000000, "supports_tools": True, "supports_vision": True},
        "gemini-1.5-flash": {"context_window": 1000000, "supports_tools": True, "supports_vision": True},
        "gemini-1.0-pro": {"context_window": 32768, "supports_tools": True, "supports_vision": True},
    },

    "ollama": {
        "llama3.1": {"context_window": 128000, "supports_tools": True, "supports_vision": False},
        "llama3.2": {"context_window": 128000, "supports_tools": True, "supports_vision": False},
        "mistral": {"context_window": 32768, "supports_tools": False, "supports_vision": False},
        "codellama": {"context_window": 16384, "supports_tools": False, "supports_vision": False},
        "phi3": {"context_window": 4096, "supports_tools": False, "supports_vision": False},
    },

    "lmstudio": {
        "local-model": {"context_window": 32768, "supports_tools": False, "supports_vision": False},
    },

    "custom": {},
}


# =============================================================================
# Model Aliases (for user-friendly switching)
# =============================================================================

_PROVIDER_ALIASES: dict[str, str] = {
    # OpenRouter shortcuts
    "sonnet": "openrouter:anthropic/claude-3.5-sonnet",
    "haiku": "openrouter:anthropic/claude-3.5-haiku",
    "opus": "openrouter:anthropic/claude-3-opus",
    "gemini-pro": "openrouter:google/gemini-1.5-pro",
    "gemini-flash": "openrouter:google/gemini-1.5-flash",
    "gpt4o": "openrouter:openai/gpt-4o",
    "gpt4o-mini": "openrouter:openai/gpt-4o-mini",
    "llama405b": "openrouter:meta-llama/llama-3.1-405b-instruct",
    "llama70b": "openrouter:meta-llama/llama-3.1-70b-instruct",
    "mistral-large": "openrouter:mistralai/mistral-large",
    "nemotron": "openrouter:nvidia/nemotron-3-ultra",

    # Direct provider shortcuts
    "gpt-4o": "openai:gpt-4o",
    "gpt-4o-mini": "openai:gpt-4o-mini",
    "gpt-4-turbo": "openai:gpt-4-turbo",
    "claude-sonnet": "anthropic:claude-3-5-sonnet-20241022",
    "claude-haiku": "anthropic:claude-3-5-haiku-20241022",
    "claude-opus": "anthropic:claude-3-opus-20240229",
    "gemini-pro": "google:gemini-1.5-pro",
    "gemini-flash": "google:gemini-1.5-flash",
    "nemotron-ultra": "nvidia:nvidia/nemotron-3-ultra",
    "nemotron-70b": "nvidia:nvidia/llama-3.1-nemotron-70b-instruct",
}


def resolve_model_alias(model_spec: str) -> tuple[str, str]:
    """
    Resolve model alias to (provider, model).
    Returns (provider, model) tuple.
    """
    if model_spec in _PROVIDER_ALIASES:
        resolved = _PROVIDER_ALIASES[model_spec]
        if ":" in resolved:
            provider, model = resolved.split(":", 1)
            return provider, model
    return "custom", model_spec


def get_model_info(provider: str, model: str) -> dict[str, Any]:
    """Get model metadata."""
    return _PROVIDER_MODELS.get(provider, {}).get(model, {})


def list_models(provider: str = None) -> dict:
    """List all models, optionally filtered by provider."""
    if provider:
        return _PROVIDER_MODELS.get(provider, {})
    return _PROVIDER_MODELS


def get_context_window(provider: str, model: str) -> int:
    """Get context window for model."""
    info = get_model_info(provider, model)
    return info.get("context_window", 128000)


def supports_tools(provider: str, model: str) -> bool:
    """Check if model supports tools."""
    info = get_model_info(provider, model)
    return info.get("supports_tools", True)


def supports_vision(provider: str, model: str) -> bool:
    """Check if model supports vision."""
    info = get_model_info(provider, model)
    return info.get("supports_vision", False)