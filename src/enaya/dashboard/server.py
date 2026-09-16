#!/usr/bin/env python3
"""
Enaya Agent - Dashboard Server
Serves the web dashboard and provides API endpoints.
"""

from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse

app = FastAPI(title="Enaya Agent Dashboard")

# Serve the dashboard HTML
DASHBOARD_PATH = Path(__file__).parent / "index.html"


@app.get("/", response_class=HTMLResponse)
async def dashboard():
    """Serve the main dashboard."""
    if DASHBOARD_PATH.exists():
        return HTMLResponse(DASHBOARD_PATH.read_text())
    return HTMLResponse(
        "<h1>Dashboard not built</h1><p>Run: npm run build in src/enaya/dashboard</p>"
    )


@app.get("/api/chat")
async def chat_endpoint(
    message: str,
    model: str = "openrouter:nvidia/nemotron-3-ultra-550b-a55b:free",
    stream: bool = False,
):
    """Chat API endpoint for the dashboard."""
    from enaya.run_agent import create_agent

    agent = create_agent(model=model)
    result = agent.run_conversation(message)

    if stream:
        # Return as SSE
        from fastapi.responses import StreamingResponse

        async def generate():
            yield f"data: {result}\n\n"
            yield "data: [DONE]\n\n"

        return StreamingResponse(generate(), media_type="text/event-stream")

    return {"response": result, "model": model}


@app.websocket("/ws/chat")
async def websocket_chat(websocket: WebSocket):
    """WebSocket for real-time chat."""
    await websocket.accept()
    try:
        while True:
            data = await websocket.receive_json()
            message = data.get("message", "")
            model = data.get("model", "openrouter:nvidia/nemotron-3-ultra-550b-a55b:free")

            from enaya.run_agent import create_agent

            agent = create_agent(model=model)
            result = agent.run_conversation(message)

            await websocket.send_json({"response": result})
    except WebSocketDisconnect:
        pass
    except Exception as e:
        await websocket.send_json({"error": str(e)})


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8080)
