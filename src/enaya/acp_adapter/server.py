#!/usr/bin/env python3
"""
Enaya Agent - ACP Server (Agent Context Protocol)
JSON-RPC over stdio for VS Code, Zed, JetBrains IDE integration.
"""

from __future__ import annotations

import asyncio
import json
import sys
import uuid
from collections.abc import AsyncGenerator
from typing import Any

from pydantic import BaseModel

from enaya.cli.config import load_config
from enaya.run_agent import AIAgent, create_agent

# =============================================================================
# ACP Protocol Types
# =============================================================================


class ACPRequest(BaseModel):
    """Base ACP request."""

    jsonrpc: str = "2.0"
    id: str | int
    method: str
    params: dict = {}


class ACPResponse(BaseModel):
    """Base ACP response."""

    jsonrpc: str = "2.0"
    id: str | int
    result: Any = None
    error: dict | None = None


class ACPNotification(BaseModel):
    """ACP notification (no response expected)."""

    jsonrpc: str = "2.0"
    method: str
    params: dict = {}


# =============================================================================
# Session Management
# =============================================================================


class ACPSession:
    """ACP session with agent."""

    def __init__(self, session_id: str, agent: AIAgent):
        self.session_id = session_id
        self.agent = agent
        self.history: list[dict] = []

    async def prompt(self, prompt: str, stream: bool = False) -> str | AsyncGenerator[str, None]:
        """Send prompt to agent."""
        if stream:
            return self._stream_prompt(prompt)
        else:
            return self.agent.run_conversation(prompt)

    async def _stream_prompt(self, prompt: str) -> AsyncGenerator[str, None]:
        """Stream prompt response."""
        # Current agent doesn't support true streaming
        result = self.agent.run_conversation(prompt)
        yield result

    def cancel(self):
        """Cancel current operation."""
        self.agent.interrupt()


# =============================================================================
# ACP Server
# =============================================================================


class ACPServer:
    """ACP JSON-RPC server over stdio."""

    def __init__(self):
        self.sessions: dict[str, ACPSession] = {}
        self.default_agent: AIAgent | None = None

    def initialize(self):
        """Initialize default agent."""
        config = load_config("default")
        self.default_agent = create_agent(
            model=config.get("model", "openrouter:nvidia/nemotron-3-ultra-550b-a55b:free"),
            provider=config.get("provider", "openrouter"),
        )

    async def handle_request(self, request: ACPRequest) -> ACPResponse:
        """Handle incoming JSON-RPC request."""
        try:
            if request.method == "initialize":
                return await self._handle_initialize(request)
            elif request.method == "session/create":
                return await self._handle_session_create(request)
            elif request.method == "session/delete":
                return await self._handle_session_delete(request)
            elif request.method == "session/list":
                return await self._handle_session_list(request)
            elif request.method == "prompt/submit":
                return await self._handle_prompt_submit(request)
            elif request.method == "prompt/cancel":
                return await self._handle_prompt_cancel(request)
            elif request.method == "agent/status":
                return await self._handle_agent_status(request)
            else:
                return ACPResponse(
                    id=request.id,
                    error={"code": -32601, "message": f"Method not found: {request.method}"},
                )
        except Exception as e:
            return ACPResponse(
                id=request.id, error={"code": -32603, "message": f"Internal error: {str(e)}"}
            )

    async def _handle_initialize(self, request: ACPRequest) -> ACPResponse:
        """Handle initialize request."""
        return ACPResponse(
            id=request.id,
            result={
                "protocolVersion": "0.1",
                "capabilities": {
                    "promptSubmit": True,
                    "streaming": True,
                    "sessionManagement": True,
                    "cancellation": True,
                },
                "serverInfo": {
                    "name": "Enaya Agent",
                    "version": "0.1.0",
                },
            },
        )

    async def _handle_session_create(self, request: ACPRequest) -> ACPResponse:
        """Create new session."""
        session_id = request.params.get("sessionId", str(uuid.uuid4()))
        model = request.params.get("model")

        if model and ":" in model:
            provider, model_name = model.split(":", 1)
        else:
            provider = None
            model_name = model

        config = load_config("default")
        default_model = config.get("model", "openrouter:nvidia/nemotron-3-ultra-550b-a55b:free")
        agent = create_agent(
            model=model_name or default_model,
            provider=provider or config.get("provider", "openrouter"),
        )

        session = ACPSession(session_id, agent)
        self.sessions[session_id] = session

        return ACPResponse(id=request.id, result={"sessionId": session_id})

    async def _handle_session_delete(self, request: ACPRequest) -> ACPResponse:
        """Delete session."""
        session_id = request.params.get("sessionId")
        if session_id in self.sessions:
            del self.sessions[session_id]
        return ACPResponse(id=request.id, result={"success": True})

    async def _handle_session_list(self, request: ACPRequest) -> ACPResponse:
        """List sessions."""
        return ACPResponse(
            id=request.id,
            result={
                "sessions": [
                    {"sessionId": sid, "model": s.agent.model} for sid, s in self.sessions.items()
                ]
            },
        )

    async def _handle_prompt_submit(self, request: ACPRequest) -> ACPResponse:
        """Submit prompt to agent."""
        session_id = request.params.get("sessionId")
        prompt = request.params.get("prompt", "")
        stream = request.params.get("stream", False)

        if session_id not in self.sessions:
            return ACPResponse(
                id=request.id, error={"code": -32602, "message": f"Session not found: {session_id}"}
            )

        session = self.sessions[session_id]

        if stream:
            # For streaming, we send notifications
            return ACPResponse(id=request.id, result={"status": "streaming"})
        else:
            result = await session.prompt(prompt)
            return ACPResponse(
                id=request.id,
                result={
                    "content": result,
                    "sessionId": session_id,
                },
            )

    async def _handle_prompt_cancel(self, request: ACPRequest) -> ACPResponse:
        """Cancel prompt."""
        session_id = request.params.get("sessionId")
        if session_id in self.sessions:
            self.sessions[session_id].cancel()
        return ACPResponse(id=request.id, result={"success": True})

    async def _handle_agent_status(self, request: ACPRequest) -> ACPResponse:
        """Get agent status."""
        return ACPResponse(
            id=request.id,
            result={
                "status": "ready",
                "model": self.default_agent.model if self.default_agent else "unknown",
                "provider": self.default_agent.provider if self.default_agent else "unknown",
            },
        )

    async def run_stdio(self):
        """Run server over stdio."""
        self.initialize()

        reader = asyncio.StreamReader()
        protocol = asyncio.StreamReaderProtocol(reader)
        await asyncio.get_event_loop().connect_read_pipe(lambda: protocol, sys.stdin)

        writer = asyncio.StreamWriter(sys.stdout, None, None, None)

        while True:
            line = await reader.readline()
            if not line:
                break

            try:
                request_data = json.loads(line.decode().strip())
                request = ACPRequest(**request_data)
                response = await self.handle_request(request)
                writer.write((response.model_dump_json() + "\n").encode())
                await writer.drain()
            except json.JSONDecodeError:
                continue
            except Exception as e:
                error_response = ACPResponse(
                    id="unknown", error={"code": -32700, "message": f"Parse error: {str(e)}"}
                )
                writer.write((error_response.model_dump_json() + "\n").encode())
                await writer.drain()


# =============================================================================
# Pydantic Models
# =============================================================================


# =============================================================================
# Entry Point
# =============================================================================


def run_acp_server():
    """Run ACP server over stdio."""
    server = ACPServer()
    asyncio.run(server.run_stdio())


if __name__ == "__main__":
    run_acp_server()
