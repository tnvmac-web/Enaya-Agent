#!/usr/bin/env python3
"""
Enaya Agent - Gateway Core
Messaging platform gateway with session routing, authorization, and delivery.
"""

from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass, field
from typing import Any

from enaya.cli.config import load_config
from enaya.hermes_state import SessionStore
from enaya.run_agent import AIAgent, create_agent

# =============================================================================
# Data Classes
# =============================================================================


@dataclass
class MessageEvent:
    """Incoming message event from a platform."""

    platform: str
    chat_type: str  # private, group, channel
    chat_id: str
    user_id: str
    username: str | None = None
    text: str = ""
    message_id: str | None = None
    timestamp: float = field(default_factory=time.time)
    raw: dict = field(default_factory=dict)


@dataclass
class GatewaySession:
    """Gateway session info."""

    session_key: str
    profile: str
    platform: str
    chat_type: str
    chat_id: str
    user_id: str
    agent: AIAgent | None = None
    created_at: float = field(default_factory=time.time)
    last_activity: float = field(default_factory=time.time)
    message_count: int = 0


@dataclass
class PendingMessage:
    """Queued message when agent is busy."""

    event: MessageEvent
    future: asyncio.Future


# =============================================================================
# Gateway Runner
# =============================================================================


class GatewayRunner:
    """
    Main gateway message dispatch.
    Handles: authorization, session resolution, agent creation, delivery.
    """

    def __init__(self, profile: str = "default"):
        self.profile = profile
        self.config = load_config(profile)

        # Session storage
        self.session_store = SessionStore(profile=profile)

        # Active sessions
        self._active_sessions: dict[str, GatewaySession] = {}
        self._pending_messages: dict[str, list[PendingMessage]] = {}

        # Platform adapters
        self._adapters: dict[str, Any] = {}

        # Authorization
        self._allow_all = self.config.get("gateway_allow_all_users", False)
        self._allowed_users: dict[str, set[str]] = {}  # platform -> user_ids

        # Home channel for cron deliveries
        self._home_channels: dict[str, tuple[str, str]] = {}  # platform -> (chat_type, chat_id)

        # Hooks
        self._hooks: dict[str, list[callable]] = {}

        # Running flag
        self._running = False

    def register_adapter(self, platform: str, adapter: Any) -> None:
        """Register a platform adapter."""
        self._adapters[platform] = adapter
        adapter.gateway = self

    def add_hook(self, event: str, handler: callable) -> None:
        """Add a gateway hook."""
        if event not in self._hooks:
            self._hooks[event] = []
        self._hooks[event].append(handler)

    async def _fire_hook(self, event: str, **kwargs) -> None:
        """Fire gateway hooks."""
        for handler in self._hooks.get(event, []):
            try:
                if asyncio.iscoroutinefunction(handler):
                    await handler(**kwargs)
                else:
                    handler(**kwargs)
            except Exception:
                pass  # Hook errors shouldn't break gateway

    def authorize_user(self, platform: str, user_id: str) -> bool:
        """Check if user is authorized."""
        if self._allow_all:
            return True

        if platform in self._allowed_users:
            return user_id in self._allowed_users[platform]

        return False

    def resolve_session_key(self, event: MessageEvent) -> str:
        """Build session key for this conversation."""
        return f"agent:{self.profile}:{event.platform}:{event.chat_type}:{event.chat_id}"

    async def handle_message(self, event: MessageEvent) -> None:
        """Main message handling entry point."""
        # Check authorization
        if not self.authorize_user(event.platform, event.user_id):
            await self._send_reply(event, "❌ You are not authorized to use this bot.")
            return

        # Resolve session
        session_key = self.resolve_session_key(event)

        # Check if agent is running for this session
        if session_key in self._active_sessions:
            session = self._active_sessions[session_key]
            # Queue message
            future = asyncio.get_event_loop().create_future()
            if session_key not in self._pending_messages:
                self._pending_messages[session_key] = []
            self._pending_messages[session_key].append(PendingMessage(event, future))

            # Interrupt running agent
            session.agent.interrupt()
            try:
                await future
            except asyncio.CancelledError:
                pass
            return

        # Create new agent and process
        await self._process_message(session_key, event)

    async def _process_message(self, session_key: str, event: MessageEvent) -> None:
        """Process a message with a new agent."""
        # Create agent
        agent = create_agent(
            model=self.config.get("model", "openrouter:nvidia/nemotron-3-ultra-550b-a55b:free"),
            provider=self.config.get("provider", "openrouter"),
            max_turns=self.config.get("max_turns", 500),
            profile=self.profile,
            platform=event.platform,
            chat_type=event.chat_type,
            chat_id=event.chat_id,
        )

        # Create session record
        session = GatewaySession(
            session_key=session_key,
            profile=self.profile,
            platform=event.platform,
            chat_type=event.chat_type,
            chat_id=event.chat_id,
            user_id=event.user_id,
            agent=agent,
        )
        self._active_sessions[session_key] = session

        # Fire session start hook
        await self._fire_hook("session:start", session=session, event=event)

        try:
            # Fire agent start hook
            await self._fire_hook("agent:start", session=session, event=event)

            # Run conversation
            result = agent.run_conversation(event.text)

            # Fire agent end hook
            await self._fire_hook("agent:end", session=session, result=result)

            # Send response
            await self._send_reply(event, result)

        except Exception as e:
            await self._send_reply(event, f"❌ Error: {str(e)}")
        finally:
            # Cleanup
            self._active_sessions.pop(session_key, None)

            # Process pending messages
            await self._process_pending(session_key)

            # Fire session end hook
            await self._fire_hook("session:end", session=session)

    async def _process_pending(self, session_key: str) -> None:
        """Process queued messages for a session."""
        pending = self._pending_messages.pop(session_key, [])
        for pending_msg in pending:
            if not pending_msg.future.done():
                pending_msg.future.set_result(None)

    async def _send_reply(self, event: MessageEvent, text: str) -> None:
        """Send reply back through the platform adapter."""
        adapter = self._adapters.get(event.platform)
        if adapter and hasattr(adapter, "send_message"):
            try:
                await adapter.send_message(
                    chat_id=event.chat_id,
                    text=text,
                    reply_to=event.message_id,
                )
            except Exception:
                pass  # Delivery failure logged by adapter

    def set_allowed_users(self, platform: str, user_ids: list[str]) -> None:
        """Set allowed users for a platform."""
        self._allowed_users[platform] = set(user_ids)

    def set_home_channel(self, platform: str, chat_type: str, chat_id: str) -> None:
        """Set home channel for cron deliveries."""
        self._home_channels[platform] = (chat_type, chat_id)

    async def deliver_to_home(self, platform: str, text: str) -> None:
        """Deliver message to home channel."""
        if platform in self._home_channels:
            chat_type, chat_id = self._home_channels[platform]
            adapter = self._adapters.get(platform)
            if adapter and hasattr(adapter, "send_message"):
                await adapter.send_message(chat_id=chat_id, text=text)

    async def start(self) -> None:
        """Start the gateway."""
        self._running = True
        await self._fire_hook("gateway:startup", profile=self.profile)

        # Start all adapters
        for adapter in self._adapters.values():
            if hasattr(adapter, "start"):
                await adapter.start()

    async def stop(self) -> None:
        """Stop the gateway."""
        self._running = False

        # Stop all adapters
        for adapter in self._adapters.values():
            if hasattr(adapter, "stop"):
                await adapter.stop()

        # Interrupt all running agents
        for session in self._active_sessions.values():
            if session.agent:
                session.agent.interrupt()

        await self._fire_hook("gateway:shutdown", profile=self.profile)


# =============================================================================
# Gateway CLI Commands
# =============================================================================


async def gateway_main(profile: str = "default") -> None:
    """Main gateway entry point."""
    runner = GatewayRunner(profile=profile)

    # Load platform adapters

    # Register adapters (configured via environment)
    # TODO: Load from config

    await runner.start()

    try:
        # Keep running
        while True:
            await asyncio.sleep(1)
    except KeyboardInterrupt:
        pass
    finally:
        await runner.stop()


if __name__ == "__main__":
    asyncio.run(gateway_main())
