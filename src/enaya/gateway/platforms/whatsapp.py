#!/usr/bin/env python3
"""
Enaya Agent - WhatsApp Adapter
WhatsApp bot integration for the gateway.
"""

from __future__ import annotations

import asyncio
import os
from typing import Any, Optional

from enaya.gateway.runner import GatewayRunner, MessageEvent


class WhatsAppAdapter:
    """WhatsApp bot adapter for the gateway using Baileys/whiskey."""
    
    def __init__(self, runner: GatewayRunner):
        self.runner = runner
        self.phone_number = os.environ.get("WHATSAPP_PHONE_NUMBER")
        self.session_path = os.environ.get("WHATSAPP_SESSION_PATH", "./whatsapp_session")
        self.allowed_users = set(
            os.environ.get("WHATSAPP_ALLOWED_USERS", "").split(",")
        ) if os.environ.get("WHATSAPP_ALLOWED_USERS") else set()
        self.allow_all = os.environ.get("WHATSAPP_ALLOW_ALL_USERS", "false").lower() == "true"
        
        self._socket = None
        self._running = False
    
    async def start(self) -> None:
        """Start the WhatsApp connection."""
        print("WhatsApp adapter: Using Baileys/whiskey would require Node.js bridge")
        print("WhatsApp adapter: For now, this is a placeholder implementation")
        self._running = True
    
    async def stop(self) -> None:
        """Stop the WhatsApp connection."""
        self._running = False
        print("WhatsApp adapter stopped")
    
    def authorize_user(self, user_id: str) -> bool:
        """Check if user is authorized."""
        if self.allow_all:
            return True
        return user_id in self.allowed_users
    
    async def _handle_message(self, message: dict) -> None:
        """Handle incoming message."""
        user_id = message.get("from", "").split("@")[0]
        
        if not self.authorize_user(user_id):
            await self.send_message(message.get("from"), "❌ You are not authorized to use this bot.")
            return
        
        # Create message event
        msg_event = MessageEvent(
            platform="whatsapp",
            chat_type="dm" if message.get("is_group") == False else "group",
            chat_id=message.get("from", ""),
            user_id=user_id,
            username=message.get("notify_name", ""),
            text=message.get("body", ""),
            message_id=message.get("id", ""),
            raw=message,
        )
        
        # Process through gateway
        await self.runner.handle_message(msg_event)
    
    async def send_message(self, chat_id: str, text: str, reply_to: Optional[str] = None) -> None:
        """Send a message to a chat."""
        # This would use the Baileys socket to send messages
        # Placeholder for now
        print(f"WhatsApp send to {chat_id}: {text}")


def setup_whatsapp(runner: GatewayRunner) -> None:
    """Set up WhatsApp adapter if configured."""
    phone = os.environ.get("WHATSAPP_PHONE_NUMBER")
    if not phone:
        return
    
    adapter = WhatsAppAdapter(runner)
    runner.register_adapter("whatsapp", adapter)