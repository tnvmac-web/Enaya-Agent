"""
Enaya Agent - Runtime Provider Resolution
Credential resolution, custom-endpoint runtime resolution.
Mirrors Hermes Agent's hermes_cli/runtime_provider.py exactly.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any, Optional

from enaya.cli.auth import ProviderConfig, PROVIDER_REGISTRY, _PROVIDER_ALIASES
from enaya.cli.models import _PROVIDER_MODELS


@dataclass
class RuntimeProvider:
    """Resolved provider configuration at runtime."""
    provider: str
    model: str
    base_url: Optional[str]
    api_key: Optional[str]
    api_mode: str
    source: str  # "cli", "config", "env", "default"
    metadata: dict = None

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


def resolve_runtime_provider(
    provider: Optional[str] = None,
    model: Optional[str] = None,
    base_url: Optional[str] = None,
    api_key: Optional[str] = None,
) -> RuntimeProvider:
    """
    Resolve provider configuration at runtime.
    Precedence:
    1. Explicit CLI/runtime request
    2. Config file (via load_config)
    3. Environment variables
    4. Provider-specific defaults or auto resolution
    """
    # Parse model string if it contains provider:model
    if model and ":" in model and not provider:
        provider, model = model.split(":", 1)

    # Resolve provider aliases
    if provider:
        provider = _PROVIDER_ALIASES.get(provider, provider)

    # For OpenRouter, strip provider prefix from model if present
    # OpenRouter expects just the model ID (e.g., "anthropic/claude-3.5-sonnet")
    if provider == "openrouter" and model and ":" in model:
        # Already parsed above, but handle case where model still has provider
        pass

    # Get provider config
    provider_config = PROVIDER_REGISTRY.get(provider) if provider else None

    # Determine API mode
    api_mode = provider_config.api_mode if provider_config else "chat_completions"

    # Resolve base_url
    resolved_base_url = base_url
    if not resolved_base_url and provider_config:
        resolved_base_url = provider_config.base_url

    # Resolve API key (priority: explicit > env > config)
    resolved_api_key = api_key
    if not resolved_api_key and provider_config:
        for env_var in provider_config.env_vars:
            resolved_api_key = os.environ.get(env_var)
            if resolved_api_key:
                break

    # Resolve model
    resolved_model = model
    if not resolved_model and provider_config:
        # Get default model from catalog
        models = _PROVIDER_MODELS.get(provider, {})
        if models:
            resolved_model = next(iter(models))

    # If still no model, try to infer from provider
    if not resolved_model and provider:
        resolved_model = _infer_default_model(provider)

    # For OpenRouter, ensure model doesn't have provider prefix
    if provider == "openrouter" and resolved_model and resolved_model.startswith("openrouter:"):
        resolved_model = resolved_model[len("openrouter:"):]

    # Determine source
    source = "cli" if (provider or model or base_url or api_key) else "default"

    return RuntimeProvider(
        provider=provider or "custom",
        model=resolved_model or "unknown",
        base_url=resolved_base_url,
        api_key=resolved_api_key,
        api_mode=api_mode,
        source=source,
    )


def _infer_default_model(provider: str) -> str:
    """Infer default model for provider."""
    defaults = {
        "openrouter": "anthropic/claude-3.5-sonnet",
        "openai": "gpt-4o",
        "anthropic": "claude-3-5-sonnet-20241022",
        "nvidia": "nvidia/nemotron-3-ultra",
        "ollama": "llama3.1",
        "lmstudio": "local-model",
    }
    return defaults.get(provider, "unknown")


def resolve_provider_client(runtime: RuntimeProvider) -> Any:
    """Create API client for the resolved provider."""
    if runtime.api_mode in ("chat_completions", "codex_responses"):
        from openai import OpenAI
        return OpenAI(
            api_key=runtime.api_key,
            base_url=runtime.base_url,
        )
    elif runtime.api_mode == "anthropic_messages":
        import anthropic
        return anthropic.Anthropic(
            api_key=runtime.api_key,
            base_url=runtime.base_url,
        )
    else:
        raise ValueError(f"Unknown api_mode: {runtime.api_mode}")