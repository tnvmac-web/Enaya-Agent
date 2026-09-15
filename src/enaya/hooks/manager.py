#!/usr/bin/env python3
"""
Enaya Agent - Hooks System
Lifecycle hooks for gateway events, agent events, and custom triggers.
"""

from __future__ import annotations

import asyncio
import os
import subprocess
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Optional

import yaml


# =============================================================================
# Hook Types and Events
# =============================================================================

class HookEvent(Enum):
    """Gateway and agent lifecycle events."""
    # Gateway events
    GATEWAY_STARTUP = "gateway:startup"
    GATEWAY_SHUTDOWN = "gateway:shutdown"
    
    # Session events
    SESSION_START = "session:start"
    SESSION_END = "session:end"
    SESSION_RESET = "session:reset"
    
    # Agent events
    AGENT_START = "agent:start"
    AGENT_STEP = "agent:step"
    AGENT_END = "agent:end"
    AGENT_ERROR = "agent:error"
    
    # Command events
    COMMAND_EXECUTED = "command:executed"
    
    # Cron events
    CRON_JOB_START = "cron:job:start"
    CRON_JOB_END = "cron:job:end"
    CRON_JOB_ERROR = "cron:job:error"
    
    # Delegation events
    DELEGATION_START = "delegation:start"
    DELEGATION_END = "delegation:end"
    
    # Custom events
    CUSTOM = "custom"


@dataclass
class HookContext:
    """Context passed to hook handlers."""
    event: HookEvent
    timestamp: float = field(default_factory=time.time)
    profile: str = "default"
    session_id: Optional[str] = None
    platform: Optional[str] = None
    user_id: Optional[str] = None
    data: dict = field(default_factory=dict)
    
    def to_dict(self) -> dict:
        return {
            "event": self.event.value,
            "timestamp": self.timestamp,
            "profile": self.profile,
            "session_id": self.session_id,
            "platform": self.platform,
            "user_id": self.user_id,
            "data": self.data,
        }


@dataclass
class HookDefinition:
    """Hook definition from manifest."""
    name: str
    event: HookEvent
    handler: str  # function name or command
    type: str = "function"  # function, shell, python, webhook
    priority: int = 0
    async_mode: bool = False
    timeout: float = 30.0
    conditions: dict = field(default_factory=dict)  # event filters
    config: dict = field(default_factory=dict)


# =============================================================================
# Hook Handlers
# =============================================================================

class HookHandler(ABC):
    """Abstract hook handler."""
    
    @abstractmethod
    async def execute(self, context: HookContext) -> Any:
        pass


class FunctionHookHandler(HookHandler):
    """Handler for Python function hooks."""
    
    def __init__(self, func: Callable):
        self.func = func
    
    async def execute(self, context: HookContext) -> Any:
        if asyncio.iscoroutinefunction(self.func):
            return await self.func(context)
        else:
            return self.func(context)


class ShellHookHandler(HookHandler):
    """Handler for shell command hooks."""
    
    def __init__(self, command: str, timeout: float = 30.0):
        self.command = command
        self.timeout = timeout
    
    async def execute(self, context: HookContext) -> Any:
        # Prepare environment
        env = os.environ.copy()
        env.update({
            "ENAYA_EVENT": context.event.value,
            "ENAYA_PROFILE": context.profile,
            "ENAYA_SESSION_ID": context.session_id or "",
            "ENAYA_PLATFORM": context.platform or "",
            "ENAYA_USER_ID": context.user_id or "",
            "ENAYA_TIMESTAMP": str(context.timestamp),
        })
        
        # Add data as JSON
        env["ENAYA_DATA"] = json.dumps(context.data)
        
        try:
            proc = await asyncio.create_subprocess_shell(
                self.command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env=env,
            )
            
            stdout, stderr = await asyncio.wait_for(
                proc.communicate(),
                timeout=self.timeout,
            )
            
            return {
                "returncode": proc.returncode,
                "stdout": stdout.decode() if stdout else "",
                "stderr": stderr.decode() if stderr else "",
            }
        except asyncio.TimeoutError:
            return {"error": f"Hook timeout after {self.timeout}s"}


