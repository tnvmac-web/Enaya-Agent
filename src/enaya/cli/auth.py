"""
Enaya Agent - Provider Auth & Registry
Provider registry, credential resolution.
Mirrors Hermes Agent's hermes_cli/auth.py exactly.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class OAuthConfig:
    """OAuth configuration for providers that use OAuth."""
    client_id: str
    client_secret: str
    auth_url: str
    token_url: str
    scopes: list[str] = field(default_factory=list)
    refresh_url: str | None = None


@dataclass
class ProviderConfig:
    """Provider configuration metadata."""
    env_vars: list[str] = field(default_factory=list)  # Priority order
    base_url: str | None = None
    api_mode: str = "chat_completions"  # chat_completions, codex_responses, anthropic_messages
    oauth_config: OAuthConfig | None = None
    fallback_models: list[str] = field(default_factory=list)
    supports_streaming: bool = True
    supports_tools: bool = True
    supports_vision: bool = False
    custom_headers: dict[str, str] = field(default_factory=dict)


# =============================================================================
# Provider Registry
# =============================================================================

PROVIDER_REGISTRY: dict[str, ProviderConfig] = {
    # OpenRouter - OpenAI compatible
    "openrouter": ProviderConfig(
        env_vars=["OPENROUTER_API_KEY"],
        base_url="https://openrouter.ai/api/v1",
        api_mode="chat_completions",
        fallback_models=["anthropic/claude-3.5-sonnet", "google/gemini-1.5-pro"],
    ),

    # OpenAI
    "openai": ProviderConfig(
        env_vars=["OPENAI_API_KEY"],
        base_url="https://api.openai.com/v1",
        api_mode="chat_completions",
        fallback_models=["gpt-4o", "gpt-4o-mini"],
    ),

    # Anthropic (native)
    "anthropic": ProviderConfig(
        env_vars=["ANTHROPIC_TOKEN", "CLAUDE_CODE_OAUTH_TOKEN"],
        base_url="https://api.anthropic.com",
        api_mode="anthropic_messages",
        fallback_models=["claude-3-5-sonnet-20241022", "claude-3-5-haiku-20241022"],
    ),

    # NVIDIA NIM
    "nvidia": ProviderConfig(
        env_vars=["NVIDIA_API_KEY"],
        base_url="https://integrate.api.nvidia.com/v1",
        api_mode="chat_completions",
        fallback_models=["nvidia/nemotron-3-ultra", "nvidia/llama-3.1-nemotron-70b-instruct"],
    ),

    # Google/Gemini
    "google": ProviderConfig(
        env_vars=["GOOGLE_API_KEY", "GEMINI_API_KEY"],
        base_url="https://generativelanguage.googleapis.com/v1beta",
        api_mode="chat_completions",
        fallback_models=["gemini-1.5-pro", "gemini-1.5-flash"],
    ),

    # Ollama (local)
    "ollama": ProviderConfig(
        env_vars=["OLLAMA_HOST"],
        base_url="http://localhost:11434/v1",
        api_mode="chat_completions",
        fallback_models=["llama3.1", "llama3.2", "mistral"],
    ),

    # LM Studio (local)
    "lmstudio": ProviderConfig(
        env_vars=["LMSTUDIO_HOST"],
        base_url="http://localhost:1234/v1",
        api_mode="chat_completions",
        fallback_models=["local-model"],
    ),

    # Custom OpenAI-compatible
    "custom": ProviderConfig(
        env_vars=["CUSTOM_API_KEY"],
        base_url=None,  # Must be provided
        api_mode="chat_completions",
    ),
}


# =============================================================================
# Provider Aliases
# =============================================================================

_PROVIDER_ALIASES: dict[str, str] = {
    "or": "openrouter",
    "oa": "openai",
    "ant": "anthropic",
    "claude": "anthropic",
    "nv": "nvidia",
    "nim": "nvidia",
    "gg": "google",
    "gemini": "google",
    "ol": "ollama",
    "lms": "lmstudio",
}


def resolve_provider(provider: str) -> ProviderConfig:
    """Resolve provider alias to canonical name and return config."""
    canonical = _PROVIDER_ALIASES.get(provider, provider)
    return PROVIDER_REGISTRY.get(canonical, ProviderConfig())


def register_provider(name: str, config: ProviderConfig) -> None:
    """Register a new provider (for plugins)."""
    PROVIDER_REGISTRY[name] = config


def get_provider_profile(provider: str) -> ProviderConfig:
    """Get provider profile by canonical name."""
    return PROVIDER_REGISTRY.get(provider, ProviderConfig())


def list_providers() -> list[str]:
    """List all registered providers."""
    return list(PROVIDER_REGISTRY.keys())
