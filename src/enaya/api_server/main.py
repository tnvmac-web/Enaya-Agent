#!/usr/bin/env python3
"""
Enaya Agent - API Server (OpenAI-Compatible)
HTTP + SSE server for OpenAI-compatible frontends.
"""

from __future__ import annotations

import asyncio
import json
import uuid
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from dataclasses import dataclass, field

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from enaya.cli.config import load_config
from enaya.run_agent import AIAgent, create_agent

# =============================================================================
# Request/Response Models (OpenAI-Compatible)
# =============================================================================

class Message(BaseModel):
    role: str
    content: str | list[dict] = ""
    name: str | None = None
    tool_calls: list[dict] | None = None
    tool_call_id: str | None = None


class ChatCompletionRequest(BaseModel):
    model: str
    messages: list[Message]
    temperature: float = 0.7
    top_p: float = 1.0
    stream: bool = False
    max_tokens: int | None = None
    tools: list[dict] | None = None
    tool_choice: str | dict | None = None


class ChatCompletionChoice(BaseModel):
    index: int
    message: Message
    finish_reason: str


class ChatCompletionResponse(BaseModel):
    id: str
    object: str = "chat.completion"
    created: int
    model: str
    choices: list[ChatCompletionChoice]
    usage: dict = field(default_factory=dict)


class ChatCompletionStreamChoice(BaseModel):
    index: int
    delta: Message
    finish_reason: str | None = None


class ChatCompletionStreamResponse(BaseModel):
    id: str
    object: str = "chat.completion.chunk"
    created: int
    model: str
    choices: list[ChatCompletionStreamChoice]


class RunRequest(BaseModel):
    prompt: str
    model: str | None = None
    stream: bool = False
    max_turns: int = 500
    toolsets: list[str] | None = None
    metadata: dict = field(default_factory=dict)


class RunResponse(BaseModel):
    run_id: str
    status: str
    result: str | None = None


class RunEvent(BaseModel):
    type: str  # message.delta, message.complete, tool.start, tool.complete, etc.
    run_id: str
    data: dict


class ModelInfo(BaseModel):
    id: str
    object: str = "model"
    created: int
    owned_by: str = "enaya"


class ModelsResponse(BaseModel):
    object: str = "list"
    data: list[ModelInfo]


class CapabilitiesResponse(BaseModel):
    streaming: bool = True
    tools: bool = True
    vision: bool = False
    audio: bool = False
    functions: bool = True


# =============================================================================
# Global State
# =============================================================================

@dataclass
class APIServerState:
    agents: dict[str, AIAgent] = field(default_factory=dict)
    runs: dict[str, dict] = field(default_factory=dict)


state = APIServerState()


# =============================================================================
# FastAPI App
# =============================================================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    config = load_config("default")
    default_agent = create_agent(
        model=config.get("model", "openrouter:nvidia/nemotron-3-ultra-550b-a55b:free"),
        provider=config.get("provider", "openrouter"),
    )
    state.agents["default"] = default_agent
    yield
    # Shutdown
    state.agents.clear()
    state.runs.clear()


