#!/usr/bin/env python3
"""
Enaya Agent - Signal Adapter
Signal bot integration for the gateway using signal-cli.
"""

from __future__ import annotations

import asyncio
import json
import os
import subprocess

from enaya.gateway.runner import GatewayRunner, MessageEvent


class SignalAdapter:
    """Signal bot adapter for the gateway using signal-cli."""

    def __init__(self, runner: GatewayRunner):
        self.runner = runner
        self.phone_number = os.environ.get("SIGNAL_PHONE_NUMBER")
        self.allowed_users = (
            set(os.environ.get("SIGNAL_ALLOWED_USERS", "").split(","))
            if os.environ.get("SIGNAL_ALLOWED_USERS")
            else set()
        )
        self.allow_all = os.environ.get("SIGNAL_ALLOW_ALL_USERS", "false").lower() == "true"

        self._process = None
        self._running = False

    async def start(self) -> None:
        """Start the Signal bot using signal-cli."""
        if not self.phone_number:
            print("SIGNAL_PHONE_NUMBER not set, skipping Signal adapter")
            return

        # Check if signal-cli is available
        try:
            result = subprocess.run(["signal-cli", "--version"], capture_output=True, timeout=5)
            if result.returncode != 0:
                print("signal-cli not found, skipping Signal adapter")
                return
        except FileNotFoundError:
            print("signal-cli not installed, skipping Signal adapter")
            return

        # Start signal-cli daemon
        self._process = subprocess.Popen(
            [
                "signal-cli",
                "-u",
                self.phone_number,
                "daemon",
                "--json",
            ],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )

        self._running = True

        # Start reading messages
        asyncio.create_task(self._read_messages())

        print(f"Signal adapter started for {self.phone_number}")

    async def stop(self) -> None:
        """Stop the Signal bot."""
        self._running = False
        if self._process:
            self._process.terminate()
            try:
                await asyncio.wait_for(self._process.wait(), timeout=5)
            except TimeoutError:
                self._process.kill()
        print("Signal adapter stopped")

    def authorize_user(self, user_id: str) -> bool:
        """Check if user is authorized."""
        if self.allow_all:
            return True
        return user_id in self.allowed_users

    async def _read_messages(self) -> None:
        """Read messages from signal-cli stdout."""
        while self._running and self._process and self._process.stdout:
            try:
                line = await asyncio.get_event_loop().run_in_executor(
                    None, self._process.stdout.readline
                )
                if not line:
                    break

                line = line.strip()
                if not line:
                    continue

                try:
                    data = json.loads(line)
                    await self._handle_envelope(data)
                except json.JSONDecodeError:
                    continue

            except Exception as e:
                print(f"Signal read error: {e}")
                await asyncio.sleep(1)

    async def _handle_envelope(self, envelope: dict) -> None:
        """Handle incoming signal envelope."""
        if "envelope" not in envelope:
            return

        env = envelope["envelope"]

        # Handle data messages
        if "dataMessage" in env:
            msg = env["dataMessage"]
            source = env["source"]
            source_number = source.get("number", "")

            if not self.authorize_user(source_number):
                # Send rejection
                await self.send_message(source_number, "❌ You are not authorized to use this bot.")
                return

            # Create message event
            msg_event = MessageEvent(
                platform="signal",
                chat_type="group" if env.get("groupInfo") else "dm",
                chat_id=env.get("groupInfo", {}).get("groupId", source_number),
                user_id=source_number,
                username=source.get("name", ""),
                text=msg.get("message", ""),
                message_id=env.get("timestamp", ""),
                raw=envelope,
            )

            # Process through gateway
            await self.runner.handle_message(msg_event)

    async def send_message(self, to_number: str, text: str, reply_to: str | None = None) -> None:
        """Send a message via signal-cli."""
        try:
            cmd = [
                "signal-cli",
                "-u",
                self.phone_number,
                "send",
                "-m",
                text,
                to_number,
            ]

            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            await proc.communicate()

        except Exception as e:
            print(f"Failed to send Signal message: {e}")


def setup_signal(runner: GatewayRunner) -> None:
    """Set up Signal adapter if configured."""
    phone = os.environ.get("SIGNAL_PHONE_NUMBER")
    if not phone:
        return

    adapter = SignalAdapter(runner)
    runner.register_adapter("signal", adapter)