class PythonHookHandler(HookHandler):
    """Handler for inline Python code hooks."""
    
    def __init__(self, code: str, timeout: float = 30.0):
        self.code = code
        self.timeout = timeout
    
    async def execute(self, context: HookContext) -> Any:
        # Create a safe execution environment
        local_vars = {
            "context": context,
            "json": json,
            "time": time,
            "os": os,
            "Path": Path,
        }
        
        try:
            # Execute with timeout
            result = await asyncio.wait_for(
                asyncio.get_event_loop().run_in_executor(
                    None,
                    lambda: exec(self.code, {"__builtins__": {}}, local_vars)
                ),
                timeout=self.timeout,
            )
            return local_vars.get("result")
        except asyncio.TimeoutError:
            return {"error": f"Python hook timeout after {self.timeout}s"}
        except Exception as e:
            return {"error": str(e)}


class WebhookHookHandler(HookHandler):
    """Handler for webhook HTTP calls."""
    
    def __init__(self, url: str, method: str = "POST", headers: dict = None, timeout: float = 30.0):
        self.url = url
        self.method = method
        self.headers = headers or {"Content-Type": "application/json"}
        self.timeout = timeout
    
    async def execute(self, context: HookContext) -> Any:
        import httpx
        
        payload = context.to_dict()
        
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                response = await client.request(
                    self.method,
                    self.url,
                    json=payload,
                    headers=self.headers,
                )
                response.raise_for_status()
                return response.json()
            except Exception as e:
                return {"error": str(e)}


# =============================================================================
# Hook Manager
# =============================================================================

