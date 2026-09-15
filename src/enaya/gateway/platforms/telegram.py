#!/usr/bin/env python3
"""
Enaya Agent - Telegram Adapter
Telegram bot integration for the gateway.
"""

from __future__ import annotations

import asyncio
import os
from typing import Any, Optional

from telegram import Update
from telegram.ext import Application, MessageHandler, filters, ContextTypes

from enaya.gateway.runner import GatewayRunner, MessageEvent


class TelegramAdapter:
    """Telegram bot adapter for the gateway."""
    
    def __init__(self, runner: GatewayRunner):
        self.runner = runner
        self.bot_token = os.environ.get("TELEGRAM_BOT_TOKEN")
        self.allowed_users = set(
            os.environ.get("TELEGRAM_ALLOWED_USERS", "").split(",")
        ) if os.environ.get("TELEGRAM_ALLOWED_USERS") else set()
        self.allow_all = os.environ.get("TELEGRAM_ALLOW_ALL_USERS", "false").lower() == "true"
        
        self.app: Optional[Application] = None
        self._running = False
    
    async def start(self) -> None:
        """Start the Telegram bot."""
        if not self.bot_token:
            print("TELEGRAM_BOT_TOKEN not set, skipping Telegram adapter")
            return
        
        self.app = Application.builder().token(self.bot_token).build()
        
        # Add handlers
        self.app.add_handler(
            MessageHandler(filters.TEXT & ~filters.COMMAND, self._handle_message)
        )
        self.app.add_handler(
            MessageHandler(filters.COMMAND, self._handle_command)
        )
        
        # Initialize and start
        await self.app.initialize()
        await self.app.start()
        await self.app.updater.start_polling()
        
        self._running = True
        print("Telegram adapter started")
    
    async def stop(self) -> None:
        """Stop the Telegram bot."""
        if self.app:
            await self.app.updater.stop()
            await self.app.stop()
            await self.app.shutdown()
        self._running = False
        print("Telegram adapter stopped")
    
    def authorize_user(self, user_id: str) -> bool:
        """Check if user is authorized."""
        if self.allow_all:
            return True
        return str(user_id) in self.allowed_users
    
    async def _handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle incoming text message."""
        if not update.message or not update.message.text:
            return
        
        user_id = str(update.effective_user.id)
        
        # Check authorization
        if not self.authorize_user(user_id):
            await update.message.reply_text("❌ You are not authorized to use this bot.")
            return
        
        # Create message event
        event = MessageEvent(
            platform="telegram",
            chat_type="private" if update.message.chat.type == "private" else "group",
            chat_id=str(update.message.chat_id),
            user_id=user_id,
            username=update.effective_user.username,
            text=update.message.text,
            message_id=str(update.message.message_id),
            raw=update.to_dict(),
        )
        
        # Process through gateway
        await self.runner.handle_message(event)
    
    async def _handle_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle slash commands."""
        if not update.message or not update.message.text:
            return
        
        command = update.message.text.split()[0].lower()
        user_id = str(update.effective_user.id)
        
        if command == "/start":
            await update.message.reply_text(
                "👋 Welcome to Enaya Agent!\n\n"
                "I'm a task-delegation AI agent with multi-agent orchestration.\n"
                "Just send me a message to chat, or use /delegate for complex tasks."
            )
        elif command == "/help":
            await update.message.reply_text(
                "📚 Enaya Agent Commands:\n\n"
                "/start - Welcome message\n"
                "/help - This help\n"
                "/delegate <task> - Delegate a complex task to a subagent\n"
                "/model - Show current model\n"
                "/new - Start new session\n"
                "/status - Show session status"
            )
        elif command == "/delegate":
            task = update.message.text[len("/delegate"):].strip()
            if not task:
                await update.message.reply_text("Usage: /delegate <task description>")
                return
            
            # Create delegation event
            event = MessageEvent(
                platform="telegram",
                chat_type="private" if update.message.chat.type == "private" else "group",
                chat_id=str(update.message.chat_id),
                user_id=user_id,
                username=update.effective_user.username,
                text=f"[DELEGATED TASK]\n{task}",
                message_id=str(update.message.message_id),
            )
            
            await self.runner.handle_message(event)
        elif command == "/model":
            # Get current model from runner config
            await update.message.reply_text("Model info: (TODO)")
        elif command == "/new":
            # New session would reset the conversation
            await update.message.reply_text("🔄 New session started!")
        elif command == "/status":
            await update.message.reply_text("Status: (TODO)")
    
    async def send_message(self, chat_id: str, text: str, reply_to: Optional[str] = None) -> None:
        """Send a message to a chat."""
        if self.app and self.app.bot:
            try:
                await self.app.bot.send_message(
                    chat_id=chat_id,
                    text=text,
                    reply_to_message_id=int(reply_to) if reply_to else None,
                    parse_mode="Markdown",
                )
            except Exception as e:
                print(f"Failed to send Telegram message: {e}")


# =============================================================================
# Register with runner
# =============================================================================

def setup_telegram(runner: GatewayRunner) -> Optional[TelegramAdapter]:
    """Set up Telegram adapter if configured."""
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    if not token:
        return None
    
    adapter = TelegramAdapter(runner)
    runner.register_adapter("telegram", adapter)
    return adapter