#!/usr/bin/env python3
"""
Enaya Agent - Slack Adapter
Slack bot integration for the gateway.
"""

from __future__ import annotations

import os
from typing import Any, Optional

from slack_bolt.async_app import AsyncApp
from slack_bolt.adapter.socket_mode.async_handler import AsyncSocketModeHandler

from enaya.gateway.runner import GatewayRunner, MessageEvent


class SlackAdapter:
    """Slack bot adapter for the gateway."""
    
    def __init__(self, runner: GatewayRunner):
        self.runner = runner
        self.bot_token = os.environ.get("SLACK_BOT_TOKEN")
        self.app_token = os.environ.get("SLACK_APP_TOKEN")
        self.allowed_users = set(
            os.environ.get("SLACK_ALLOWED_USERS", "").split(",")
        ) if os.environ.get("SLACK_ALLOWED_USERS") else set()
        self.allow_all = os.environ.get("SLACK_ALLOW_ALL_USERS", "false").lower() == "true"
        
        self.app: Optional[AsyncApp] = None
        self.handler: Optional[AsyncSocketModeHandler] = None
        self._running = False
    
    async def start(self) -> None:
        """Start the Slack bot."""
        if not self.bot_token or not self.app_token:
            print("SLACK_BOT_TOKEN or SLACK_APP_TOKEN not set, skipping Slack adapter")
            return
        
        self.app = AsyncApp(token=self.bot_token)
        
        # Event handlers
        self.app.event("message")(self._handle_message)
        self.app.event("app_mention")(self._handle_mention)
        
        # Commands
        self.app.command("/help")(self._cmd_help)
        self.app.command("/delegate")(self._cmd_delegate)
        self.app.command("/model")(self._cmd_model)
        self.app.command("/new")(self._cmd_new)
        self.app.command("/status")(self._cmd_status)
        
        # Start handler
        self.handler = AsyncSocketModeHandler(self.app, self.app_token)
        await self.handler.connect_async()
        
        self._running = True
        print("Slack adapter started")
    
    async def stop(self) -> None:
        """Stop the Slack bot."""
        if self.handler:
            await self.handler.close_async()
        self._running = False
        print("Slack adapter stopped")
    
    def authorize_user(self, user_id: str) -> bool:
        """Check if user is authorized."""
        if self.allow_all:
            return True
        return user_id in self.allowed_users
    
    async def _handle_message(self, body: dict, say: callable) -> None:
        """Handle incoming message."""
        event = body.get("event", {})
        
        # Skip bot messages
        if event.get("bot_id"):
            return
        
        user_id = event.get("user")
        
        # Check authorization
        if not self.authorize_user(user_id):
            await say(text="❌ You are not authorized to use this bot.")
            return
        
        # Skip if it's a mention (handled separately)
        if event.get("subtype") == "bot_message":
            return
        
        # Create message event
        chat_type = "dm" if event.get("channel_type") == "im" else "group"
        chat_id = event.get("channel")
        
        msg_event = MessageEvent(
            platform="slack",
            chat_type=chat_type,
            chat_id=chat_id,
            user_id=user_id,
            username=event.get("username", ""),
            text=event.get("text", ""),
            message_id=event.get("ts", ""),
            raw=event,
        )
        
        # Process through gateway
        await self.runner.handle_message(msg_event)
    
    async def _handle_mention(self, body: dict, say: callable) -> None:
        """Handle @mention."""
        await self._handle_message(body, say)
    
    # Commands
    async def _cmd_help(self, ack: callable, say: callable) -> None:
        await ack()
        await say(text=(
            "👋 *Enaya Agent Commands*\n\n"
            "*/help* - Show this help\n"
            "*/delegate <task>* - Delegate a complex task to a subagent\n"
            "*/model* - Show current model\n"
            "*/new* - Start new session\n"
            "*/status* - Show session status"
        ))
    
    async def _cmd_delegate(self, ack: callable, say: callable, command: dict) -> None:
        await ack()
        task = command.get("text", "").strip()
        if not task:
            await say(text="Usage: `/delegate <task description>`")
            return
        
        user_id = command.get("user_id")
        chat_type = "dm" if command.get("channel_type") == "im" else "group"
        chat_id = command.get("channel_id")
        
        msg_event = MessageEvent(
            platform="slack",
            chat_type=chat_type,
            chat_id=chat_id,
            user_id=user_id,
            username=command.get("user_name", ""),
            text=f"[DELEGATED TASK]\n{task}",
            message_id=command.get("trigger_id", ""),
        )
        
        await self.runner.handle_message(msg_event)
    
    async def _cmd_model(self, ack: callable, say: callable) -> None:
        await ack()
        await say(text="Model info: (TODO)")
    
    async def _cmd_new(self, ack: callable, say: callable) -> None:
        await ack()
        await say(text="🔄 New session started!")
    
    async def _cmd_status(self, ack: callable, say: callable) -> None:
        await ack()
        await say(text="Status: (TODO)")
    
    async def send_message(self, chat_id: str, text: str, reply_to: Optional[str] = None) -> None:
        """Send a message to a channel."""
        if self.app:
            try:
                await self.app.client.chat_postMessage(
                    channel=chat_id,
                    text=text,
                    thread_ts=reply_to,
                )
            except Exception as e:
                print(f"Failed to send Slack message: {e}")


def setup_slack(runner: GatewayRunner) -> Optional[SlackAdapter]:
    """Set up Slack adapter if configured."""
    bot_token = os.environ.get("SLACK_BOT_TOKEN")
    app_token = os.environ.get("SLACK_APP_TOKEN")
    if not bot_token or not app_token:
        return None
    
    adapter = SlackAdapter(runner)
    runner.register_adapter("slack", adapter)
    return adapter