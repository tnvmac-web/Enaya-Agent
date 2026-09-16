#!/usr/bin/env python3
"""
Enaya Agent - MCP (Model Context Protocol) Client
MCP client facade for connecting to external tool servers.
"""

from __future__ import annotations

import asyncio
import json
import os
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any

import httpx

# =============================================================================
# MCP Data Classes
# =============================================================================

@dataclass
class MCPServerConfig:
    """MCP server configuration."""
    name: str
    transport: str = "stdio"  # stdio, sse, websocket
    command: list[str] = field(default_factory=list)
    args: list[str] = field(default_factory=list)
    env: dict[str, str] = field(default_factory=dict)
    url: str = ""  # for sse/websocket
    headers: dict[str, str] = field(default_factory=dict)
    timeout: float = 30.0


@dataclass
class MCPTool:
    """MCP tool definition."""
    name: str
    description: str
    input_schema: dict
    server_name: str


@dataclass
class MCPResource:
    """MCP resource definition."""
    uri: str
    name: str
    description: str
    mime_type: str
    server_name: str


@dataclass
class MCPPrompt:
    """MCP prompt template."""
    name: str
    description: str
    arguments: list[dict]
    server_name: str


# =============================================================================
# MCP Client Base
# =============================================================================

class MCPClient(ABC):
    """Abstract MCP client."""

    def __init__(self, config: MCPServerConfig):
        self.config = config
        self._connected = False
        self._tools: list[MCPTool] = []
        self._resources: list[MCPResource] = []
        self._prompts: list[MCPPrompt] = []

    @abstractmethod
    async def connect(self) -> None:
        """Connect to MCP server."""
        pass

    @abstractmethod
    async def disconnect(self) -> None:
        """Disconnect from MCP server."""
        pass

    @abstractmethod
    async def list_tools(self) -> list[MCPTool]:
        """List available tools."""
        pass

    @abstractmethod
    async def call_tool(self, name: str, arguments: dict) -> Any:
        """Call a tool."""
        pass

    @abstractmethod
    async def list_resources(self) -> list[MCPResource]:
        """List available resources."""
        pass

    @abstractmethod
    async def read_resource(self, uri: str) -> str:
        """Read a resource."""
        pass

    @abstractmethod
    async def list_prompts(self) -> list[MCPPrompt]:
        """List available prompts."""
        pass

    @abstractmethod
    async def get_prompt(self, name: str, arguments: dict) -> str:
        """Get a prompt template."""
        pass


# =============================================================================
# STDIO Transport Client
# =============================================================================

class StdioMCPClient(MCPClient):
    """MCP client using stdio transport."""

    def __init__(self, config: MCPServerConfig):
        super().__init__(config)
        self._process: asyncio.subprocess.Process | None = None
        self._request_id = 0
        self._pending: dict[int, asyncio.Future] = {}

    async def connect(self) -> None:
        """Start the MCP server process."""
        if not self.config.command:
            raise RuntimeError("No command specified for stdio transport")

        self._process = await asyncio.create_subprocess_exec(
            self.config.command[0],
            *self.config.args,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env={**os.environ, **self.config.env},
        )

        # Start reading stdout
        asyncio.create_task(self._read_stdout())

        # Initialize
        await self._send_request("initialize", {
            "protocolVersion": "2024-11-05",
            "capabilities": {},
            "clientInfo": {"name": "enaya-agent", "version": "0.1.0"},
        })

        self._connected = True

        # Load tools, resources, prompts
        self._tools = await self.list_tools()
        self._resources = await self.list_resources()
        self._prompts = await self.list_prompts()

    async def disconnect(self) -> None:
        """Stop the MCP server process."""
        if self._process:
            await self._send_request("shutdown", {})
            self._process.terminate()
            await self._process.wait()
            self._process = None
        self._connected = False

    async def _send_request(self, method: str, params: dict) -> Any:
        """Send JSON-RPC request."""
        self._request_id += 1
        request_id = self._request_id

        request = {
            "jsonrpc": "2.0",
            "id": request_id,
            "method": method,
            "params": params,
        }

        future = asyncio.get_event_loop().create_future()
        self._pending[request_id] = future

        if self._process and self._process.stdin:
            message = json.dumps(request) + "\n"
            self._process.stdin.write(message.encode())
            await self._process.stdin.drain()

        try:
            return await asyncio.wait_for(future, timeout=self.config.timeout)
        except TimeoutError:
            raise RuntimeError(f"MCP request timeout: {method}")

    async def _read_stdout(self) -> None:
        """Read responses from stdout."""
        if not self._process or not self._process.stdout:
            return

        while True:
            line = await self._process.stdout.readline()
            if not line:
                break

            try:
                response = json.loads(line.decode().strip())

                if "id" in response and response["id"] in self._pending:
                    future = self._pending.pop(response["id"])
                    if "error" in response:
                        future.set_exception(RuntimeError(response["error"]["message"]))
                    else:
                        future.set_result(response.get("result"))

            except json.JSONDecodeError:
                continue

    async def list_tools(self) -> list[MCPTool]:
        if not self._connected:
            await self.connect()

        result = await self._send_request("tools/list", {})
        tools = []
        for t in result.get("tools", []):
            tools.append(MCPTool(
                name=t["name"],
                description=t["description"],
                input_schema=t["inputSchema"],
                server_name=self.config.name,
            ))
        self._tools = tools
        return tools

    async def call_tool(self, name: str, arguments: dict) -> Any:
        result = await self._send_request("tools/call", {
            "name": name,
            "arguments": arguments,
        })
        return result.get("content", [])

    async def list_resources(self) -> list[MCPResource]:
        result = await self._send_request("resources/list", {})
        resources = []
        for r in result.get("resources", []):
            resources.append(MCPResource(
                uri=r["uri"],
                name=r["name"],
                description=r.get("description", ""),
                mime_type=r.get("mimeType", "text/plain"),
                server_name=self.config.name,
            ))
        self._resources = resources
        return resources

    async def read_resource(self, uri: str) -> str:
        result = await self._send_request("resources/read", {"uri": uri})
        contents = result.get("contents", [])
        if contents:
            return contents[0].get("text", "")
        return ""

    async def list_prompts(self) -> list[MCPPrompt]:
        result = await self._send_request("prompts/list", {})
        prompts = []
        for p in result.get("prompts", []):
            prompts.append(MCPPrompt(
                name=p["name"],
                description=p["description"],
                arguments=p.get("arguments", []),
                server_name=self.config.name,
            ))
        self._prompts = prompts
        return prompts

    async def get_prompt(self, name: str, arguments: dict) -> str:
        result = await self._send_request("prompts/get", {
            "name": name,
            "arguments": arguments,
        })
        messages = result.get("messages", [])
        return "\n".join(m.get("content", {}).get("text", "") for m in messages)


