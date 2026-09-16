#!/usr/bin/env python3
"""
Enaya Agent - Matrix Adapter
Matrix bot integration for the gateway.
"""

from __future__ import annotations

import asyncio
import os

from matrix_nio import AsyncClient, MatrixRoom, RoomMessageText

from enaya.gateway.runner import GatewayRunner, MessageEvent


class MatrixAdapter:
    """Matrix bot adapter for the gateway."""

    def __init__(self, runner: GatewayRunner):
        self.runner = runner
        self.homeserver = os.environ.get("MATRIX_HOMESERVER", "https://matrix.org")
        self.user_id = os.environ.get("MATRIX_USER_ID")
        self.access_token = os.environ.get("MATRIX_ACCESS_TOKEN")
        self.allowed_users = (
            set(os.environ.get("MATRIX_ALLOWED_USERS", "").split(","))
            if os.environ.get("MATRIX_ALLOWED_USERS")
            else set()
        )
        self.allow_all = os.environ.get("MATRIX_ALLOW_ALL_USERS", "false").lower() == "true"

        self.client: AsyncClient | None = None
        self._running = False

    async def start(self) -> None:
        """Start the Matrix client."""
        if not self.user_id or not self.access_token:
            print("MATRIX_USER_ID or MATRIX_ACCESS_TOKEN not set, skipping Matrix adapter")
            return

        self.client = AsyncClient(
            homeserver=self.homeserver,
            user=self.user_id,
        )
        self.client.access_token = self.access_token
        self.client.user_id = self.user_id

        # Add event callback
        self.client.add_event_callback(self._on_message, RoomMessageText)

        # Start sync
        asyncio.create_task(self.client.sync_forever(timeout=30000))

        self._running = True
        print("Matrix adapter started")

    async def stop(self) -> None:
        """Stop the Matrix client."""
        if self.client:
            await self.client.close()
        self._running = False
        print("Matrix adapter stopped")

    def authorize_user(self, user_id: str) -> bool:
        """Check if user is authorized."""
        if self.allow_all:
            return True
        return user_id in self.allowed_users

    async def _on_message(self, room: MatrixRoom, event: RoomMessageText) -> None:
        """Handle incoming message."""
        # Skip own messages
        if event.sender == self.user_id:
            return

        # Check authorization
        if not self.authorize_user(event.sender):
            await self.send_message(room.room_id, "❌ You are not authorized to use this bot.")
            return

        # Create message event
        msg_event = MessageEvent(
            platform="matrix",
            chat_type="dm" if room.is_direct else "group",
            chat_id=room.room_id,
            user_id=event.sender,
            username=event.sender,
            text=event.body,
            message_id=event.event_id,
            raw={
                "room_id": room.room_id,
                "room_name": room.display_name,
            },
        )

        # Process through gateway
        await self.runner.handle_message(msg_event)

    async def send_message(self, chat_id: str, text: str, reply_to: str | None = None) -> None:
        """Send a message to a room."""
        if self.client:
            try:
                content = {
                    "msgtype": "m.text",
                    "body": text,
                }
                if reply_to:
                    content["m.relates_to"] = {"m.in_reply_to": {"event_id": reply_to}}
                await self.client.room_send(
                    room_id=chat_id,
                    message_type="m.room.message",
                    content=content,
                )
            except Exception as e:
                print(f"Failed to send Matrix message: {e}")


def setup_matrix(runner: GatewayRunner) -> MatrixAdapter | None:
    """Set up Matrix adapter if configured."""
    user_id = os.environ.get("MATRIX_USER_ID")
    access_token = os.environ.get("MATRIX_ACCESS_TOKEN")
    if not user_id or not access_token:
        return None

    adapter = MatrixAdapter(runner)
    runner.register_adapter("matrix", adapter)
    return adapter