app = FastAPI(
    title="Enaya Agent API",
    description="OpenAI-compatible API for Enaya Agent",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def get_agent(model: str | None = None) -> AIAgent:
    """Get or create agent for model."""
    if model and model in state.agents:
        return state.agents[model]

    if "default" in state.agents:
        return state.agents["default"]

    config = load_config("default")
    agent = create_agent(
        model=model or config.get("model", "openrouter:nvidia/nemotron-3-ultra-550b-a55b:free"),
        provider=config.get("provider", "openrouter"),
    )
    if model:
        state.agents[model] = agent
    return agent


# =============================================================================
# Health Endpoints
# =============================================================================

@app.get("/health")
async def health():
    return {"status": "ok", "service": "enaya-agent"}


@app.get("/health/detailed")
async def health_detailed():
    config = load_config("default")
    return {
        "status": "ok",
        "service": "enaya-agent",
        "version": "0.1.0",
        "default_model": config.get("model"),
        "active_agents": len(state.agents),
        "active_runs": len(state.runs),
    }


# =============================================================================
# Model Endpoints
# =============================================================================

@app.get("/v1/models", response_model=ModelsResponse)
async def list_models():
    """List available models (OpenAI-compatible)."""
    models = [
        ModelInfo(id="openrouter:nvidia/nemotron-3-ultra-550b-a55b:free", created=1700000000, owned_by="enaya"),
        ModelInfo(id="openrouter:anthropic/claude-3.5-sonnet", created=1700000000, owned_by="enaya"),
        ModelInfo(id="openrouter:openai/gpt-4o", created=1700000000, owned_by="enaya"),
        ModelInfo(id="openrouter:google/gemini-1.5-pro", created=1700000000, owned_by="enaya"),
    ]
    return ModelsResponse(data=models)


@app.get("/api/model/options")
async def model_options():
    """Provider-aware model picker inventory."""
    return {
        "providers": [
            {
                "id": "openrouter",
                "name": "OpenRouter",
                "models": [
                    {"id": "nvidia/nemotron-3-ultra-550b-a55b:free", "name": "Nemotron 3 Ultra (free)"},
                    {"id": "anthropic/claude-3.5-sonnet", "name": "Claude 3.5 Sonnet"},
                    {"id": "openai/gpt-4o", "name": "GPT-4o"},
                    {"id": "google/gemini-1.5-pro", "name": "Gemini 1.5 Pro"},
                ],
            },
        ],
        "current": "openrouter:nvidia/nemotron-3-ultra-550b-a55b:free",
    }


@app.get("/v1/capabilities", response_model=CapabilitiesResponse)
async def capabilities():
    """Machine-readable feature flags."""
    return CapabilitiesResponse()


# =============================================================================
# Chat Completions
# =============================================================================

@app.post("/v1/chat/completions")
async def chat_completions(request: ChatCompletionRequest):
    """OpenAI Chat Completions endpoint."""
    agent = get_agent(request.model)

    # Convert messages to single prompt
    prompt = _messages_to_prompt(request.messages)

    if request.stream:
        return StreamingResponse(
            _stream_chat_completions(agent, prompt, request.model),
            media_type="text/event-stream",
        )
    else:
        result = agent.run_conversation(prompt)
        return _format_chat_response(result, request.model)


async def _stream_chat_completions(agent: AIAgent, prompt: str, model: str) -> AsyncGenerator[str, None]:
    """Stream chat completions."""
    run_id = f"chatcmpl-{uuid.uuid4().hex[:8]}"
    created = int(asyncio.get_event_loop().time())

    # Send first chunk with role
    first_chunk = ChatCompletionStreamResponse(
        id=run_id,
        created=created,
        model=model,
        choices=[ChatCompletionStreamChoice(index=0, delta=Message(role="assistant"))],
    )
    yield f"data: {first_chunk.model_dump_json()}\n\n"

    # Run agent and stream result
    # Note: Current agent doesn't support true streaming, so we simulate
    result = agent.run_conversation(prompt)

    # Stream in chunks
    chunk_size = 50
    for i in range(0, len(result), chunk_size):
        chunk_text = result[i:i+chunk_size]
        chunk = ChatCompletionStreamResponse(
            id=run_id,
            created=created,
            model=model,
            choices=[ChatCompletionStreamChoice(
                index=0,
                delta=Message(content=chunk_text),
            )],
        )
        yield f"data: {chunk.model_dump_json()}\n\n"
        await asyncio.sleep(0.01)

    # Final chunk
    final_chunk = ChatCompletionStreamResponse(
        id=run_id,
        created=created,
        model=model,
        choices=[ChatCompletionStreamChoice(
            index=0,
            delta=Message(content=""),
            finish_reason="stop",
        )],
    )
    yield f"data: {final_chunk.model_dump_json()}\n\n"
    yield "data: [DONE]\n\n"


def _messages_to_prompt(messages: list[Message]) -> str:
    """Convert OpenAI messages to single prompt."""
    parts = []
    for msg in messages:
        if msg.role == "system":
            parts.append(f"System: {msg.content}")
        elif msg.role == "user":
            parts.append(f"User: {msg.content}")
        elif msg.role == "assistant":
            parts.append(f"Assistant: {msg.content}")
    return "\n\n".join(parts)


def _format_chat_response(content: str, model: str) -> ChatCompletionResponse:
    """Format agent response as OpenAI chat completion."""
    return ChatCompletionResponse(
        id=f"chatcmpl-{uuid.uuid4().hex[:8]}",
        created=int(asyncio.get_event_loop().time()),
        model=model,
        choices=[ChatCompletionChoice(
            index=0,
            message=Message(role="assistant", content=content),
            finish_reason="stop",
        )],
        usage={
            "prompt_tokens": 0,
            "completion_tokens": 0,
            "total_tokens": 0,
        },
    )


# =============================================================================
# Runs Endpoints (Stateful)
# =============================================================================

@app.post("/v1/runs", response_model=RunResponse)
async def create_run(request: RunRequest):
    """Start a run."""
    run_id = f"run-{uuid.uuid4().hex[:8]}"
    agent = get_agent(request.model)

    if request.toolsets:
        agent.config.toolsets = request.toolsets
    agent.config.max_turns = request.max_turns

    state.runs[run_id] = {
        "agent": agent,
        "prompt": request.prompt,
        "status": "running",
        "result": None,
        "metadata": request.metadata,
    }

    # Run in background
    asyncio.create_task(_execute_run(run_id, agent, request.prompt))

    return RunResponse(run_id=run_id, status="running")


async def _execute_run(run_id: str, agent: AIAgent, prompt: str):
    """Execute run in background."""
    try:
        result = agent.run_conversation(prompt)
        state.runs[run_id]["status"] = "completed"
        state.runs[run_id]["result"] = result
    except Exception as e:
        state.runs[run_id]["status"] = "failed"
        state.runs[run_id]["error"] = str(e)


@app.get("/v1/runs/{run_id}", response_model=RunResponse)
async def get_run(run_id: str):
    """Get run status."""
    if run_id not in state.runs:
        raise HTTPException(404, "Run not found")

    run = state.runs[run_id]
    return RunResponse(
        run_id=run_id,
        status=run["status"],
        result=run.get("result"),
    )


@app.get("/v1/runs/{run_id}/events")
async def run_events(run_id: str):
    """SSE stream of run lifecycle events."""
    if run_id not in state.runs:
        raise HTTPException(404, "Run not found")

    async def event_stream():
        run = state.runs[run_id]

        # Initial event
        yield f"data: {json.dumps({'type': 'run.started', 'run_id': run_id})}\n\n"

        # Poll for completion
        while run["status"] == "running":
            await asyncio.sleep(0.5)
            if run["status"] != "running":
                break

        if run["status"] == "completed":
            yield f"data: {json.dumps({'type': 'run.completed', 'run_id': run_id, 'result': run['result']})}\n\n"
        elif run["status"] == "failed":
            yield f"data: {json.dumps({'type': 'run.failed', 'run_id': run_id, 'error': run.get('error')})}\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")


@app.post("/v1/runs/{run_id}/stop")
async def stop_run(run_id: str):
    """Interrupt a run."""
    if run_id not in state.runs:
        raise HTTPException(404, "Run not found")

    run = state.runs[run_id]
    run["agent"].interrupt()
    run["status"] = "interrupted"
    return {"status": "interrupted"}


@app.post("/v1/runs/{run_id}/steer")
async def steer_run(run_id: str, request: Request):
    """Inject mid-run guidance."""
    if run_id not in state.runs:
        raise HTTPException(404, "Run not found")

    body = await request.json()
    steer_text = body.get("text", "")

    # In a real implementation, this would inject into the agent's context
    return {"status": "steered", "text": steer_text}


# =============================================================================
# Browser Control (Stub)
# =============================================================================

@app.post("/v1/browser-control/register")
async def register_browser_control(request: Request):
    """Register a browser controller."""
    return {"status": "registered", "controller_id": str(uuid.uuid4())}


# =============================================================================
# Run Server
# =============================================================================

def run_api_server(host: str = "0.0.0.0", port: int = 8000):
    """Run the API server."""
    import uvicorn
    uvicorn.run(app, host=host, port=port)


if __name__ == "__main__":
    run_api_server()