# =============================================================================
# SSE Transport Client
# =============================================================================

class SSEClient(MCPClient):
    """MCP client using SSE transport."""

    def __init__(self, config: MCPServerConfig):
        super().__init__(config)
        self._client: httpx.AsyncClient | None = None
        self._event_source = None

    async def connect(self) -> None:
        if not self.config.url:
            raise RuntimeError("No URL specified for SSE transport")

        self._client = httpx.AsyncClient(
            headers=self.config.headers,
            timeout=self.config.timeout,
        )

        # Initialize
        await self._send_request("initialize", {
            "protocolVersion": "2024-11-05",
            "capabilities": {},
            "clientInfo": {"name": "enaya-agent", "version": "0.1.0"},
        })

        self._connected = True

        # Load tools, resources, prompts
        self._tools = await self.list_tools()
        self._resources = await self.list_resources()
        self._prompts = await self.list_prompts()

    async def disconnect(self) -> None:
        if self._client:
            await self._send_request("shutdown", {})
            await self._client.aclose()
            self._client = None
        self._connected = False

    async def _send_request(self, method: str, params: dict) -> Any:
        if not self._client:
            raise RuntimeError("Not connected")

        response = await self._client.post(
            f"{self.config.url}/mcp",
            json={
                "jsonrpc": "2.0",
                "id": 1,
                "method": method,
                "params": params,
            },
            timeout=self.config.timeout,
        )
        response.raise_for_status()
        result = response.json()

        if "error" in result:
            raise RuntimeError(result["error"]["message"])

        return result.get("result")

    async def list_tools(self) -> list[MCPTool]:
        result = await self._send_request("tools/list", {})
        return [MCPTool(name=t["name"], description=t["description"], input_schema=t["inputSchema"], server_name=self.config.name) for t in result.get("tools", [])]

    async def call_tool(self, name: str, arguments: dict) -> Any:
        result = await self._send_request("tools/call", {"name": name, "arguments": arguments})
        return result.get("content", [])

    async def list_resources(self) -> list[MCPResource]:
        result = await self._send_request("resources/list", {})
        return [MCPResource(uri=r["uri"], name=r["name"], description=r.get("description", ""), mime_type=r.get("mimeType", "text/plain"), server_name=self.config.name) for r in result.get("resources", [])]

    async def read_resource(self, uri: str) -> str:
        result = await self._send_request("resources/read", {"uri": uri})
        return result.get("contents", [{}])[0].get("text", "")

    async def list_prompts(self) -> list[MCPPrompt]:
        result = await self._send_request("prompts/list", {})
        return [MCPPrompt(name=p["name"], description=p["description"], arguments=p.get("arguments", []), server_name=self.config.name) for p in result.get("prompts", [])]

    async def get_prompt(self, name: str, arguments: dict) -> str:
        result = await self._send_request("prompts/get", {"name": name, "arguments": arguments})
        return "\n".join(m.get("content", {}).get("text", "") for m in result.get("messages", []))


# =============================================================================
# MCP Manager
# =============================================================================

