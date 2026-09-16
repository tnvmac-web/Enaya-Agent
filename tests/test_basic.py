"""
Enaya Agent - Basic Tests
"""

import pytest

from enaya.cli.auth import PROVIDER_REGISTRY, resolve_provider
from enaya.cli.config import CONFIG_DEFAULTS, load_config
from enaya.cli.models import _PROVIDER_MODELS, resolve_model_alias
from enaya.model_tools import build_function_schema
from enaya.tools.registry import registry


class TestToolRegistry:
    def test_registry_exists(self):
        assert registry is not None

    def test_register_and_get(self):
        schema = {"type": "function", "function": {"name": "test_tool", "description": "Test", "parameters": {"type": "object", "properties": {}}}}
        def handler(args, **kwargs):
            return '{"result": "ok"}'
        def check_fn():
            return True

        registry.register("test_tool", "test", schema, handler, check_fn)
        tool = registry.get("test_tool")
        assert tool is not None
        assert tool.name == "test_tool"

    def test_get_schemas(self):
        schemas = registry.get_schemas(["core"], [])
        assert isinstance(schemas, list)


class TestModelTools:
    def test_build_function_schema(self):
        schema = build_function_schema(
            "test",
            "Test description",
            {"arg": {"type": "string", "description": "Test arg"}},
            ["arg"]
        )
        assert schema["type"] == "function"
        assert schema["function"]["name"] == "test"
        assert "arg" in schema["function"]["parameters"]["properties"]


class TestConfig:
    def test_defaults_exist(self):
        assert "model" in CONFIG_DEFAULTS
        assert "provider" in CONFIG_DEFAULTS
        assert "max_turns" in CONFIG_DEFAULTS

    def test_load_config(self):
        # Should not crash even without config file
        config = load_config("test_profile_nonexistent")
        assert config["model"] == CONFIG_DEFAULTS["model"]


class TestAuth:
    def test_provider_registry(self):
        assert "openrouter" in PROVIDER_REGISTRY
        assert "openai" in PROVIDER_REGISTRY
        assert "anthropic" in PROVIDER_REGISTRY

    def test_resolve_provider(self):
        config = resolve_provider("openrouter")
        assert config is not None
        assert config.base_url == "https://openrouter.ai/api/v1"


class TestModels:
    def test_model_catalog(self):
        assert "openrouter" in _PROVIDER_MODELS
        models = _PROVIDER_MODELS["openrouter"]
        assert "anthropic/claude-3.5-sonnet" in models

    def test_resolve_model_alias(self):
        provider, model = resolve_model_alias("sonnet")
        assert provider == "openrouter"
        assert model == "anthropic/claude-3.5-sonnet"


class TestRuntimeProvider:
    def test_resolve_runtime_provider(self):
        from enaya.cli.runtime_provider import resolve_runtime_provider

        runtime = resolve_runtime_provider(provider="openrouter", model="anthropic/claude-3.5-sonnet")
        assert runtime.provider == "openrouter"
        assert runtime.model == "anthropic/claude-3.5-sonnet"
        assert runtime.api_mode == "chat_completions"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
