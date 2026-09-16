"""
Enaya Agent - Conversation Loop
Main agent loop (run_conversation) with turn phases.
Mirrors Hermes Agent's agent/conversation_loop.py exactly.
"""

from __future__ import annotations

import json
import uuid
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from enaya.run_agent import AIAgent


def run_conversation(
    agent: AIAgent,
    user_input: str,
    *,
    prefill: str | None = None,
    ephemeral_system_prompt: str | None = None,
) -> str:
    """
    Main conversation loop.
    Handles: history management, prompt building, API calls, tool execution, compression, persistence.
    """
    task_id = str(uuid.uuid4())
    agent._iteration_count = 0

    # 1. Append user message to conversation history
    user_msg = {"role": "user", "content": user_input}
    agent.conversation_history.append(user_msg)

    # 2. Build or reuse cached system prompt
    system_prompt = agent.get_system_prompt()

    # 3. Check preflight compression
    agent.maybe_compress()

    # 4. Build API messages from conversation history
    messages = _build_api_messages(agent, system_prompt, prefill, ephemeral_system_prompt)

    # 5. Main loop
    while agent._iteration_count < agent.config.max_turns:
        agent._iteration_count += 1

        if agent.is_interrupted():
            return _handle_interruption(agent)

        # Make API call
        response = _make_interruptible_api_call(agent, messages)

        # Parse response
        content = response.get("content", "")
        tool_calls = response.get("tool_calls", [])
        finish_reason = response.get("finish_reason", "stop")
        usage = response.get("usage", {})

        # Handle reasoning content if present
        reasoning = response.get("reasoning")
        if reasoning and agent.reasoning_callback:
            agent.reasoning_callback(reasoning)

        # If tool calls, execute them
        if tool_calls:
            # Append assistant message with tool_calls
            assistant_msg = {"role": "assistant", "content": content, "tool_calls": tool_calls}
            agent.conversation_history.append(assistant_msg)

            # Execute tools
            tool_results = _execute_tool_calls(agent, tool_calls, task_id)

            # Append tool results
            for result in tool_results:
                agent.conversation_history.append(result)

            # Rebuild messages for next iteration
            messages = _build_api_messages(agent, system_prompt, prefill, ephemeral_system_prompt)

            # Check compression again
            agent.maybe_compress()

            continue

        # No tool calls - final response
        assistant_msg = {"role": "assistant", "content": content}
        agent.conversation_history.append(assistant_msg)

        # Persist session
        agent._save_session()
        agent._flush_memory()

        return content

    # Max turns reached
    return _handle_max_turns(agent)


def _build_api_messages(
    agent: AIAgent,
    system_prompt: str,
    prefill: str | None = None,
    ephemeral_system_prompt: str | None = None,
) -> list[dict]:
    """Build messages array for API call based on api_mode."""
    messages = [{"role": "system", "content": system_prompt}]

    # Add ephemeral system prompt if provided
    if ephemeral_system_prompt:
        messages.append({"role": "system", "content": ephemeral_system_prompt})

    # Add conversation history
    messages.extend(agent.conversation_history)

    # Add prefill if provided (for response continuation)
    if prefill:
        messages.append({"role": "assistant", "content": prefill})

    return messages


def _make_interruptible_api_call(agent: AIAgent, messages: list[dict]) -> dict:
    """Make an interruptible API call with timeout and interrupt handling."""
    import threading

    result_container = {"response": None, "error": None}
    event = threading.Event()

    def api_thread():
        try:
            if agent.thinking_callback:
                agent.thinking_callback(True)
            result_container["response"] = agent._make_api_call(messages)
        except Exception as e:
            result_container["error"] = e
        finally:
            if agent.thinking_callback:
                agent.thinking_callback(False)
            event.set()

    thread = threading.Thread(target=api_thread, daemon=True)
    thread.start()

    # Wait with interrupt checking
    while not event.is_set():
        if agent.is_interrupted():
            # Interrupt triggered - abandon thread
            return {"content": "", "tool_calls": [], "finish_reason": "interrupted"}
        event.wait(timeout=0.1)

    if result_container["error"]:
        raise result_container["error"]

    return result_container["response"]


def _execute_tool_calls(agent: AIAgent, tool_calls: list[dict], task_id: str) -> list[dict]:
    """Execute tool calls sequentially or concurrently."""
    # Check if any tool requires sequential execution (e.g., clarify)
    requires_sequential = any(
        tc.get("function", {}).get("name") in ("clarify", "session_search", "memory", "todo", "delegate_task")
        for tc in tool_calls
    )

    results = []

    if requires_sequential or len(tool_calls) == 1:
        # Sequential execution
        for tc in tool_calls:
            result = _execute_single_tool(agent, tc, task_id)
            results.append(result)
    else:
        # Concurrent execution
        from concurrent.futures import ThreadPoolExecutor, as_completed

        with ThreadPoolExecutor(max_workers=len(tool_calls)) as executor:
            futures = {
                executor.submit(_execute_single_tool, agent, tc, task_id): tc
                for tc in tool_calls
            }
            for future in as_completed(futures):
                results.append(future.result())

        # Reorder results to match original tool_calls order
        id_to_result = {r["tool_call_id"]: r for r in results}
        results = [id_to_result[tc["id"]] for tc in tool_calls]

    return results


def _execute_single_tool(agent: AIAgent, tool_call: dict, task_id: str) -> dict:
    """Execute a single tool call with callbacks and error handling."""
    tool_name = tool_call.get("function", {}).get("name", "unknown")
    tool_args = tool_call.get("function", {}).get("arguments", "{}")

    # Progress callback - start
    if agent.tool_progress_callback:
        agent.tool_progress_callback(tool_name, "start", True)

    try:
        # Parse arguments
        args = json.loads(tool_args) if isinstance(tool_args, str) else tool_args

        # Execute via agent's execute_tool (handles agent-level tools)
        result_content = agent.execute_tool(tool_call, task_id)

    except Exception as e:
        result_content = json.dumps({"error": str(e)})

    # Progress callback - end
    if agent.tool_progress_callback:
        agent.tool_progress_callback(tool_name, "complete", False)

    return {
        "role": "tool",
        "tool_call_id": tool_call["id"],
        "content": result_content,
    }


def _handle_interruption(agent: AIAgent) -> str:
    """Handle graceful interruption."""
    agent._save_session()
    agent._flush_memory()
    return "[Interrupted]"


def _handle_max_turns(agent: AIAgent) -> str:
    """Handle max turns reached."""
    agent._save_session()
    agent._flush_memory()
    summary = f"[Max turns ({agent.config.max_turns}) reached. Conversation incomplete.]"
    if agent.conversation_history:
        last_assistant = next(
            (msg for msg in reversed(agent.conversation_history) if msg["role"] == "assistant"),
            None,
        )
        if last_assistant:
            summary += f"\n\nLast response:\n{last_assistant.get('content', '')}"
    return summary