class HookManager:
    """Manages hook registration, execution, and lifecycle."""
    
    def __init__(self, profile: str = "default"):
        self.profile = profile
        self.hooks_dir = Path(os.environ.get("ENAYA_HOME", Path.home() / ".enaya")) / "hooks"
        self.hooks_dir.mkdir(parents=True, exist_ok=True)
        
        self._handlers: dict[HookEvent, list[tuple[HookHandler, HookDefinition]]] = {}
        self._builtin_hooks: dict[str, HookHandler] = {}
        
        self._register_builtin_hooks()
    
    def _register_builtin_hooks(self) -> None:
        """Register built-in hook handlers."""
        # Session logging
        self.register_handler(
            HookEvent.SESSION_START,
            FunctionHookHandler(self._log_session_start),
            HookDefinition(name="log_session_start", event=HookEvent.SESSION_START, handler="log_session_start"),
        )
        
        self.register_handler(
            HookEvent.SESSION_END,
            FunctionHookHandler(self._log_session_end),
            HookDefinition(name="log_session_end", event=HookEvent.SESSION_END, handler="log_session_end"),
        )
        
        # Agent step logging
        self.register_handler(
            HookEvent.AGENT_STEP,
            FunctionHookHandler(self._log_agent_step),
            HookDefinition(name="log_agent_step", event=HookEvent.AGENT_STEP, handler="log_agent_step"),
        )
        
        # Error handling
        self.register_handler(
            HookEvent.AGENT_ERROR,
            FunctionHookHandler(self._handle_agent_error),
            HookDefinition(name="handle_agent_error", event=HookEvent.AGENT_ERROR, handler="handle_agent_error"),
        )
    
    def _matches_conditions(self, definition: HookDefinition, context: HookContext) -> bool:
        """Check if hook conditions match context."""
        for key, value in definition.conditions.items():
            if key == "platform" and context.platform != value:
                return False
            if key == "user_id" and context.user_id != value:
                return False
            if key == "event_contains" and value not in context.data.get("text", ""):
                return False
        return True
    
    def register_handler(
        self,
        event: HookEvent,
        handler: HookHandler,
        definition: HookDefinition,
    ) -> None:
        """Register a hook handler for an event."""
        if event not in self._handlers:
            self._handlers[event] = []
        
        self._handlers[event].append((handler, definition))
        
        # Sort by priority (highest first)
        self._handlers[event].sort(key=lambda x: x[1].priority, reverse=True)
    
    def unregister_handler(self, event: HookEvent, handler_name: str) -> bool:
        if event in self._handlers:
            self._handlers[event] = [
                (h, d) for h, d in self._handlers[event]
                if d.name != handler_name
            ]
            return True
        return False
    
    async def fire(self, event: HookEvent, context: HookContext) -> list[Any]:
        """Fire all handlers for an event."""
        results = []
        
        handlers = self._handlers.get(event, [])
        
        for handler, definition in handlers:
            # Check conditions
            if not self._matches_conditions(definition, context):
                continue
            
            try:
                if definition.async_mode:
                    # Fire and forget
                    asyncio.create_task(self._execute_with_timeout(handler, context, definition))
                    results.append({"handler": definition.name, "status": "async_queued"})
                else:
                    result = await self._execute_with_timeout(handler, context, definition)
                    results.append({"handler": definition.name, "result": result})
            except Exception as e:
                results.append({"handler": definition.name, "error": str(e)})
        
        return results
    
    async def _execute_with_timeout(
        self,
        handler: HookHandler,
        context: HookContext,
        definition: HookDefinition,
    ) -> Any:
        try:
            return await asyncio.wait_for(
                handler.execute(context),
                timeout=definition.timeout,
            )
        except asyncio.TimeoutError:
            return {"error": f"Hook timeout after {definition.timeout}s"}
        except Exception as e:
            return {"error": str(e)}
    
    # Built-in hook implementations
    def _log_session_start(self, context: HookContext) -> dict:
        return {"logged": True, "session_id": context.session_id}
    
    def _log_session_end(self, context: HookContext) -> dict:
        return {"logged": True, "session_id": context.session_id}
    
    def _log_agent_step(self, context: HookContext) -> dict:
        return {"logged": True, "step": context.data.get("step")}
    
    def _handle_agent_error(self, context: HookContext) -> dict:
        error = context.data.get("error", "Unknown error")
        return {"handled": True, "error": error}
    
    def load_hooks_from_dir(self, hooks_dir: Path = None) -> int:
        """Load hook definitions from directory."""
        hooks_dir = hooks_dir or self.hooks_dir
        loaded = 0
        
        for hook_file in hooks_dir.glob("*.yaml"):
            try:
                with open(hook_file) as f:
                    data = yaml.safe_load(f)
                
                for hook_data in data.get("hooks", []):
                    definition = HookDefinition(**hook_data)
                    
                    # Create handler based on type
                    if definition.type == "function":
                        # Would need to import the function
                        handler = FunctionHookHandler(lambda ctx: {"status": "function_hook"})
                    elif definition.type == "shell":
                        handler = ShellHookHandler(definition.handler, definition.timeout)
                    elif definition.type == "python":
                        handler = PythonHookHandler(definition.handler, definition.timeout)
                    elif definition.type == "webhook":
                        handler = WebhookHookHandler(
                            definition.config.get("url", ""),
                            definition.config.get("method", "POST"),
                            definition.config.get("headers"),
                            definition.timeout,
                        )
                    else:
                        continue
                    
                    self.register_handler(definition.event, handler, definition)
                    loaded += 1
                    
            except Exception as e:
                print(f"Failed to load hooks from {hook_file}: {e}")
        
        return loaded
    
    def create_hook_file(self, name: str, event: HookEvent, handler_type: str = "shell", handler: str = "") -> Path:
        """Create a new hook definition file."""
        hooks_dir = self.hooks_dir / name
        hooks_dir.mkdir(parents=True, exist_ok=True)
        
        hook_data = {
            "hooks": [{
                "name": name,
                "event": event.value,
                "handler": handler,
                "type": handler_type,
                "priority": 0,
                "async_mode": False,
                "timeout": 30.0,
                "conditions": {},
                "config": {},
            }]
        }
        
        hook_file = hooks_dir / "hooks.yaml"
        with open(hook_file, "w") as f:
            yaml.dump(hook_data, f, default_flow_style=False)
        
        # Create example handler
        if handler_type == "shell":
            script_file = hooks_dir / "hook.sh"
            script_file.write_text(f'''#!/bin/bash
# Hook: {name}
# Event: {event.value}

echo "Hook triggered: {event.value}"
echo "Profile: $ENAYA_PROFILE"
echo "Session: $ENAYA_SESSION_ID"
echo "Platform: $ENAYA_PLATFORM"
echo "Data: $ENAYA_DATA"
''')
            script_file.chmod(0o755)
        elif handler_type == "python":
            script_file = hooks_dir / "hook.py"
            script_file.write_text(f'''#!/usr/bin/env python3
"""
Hook: {name}
Event: {event.value}
"""

def hook(context):
    """Hook handler function."""
    print(f"Hook triggered: {event.value}")
    print(f"Profile: {{context.profile}}")
    print(f"Session: {{context.session_id}}")
    print(f"Data: {{context.data}}")
    return {{"status": "ok"}}

result = hook(context)
''')
        
        return hooks_dir