class MCPManager:
    """Manages multiple MCP server connections."""

    def __init__(self):
        self.servers: dict[str, MCPClient] = {}
        self.configs: dict[str, MCPServerConfig] = {}

    def add_server(self, config: MCPServerConfig) -> None:
        self.configs[config.name] = config

    def remove_server(self, name: str) -> bool:
        if name in self.servers:
            asyncio.create_task(self.servers[name].disconnect())
            del self.servers[name]
            del self.configs[name]
            return True
        return False

    async def connect(self, name: str) -> MCPClient:
        """Connect to a server."""
        if name in self.servers:
            return self.servers[name]

        if name not in self.configs:
            raise ValueError(f"Server not configured: {name}")

        config = self.configs[name]

        if config.transport == "stdio":
            client = StdioMCPClient(config)
        elif config.transport == "sse":
            client = SSEClient(config)
        else:
            raise ValueError(f"Unsupported transport: {config.transport}")

        await client.connect()
        self.servers[name] = client
        return client

    async def disconnect(self, name: str) -> bool:
        if name in self.servers:
            await self.servers[name].disconnect()
            del self.servers[name]
            return True
        return False

    async def disconnect_all(self) -> None:
        for name in list(self.servers.keys()):
            await self.disconnect(name)

    def get_client(self, name: str) -> MCPClient | None:
        return self.servers.get(name)

    def list_servers(self) -> list[dict]:
        return [
            {"name": name, "connected": name in self.servers, "config": self.configs[name]}
            for name in self.configs
        ]

    # Convenience methods
    async def list_all_tools(self) -> list[MCPTool]:
        all_tools = []
        for client in self.servers.values():
            tools = await client.list_tools()
            all_tools.extend(tools)
        return all_tools

    async def call_tool(self, server_name: str, tool_name: str, arguments: dict) -> Any:
        client = self.servers.get(server_name)
        if not client:
            raise ValueError(f"Server not connected: {server_name}")
        return await client.call_tool(tool_name, arguments)

    async def list_all_resources(self) -> list[MCPResource]:
        all_resources = []
        for client in self.servers.values():
            resources = await client.list_resources()
            all_resources.extend(resources)
        return all_resources


# =============================================================================
# MCP Tool Integration
# =============================================================================

MCP_TOOL_SCHEMA = {
    "type": "function",
    "function": {
        "name": "mcp",
        "description": "Manage MCP servers: connect, list tools, call tools, read resources",
        "parameters": {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "enum": ["add_server", "connect", "disconnect", "list_servers", "list_tools", "call_tool", "list_resources", "read_resource"],
                    "description": "Action to perform",
                },
                "server_name": {"type": "string", "description": "Server name"},
                "transport": {"type": "string", "enum": ["stdio", "sse"], "default": "stdio"},
                "command": {"type": "array", "items": {"type": "string"}, "description": "Command for stdio transport"},
                "args": {"type": "array", "items": {"type": "string"}, "description": "Command arguments"},
                "url": {"type": "string", "description": "URL for SSE transport"},
                "tool_name": {"type": "string", "description": "Tool to call"},
                "arguments": {"type": "object", "description": "Tool arguments"},
                "resource_uri": {"type": "string", "description": "Resource URI to read"},
            },
            "required": ["action"],
        },
    },
}


async def mcp_tool(action: str, **kwargs) -> str:
    """MCP tool handler."""
    import json

    manager = MCPManager()

    try:
        if action == "add_server":
            config = MCPServerConfig(
                name=kwargs["server_name"],
                transport=kwargs.get("transport", "stdio"),
                command=kwargs.get("command", []),
                args=kwargs.get("args", []),
                url=kwargs.get("url", ""),
            )
            manager.add_server(config)
            return json.dumps({"success": True, "message": f"Server {kwargs['server_name']} added"})

        elif action == "connect":
            client = await manager.connect(kwargs["server_name"])
            return json.dumps({"success": True, "message": f"Connected to {kwargs['server_name']}"})

        elif action == "disconnect":
            await manager.disconnect(kwargs["server_name"])
            return json.dumps({"success": True, "message": f"Disconnected from {kwargs['server_name']}"})

        elif action == "list_servers":
            return json.dumps({"servers": manager.list_servers()})

        elif action == "list_tools":
            tools = await manager.list_all_tools()
            return json.dumps({
                "tools": [
                    {"name": t.name, "description": t.description, "server": t.server_name}
                    for t in tools
                ]
            })

        elif action == "call_tool":
            result = await manager.call_tool(kwargs["server_name"], kwargs["tool_name"], kwargs.get("arguments", {}))
            return json.dumps({"result": result})

        elif action == "list_resources":
            resources = await manager.list_all_resources()
            return json.dumps({
                "resources": [
                    {"uri": r.uri, "name": r.name, "description": r.description, "server": r.server_name}
                    for r in resources
                ]
            })

        elif action == "read_resource":
            client = manager.servers.get(kwargs["server_name"])
            if not client:
                return json.dumps({"error": f"Server not connected: {kwargs['server_name']}"})
            content = await client.read_resource(kwargs["resource_uri"])
            return json.dumps({"content": content})

        else:
            return json.dumps({"error": f"Unknown action: {action}"})

    except Exception as e:
        return json.dumps({"error": str(e)})
