"""
Enaya Agent - CLI Entry Point
Mirrors Hermes Agent's hermes_cli/main.py structure.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

import click
from rich.console import Console

from enaya.run_agent import create_agent, AIAgent, AgentConfig
from enaya.cli.config import load_config, save_config, CONFIG_DEFAULTS
from enaya.cli.runtime_provider import resolve_runtime_provider


console = Console()


# =============================================================================
# Main CLI Group
# =============================================================================

@click.group()
@click.version_option(version="0.1.0", prog_name="enaya")
@click.option("-p", "--profile", default="default", help="Profile name")
@click.pass_context
def cli(ctx: click.Context, profile: str):
    """Enaya Agent — Task-delegation AI agent with multi-agent orchestration."""
    ctx.ensure_object(dict)
    ctx.obj["profile"] = profile
    # Set ENAYA_HOME for this profile
    enaya_home = Path.home() / ".enaya"
    if profile != "default":
        enaya_home = enaya_home / "profiles" / profile
    os.environ["ENAYA_HOME"] = str(enaya_home)
    enaya_home.mkdir(parents=True, exist_ok=True)


# =============================================================================
# Chat Command
# =============================================================================

@cli.command()
@click.argument("query", required=False)
@click.option("-q", "--query", "query_opt", help="Query to run (alternative to positional)")
@click.option("-m", "--model", help="Model to use (e.g., openrouter:anthropic/claude-sonnet-4)")
@click.option("--provider", help="Provider to use")
@click.option("--resume/--no-resume", default=False, help="Resume last session")
@click.option("--session-id", help="Specific session ID to resume")
@click.option("--prefill", help="Prefill assistant response")
@click.pass_context
def chat(
    ctx: click.Context,
    query: str,
    query_opt: str,
    model: str,
    provider: str,
    resume: bool,
    session_id: str,
    prefill: str,
):
    """Start a chat session or run a single query."""
    user_query = query or query_opt
    if not user_query and not resume:
        console.print("[red]Error:[/red] Provide a query or use --resume")
        sys.exit(1)

    profile = ctx.obj["profile"]
    config = load_config(profile)

    # Override with CLI args
    if model:
        config["model"] = model
    if provider:
        config["provider"] = provider

    agent_config = AgentConfig(
        model=config.get("model", "openrouter:anthropic/claude-sonnet-4"),
        provider=config.get("provider"),
        max_turns=config.get("max_turns", 500),
        temperature=config.get("temperature", 0.7),
        toolsets=config.get("toolsets", ["core", "research", "planning", "delegation"]),
        disabled_tools=config.get("disabled_tools", []),
        fallback_providers=config.get("fallback_providers", []),
        profile=profile,
        platform="cli",
    )

    agent = AIAgent(agent_config)

    if resume:
        # Resume last session
        if session_id:
            agent.session_id = session_id
        result = agent.run_conversation("", resume=True)
    elif user_query:
        result = agent.run_conversation(user_query, prefill=prefill)
    else:
        # Interactive mode
        result = _run_interactive(agent)

    console.print(result)


def _run_interactive(agent: AIAgent) -> str:
    """Run interactive chat loop."""
    console.print("[green]Enaya Agent[/green] — Interactive mode (Ctrl+C to exit)")
    console.print(f"Model: {agent.model} | Provider: {agent.provider} | Session: {agent.session_id[:8]}")

    while True:
        try:
            user_input = console.input("\n[bold cyan]You:[/bold cyan] ")
            if not user_input.strip():
                continue
            if user_input.strip().lower() in ("exit", "quit", "/exit", "/quit"):
                break

            result = agent.run_conversation(user_input)
            console.print(f"\n[bold green]Enaya:[/bold green] {result}")

        except KeyboardInterrupt:
            console.print("\n[yellow]Interrupted[/yellow]")
            break
        except EOFError:
            break

    return "Session ended."


# =============================================================================
# Model Command
# =============================================================================

@cli.command()
@click.argument("model_spec", required=False)
@click.option("--list", "list_models", is_flag=True, help="List available models")
@click.option("--provider", help="Filter by provider")
@click.pass_context
def model(ctx: click.Context, model_spec: str, list_models: bool, provider: str):
    """Switch or list models."""
    profile = ctx.obj["profile"]
    config = load_config(profile)

    if list_models:
        _list_models(provider)
        return

    if not model_spec:
        console.print(f"Current model: {config.get('model', 'not set')}")
        return

    # Parse provider:model format
    if ":" in model_spec:
        provider, model = model_spec.split(":", 1)
    else:
        model = model_spec

    # Resolve and validate
    try:
        runtime = resolve_runtime_provider(provider=provider, model=model)
        config["model"] = f"{runtime.provider}:{runtime.model}" if runtime.provider != "custom" else runtime.model
        config["provider"] = runtime.provider
        save_config(profile, config)
        console.print(f"[green]Model set to:[/green] {config['model']}")
    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
        sys.exit(1)


def _list_models(provider: str = None):
    """List available models."""
    # This would query provider catalogs
    console.print("[yellow]Model listing not yet implemented[/yellow]")


# =============================================================================
# Setup Command
# =============================================================================

@cli.command()
@click.pass_context
def setup(ctx: click.Context):
    """Interactive setup wizard."""
    profile = ctx.obj["profile"]
    config = load_config(profile)

    console.print("[bold]Enaya Agent Setup[/bold]")
    console.print(f"Profile: {profile}")

    # Model selection
    model = click.prompt("Model", default=config.get("model", "openrouter:anthropic/claude-sonnet-4"))
    config["model"] = model

    # Provider
    provider = click.prompt("Provider (optional)", default=config.get("provider", ""), show_default=False)
    if provider:
        config["provider"] = provider

    # API Keys (stored in .env)
    _prompt_api_keys(config)

    save_config(profile, config)
    console.print("[green]Setup complete![/green]")


def _prompt_api_keys(config: dict):
    """Prompt for API keys and write to .env."""
    enaya_home = Path(os.environ.get("ENAYA_HOME", Path.home() / ".enaya"))
    env_file = enaya_home / ".env"

    keys = {
        "OPENROUTER_API_KEY": "OpenRouter",
        "ANTHROPIC_TOKEN": "Anthropic (Claude)",
        "OPENAI_API_KEY": "OpenAI",
        "NVIDIA_API_KEY": "NVIDIA NIM",
    }

    existing = {}
    if env_file.exists():
        for line in env_file.read_text().splitlines():
            if "=" in line and not line.startswith("#"):
                k, v = line.split("=", 1)
                existing[k.strip()] = v.strip()

    new_keys = {}
    for key, label in keys.items():
        current = existing.get(key, "")
        masked = "*" * 8 + current[-4:] if current else ""
        value = click.prompt(f"{label} API key", default=masked, show_default=False, hide_input=True)
        if value and value != masked:
            new_keys[key] = value

    # Write .env
    lines = []
    for k, v in {**existing, **new_keys}.items():
        lines.append(f"{k}={v}")
    env_file.write_text("\n".join(lines) + "\n")


# =============================================================================
# Delegate Command
# =============================================================================

@cli.command()
@click.argument("task")
@click.option("--model", help="Model for subagent")
@click.option("--provider", help="Provider for subagent")
@click.option("--max-iterations", default=50, help="Max iterations for subagent")
@click.pass_context
def delegate(ctx: click.Context, task: str, model: str, provider: str, max_iterations: int):
    """Delegate a task to a subagent."""
    profile = ctx.obj["profile"]
    config = load_config(profile)

    agent_config = AgentConfig(
        model=model or config.get("model", "openrouter:anthropic/claude-sonnet-4"),
        provider=provider or config.get("provider"),
        max_turns=max_iterations,
        profile=profile,
        platform="cli",
    )

    agent = AIAgent(agent_config)
    result = agent.run_conversation(f"[DELEGATED TASK]\n{task}")
    console.print(result)


# =============================================================================
# Research Command
# =============================================================================

@cli.command()
@click.argument("query")
@click.option("--depth", type=click.Choice(["quick", "deep", "comprehensive"]), default="deep")
@click.option("--sources", type=click.Choice(["web", "academic", "all"]), default="all")
@click.pass_context
def research(ctx: click.Context, query: str, depth: str, sources: str):
    """Run a research query."""
    profile = ctx.obj["profile"]
    config = load_config(profile)

    agent_config = AgentConfig(
        model=config.get("model", "openrouter:anthropic/claude-sonnet-4"),
        toolsets=["core", "research"],
        profile=profile,
        platform="cli",
    )

    agent = AIAgent(agent_config)
    prompt = f"Research query: {query}\nDepth: {depth}\nSources: {sources}\n\nConduct thorough research and provide synthesized findings with citations."
    result = agent.run_conversation(prompt)
    console.print(result)


# =============================================================================
# Plan Command
# =============================================================================

@cli.command()
@click.argument("goal")
@click.option("--complexity", type=click.Choice(["simple", "moderate", "complex"]), default="moderate")
@click.pass_context
def plan(ctx: click.Context, goal: str, complexity: str):
    """Create a structured plan for a goal."""
    profile = ctx.obj["profile"]
    config = load_config(profile)

    agent_config = AgentConfig(
        model=config.get("model", "openrouter:anthropic/claude-sonnet-4"),
        toolsets=["core", "planning"],
        profile=profile,
        platform="cli",
    )

    agent = AIAgent(agent_config)
    prompt = f"Create a structured plan for: {goal}\nComplexity: {complexity}\n\nDecompose into tasks, define milestones, identify risks, and provide execution order."
    result = agent.run_conversation(prompt)
    console.print(result)


# =============================================================================
# Gateway Commands
# =============================================================================

@cli.group()
def gateway():
    """Messaging gateway commands."""
    pass


@gateway.command("start")
@click.option("--daemon/--no-daemon", default=False)
@click.pass_context
def gateway_start(ctx: click.Context, daemon: bool):
    """Start the messaging gateway."""
    console.print("[yellow]Gateway not yet implemented[/yellow]")


@gateway.command("stop")
@click.option("--all", "stop_all", is_flag=True)
@click.pass_context
def gateway_stop(ctx: click.Context, stop_all: bool):
    """Stop the messaging gateway."""
    console.print("[yellow]Gateway not yet implemented[/yellow]")


# =============================================================================
# TUI Command
# =============================================================================

@cli.command()
@click.pass_context
def tui(ctx: click.Context):
    """Launch the Textual TUI interface."""
    try:
        from enaya.tui.main import run_tui
        run_tui()
    except ImportError:
        console.print("[red]Error:[/red] TUI dependencies not installed. Run: pip install enaya-agent[tui]")
        sys.exit(1)


# =============================================================================
# Dashboard Command
# =============================================================================

@cli.command()
@click.option("--host", default="0.0.0.0", help="Host to bind")
@click.option("--port", default=8080, help="Port to bind")
@click.pass_context
def dashboard(ctx: click.Context, host: str, port: int):
    """Launch the web dashboard."""
    try:
        import uvicorn
        from enaya.dashboard.server import app
        console.print(f"[green]Starting dashboard on http://{host}:{port}[/green]")
        uvicorn.run(app, host=host, port=port)
    except ImportError:
        console.print("[red]Error:[/red] Dashboard dependencies not installed. Run: pip install enaya-agent[dashboard]")
        sys.exit(1)


# =============================================================================
# API Server Command
# =============================================================================

@cli.command()
@click.option("--host", default="0.0.0.0", help="Host to bind")
@click.option("--port", default=8000, help="Port to bind")
@click.pass_context
def api_server(ctx: click.Context, host: str, port: int):
    """Launch the OpenAI-compatible API server."""
    try:
        from enaya.api_server.main import run_api_server
        console.print(f"[green]Starting API server on http://{host}:{port}[/green]")
        run_api_server(host=host, port=port)
    except ImportError:
        console.print("[red]Error:[/red] API server dependencies not installed. Run: pip install enaya-agent[api]")
        sys.exit(1)


# =============================================================================
# ACP Command
# =============================================================================

@cli.command()
@click.option("--check", is_flag=True, help="Verify ACP dependencies")
@click.option("--setup", is_flag=True, help="Interactive ACP setup")
@click.pass_context
def acp(ctx: click.Context, check: bool, setup: bool):
    """ACP server for IDE integration (VS Code, Zed, JetBrains)."""
    if check:
        console.print("[yellow]Checking ACP dependencies...[/yellow]")
        try:
            import pydantic
            console.print("[green]ACP dependencies OK[/green]")
        except ImportError:
            console.print("[red]Missing dependencies. Run: pip install enaya-agent[acp][/red]")
            sys.exit(1)
        return
    
    if setup:
        console.print("[yellow]ACP setup not yet implemented[/yellow]")
        return
    
    try:
        from enaya.acp_adapter.server import run_acp_server
        console.print("[green]Starting ACP server on stdio...[/green]")
        run_acp_server()
    except ImportError:
        console.print("[red]Error:[/red] ACP dependencies not installed. Run: pip install enaya-agent[acp]")
        sys.exit(1)


# =============================================================================
# Skills Command
# =============================================================================

@cli.command()
@click.option("--list", "list_skills", is_flag=True, help="List available skills")
@click.option("--enable", help="Enable a skill")
@click.option("--disable", help="Disable a skill")
@click.pass_context
def skills(ctx: click.Context, list_skills: bool, enable: str, disable: str):
    """Manage skills."""
    console.print("[yellow]Skills management not yet implemented[/yellow]")


# =============================================================================
# Plugins Command
# =============================================================================

@cli.group()
def plugins():
    """Plugin management."""
    pass


@plugins.command("doctor")
@click.option("--path", help="Plugin path to validate")
@click.pass_context
def plugins_doctor(ctx: click.Context, path: str):
    """Validate a plugin."""
    console.print("[yellow]Plugin doctor not yet implemented[/yellow]")


# =============================================================================
# Cron Command
# =============================================================================

@cli.group()
def cron():
    """Cron job management."""
    pass


@cron.command("add")
@click.argument("name")
@click.argument("schedule")
@click.argument("prompt")
@click.pass_context
def cron_add(ctx: click.Context, name: str, schedule: str, prompt: str):
    """Add a cron job."""
    console.print("[yellow]Cron not yet implemented[/yellow]")


# =============================================================================
# Config Command
# =============================================================================

@cli.command()
@click.argument("key", required=False)
@click.argument("value", required=False)
@click.option("--list", "list_config", is_flag=True)
@click.pass_context
def config(ctx: click.Context, key: str, value: str, list_config: bool):
    """Get/set configuration."""
    profile = ctx.obj["profile"]
    config_data = load_config(profile)

    if list_config:
        for k, v in config_data.items():
            console.print(f"  {k}: {v}")
        return

    if key and value:
        config_data[key] = value
        save_config(profile, config_data)
        console.print(f"[green]Set {key} = {value}[/green]")
    elif key:
        console.print(f"{key}: {config_data.get(key, 'not set')}")
    else:
        console.print("[red]Specify key and value, or --list[/red]")


# =============================================================================
# Entry Point
# =============================================================================

def main():
    """Main entry point."""
    cli(obj={})


if __name__ == "__main__":
    main()