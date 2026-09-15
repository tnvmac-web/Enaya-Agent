#!/usr/bin/env python3
"""
Enaya Agent - Discord Adapter
Discord bot integration for the gateway.
"""

from __future__ import annotations

import asyncio
import os
from typing import Any, Optional

import discord
from discord.ext import commands

from enaya.gateway.runner import GatewayRunner, MessageEvent


class DiscordAdapter:
    """Discord bot adapter for the gateway."""
    
    def __init__(self, runner: GatewayRunner):
        self.runner = runner
        self.bot_token = os.environ.get("DISCORD_BOT_TOKEN")
        self.allowed_users = set(
            os.environ.get("DISCORD_ALLOWED_USERS", "").split(",")
        ) if os.environ.get("DISCORD_ALLOWED_USERS") else set()
        self.allow_all = os.environ.get("DISCORD_ALLOW_ALL_USERS", "false").lower() == "true"
        
        self.bot: Optional[commands.Bot] = None
        self._running = False
    
    async def start(self) -> None:
        """Start the Discord bot."""
        if not self.bot_token:
            print("DISCORD_BOT_TOKEN not set, skipping Discord adapter")
            return
        
        intents = discord.Intents.default()
        intents.message_content = True
        intents.messages = True
        intents.guilds = True
        intents.dm_messages = True
        
        self.bot = commands.Bot(command_prefix="/", intents=intents)
        
        # Event handlers
        self.bot.event(self._on_ready)
        self.bot.event(self._on_message)
        
        # Commands
        self.bot.command()(self._cmd_help)
        self.bot.command()(self._cmd_delegate)
        self.bot.command()(self._cmd_model)
        self.bot.command()(self._cmd_new)
        self.bot.command()(self._cmd_status)
        
        # Start bot
        await self.bot.start(self.bot_token)
        self._running = True
        print("Discord adapter started")
    
    async def stop(self) -> None:
        """Stop the Discord bot."""
        if self.bot:
            await self.bot.close()
        self._running = False
        print("Discord adapter stopped")
    
    def authorize_user(self, user_id: str) -> bool:
        """Check if user is authorized."""
        if self.allow_all:
            return True
        return str(user_id) in self.allowed_users
    
    async def _on_ready(self) -> None:
        """Bot ready event."""
        print(f"Discord bot logged in as {self.bot.user}")
    
    async def _on_message(self, message: discord.Message) -> None:
        """Handle incoming message."""
        # Ignore bot's own messages
        if message.author.bot:
            return
        
        user_id = str(message.author.id)
        
        # Check authorization
        if not self.authorize_user(user_id):
            await message.reply("❌ You are not authorized to use this bot.")
            return
        
        # Skip commands (they're handled by command processor)
        if message.content.startswith("/"):
            return
        
        # Create message event
        chat_type = "dm" if isinstance(message.channel, discord.DMChannel) else "group"
        chat_id = str(message.channel.id)
        
        event = MessageEvent(
            platform="discord",
            chat_type=chat_type,
            chat_id=chat_id,
            user_id=user_id,
            username=str(message.author),
            text=message.content,
            message_id=str(message.id),
            raw={
                "guild_id": str(message.guild.id) if message.guild else None,
                "channel_id": str(message.channel.id),
            },
        )
        
        # Process through gateway
        await self.runner.handle_message(event)
    
    # Commands
    async def _cmd_help(self, ctx: commands.Context) -> None:
        """Help command."""
        embed = discord.Embed(
            title="Enaya Agent Commands",
            description="Task-delegation AI agent with multi-agent orchestration",
            color=0x00D4AA,
        )
        embed.add_field(name="/help", value="Show this help", inline=False)
        embed.add_field(name="/delegate <task>", value="Delegate a complex task to a subagent", inline=False)
        embed.add_field(name="/model", value="Show current model", inline=False)
        embed.add_field(name="/new", value="Start new session", inline=False)
        embed.add_field(name="/status", value="Show session status", inline=False)
        await ctx.send(embed=embed)
    
    async def _cmd_delegate(self, ctx: commands.Context, *, task: str) -> None:
        """Delegate a task to a subagent."""
        if not task:
            await ctx.send("Usage: /delegate <task description>")
            return
        
        user_id = str(ctx.author.id)
        chat_type = "dm" if isinstance(ctx.channel, discord.DMChannel) else "group"
        chat_id = str(ctx.channel.id)
        
        event = MessageEvent(
            platform="discord",
            chat_type=chat_type,
            chat_id=chat_id,
            user_id=user_id,
            username=str(ctx.author),
            text=f"[DELEGATED TASK]\n{task}",
            message_id=str(ctx.message.id),
        )
        
        await self.runner.handle_message(event)
    
    async def _cmd_model(self, ctx: commands.Context) -> None:
        """Show current model."""
        await ctx.send("Model info: (TODO)")
    
    async def _cmd_new(self, ctx: commands.Context) -> None:
        """Start new session."""
        await ctx.send("🔄 New session started!")
    
    async def _cmd_status(self, ctx: commands.Context) -> None:
        """Show session status."""
        await ctx.send("Status: (TODO)")
    
    async def send_message(self, chat_id: str, text: str, reply_to: Optional[str] = None) -> None:
        """Send a message to a channel."""
        if self.bot:
            try:
                channel = self.bot.get_channel(int(chat_id))
                if channel:
                    kwargs = {}
                    if reply_to:
                        kwargs["reference"] = discord.MessageReference(message_id=int(reply_to))
                    await channel.send(text, **kwargs)
            except Exception as e:
                print(f"Failed to send Discord message: {e}")


def setup_discord(runner: GatewayRunner) -> Optional[DiscordAdapter]:
    """Set up Discord adapter if configured."""
    token = os.environ.get("DISCORD_BOT_TOKEN")
    if not token:
        return None
    
    adapter = DiscordAdapter(runner)
    runner.register_adapter("discord", adapter)
    return adapter