# =============================================================================
# Webhook Server (for receiving external webhooks)
# =============================================================================

class WebhookServer:
    """HTTP server for receiving external webhooks."""
    
    def __init__(self, hook_manager: HookManager, host: str = "0.0.0.0", port: int = 8080):
        self.hook_manager = hook_manager
        self.host = host
        self.port = port
        self._app = None
        self._server = None
    
    def create_app(self):
        from fastapi import FastAPI, Request, HTTPException
        from pydantic import BaseModel
        
        app = FastAPI(title="Enaya Webhook Server")
        
        class WebhookPayload(BaseModel):
            event: str
            data: dict = {}
            source: str = "webhook"
        
        @app.post("/webhook/{event_name}")
        async def receive_webhook(event_name: str, payload: WebhookPayload, request: Request):
            try:
                event = HookEvent(event_name)
            except ValueError:
                # Custom event
                event = HookEvent.CUSTOM
                payload.data["_custom_event"] = event_name
            
            context = HookContext(
                event=event,
                profile=self.hook_manager.profile,
                data=payload.data,
            )
            
            results = await self.hook_manager.fire(event, context)
            
            return {"status": "received", "results": results}
        
        @app.get("/webhook/health")
        async def health():
            return {"status": "ok", "hooks": len(self.hook_manager._handlers)}
        
        self._app = app
        return app
    
    async def start(self):
        import uvicorn
        if not self._app:
            self.create_app()
        
        config = uvicorn.Config(self._app, host=self.host, port=self.port)
        self._server = uvicorn.Server(config)
        await self._server.serve()
    
    async def stop(self):
        if self._server:
            self._server.should_exit = True


# =============================================================================
# Hook CLI Commands
# =============================================================================

_hook_manager: Optional[HookManager] = None


def get_hook_manager(profile: str = "default") -> HookManager:
    global _hook_manager
    if _hook_manager is None:
        _hook_manager = HookManager(profile=profile)
    return _hook_manager


def hook_list() -> list[dict]:
    """List registered hooks."""
    manager = get_hook_manager()
    result = []
    for event, handlers in manager._handlers.items():
        for handler, definition in handlers:
            result.append({
                "event": event.value,
                "name": definition.name,
                "type": definition.type,
                "priority": definition.priority,
                "async": definition.async_mode,
            })
    return result


def hook_create(name: str, event: str, handler_type: str = "shell", handler: str = "") -> Path:
    """Create a new hook."""
    try:
        hook_event = HookEvent(event)
    except ValueError:
        hook_event = HookEvent.CUSTOM
    
    manager = get_hook_manager()
    return manager.create_hook_file(name, hook_event, handler_type, handler)


def hook_fire(event: str, data: str = "{}", profile: str = "default") -> list:
    """Fire a hook manually."""
    try:
        hook_event = HookEvent(event)
    except ValueError:
        hook_event = HookEvent.CUSTOM
    
    context = HookContext(
        event=hook_event,
        profile=profile,
        data=json.loads(data) if data else {},
    )
    
    manager = get_hook_manager(profile)
    return asyncio.run(manager.fire(hook_event, context))


def hook_webhook_server(host: str = "0.0.0.0", port: int = 8080) -> None:
    """Start webhook server."""
    manager = get_hook_manager()
    server = WebhookServer(manager, host, port)
    asyncio.run(server.start())