#!/usr/bin/env python3
"""
Enaya Agent - TUI (Ink Terminal UI)
Textual-based terminal UI with mouse support, streaming output, widgets.
"""

from __future__ import annotations

import asyncio

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Container, Vertical
from textual.message import Message
from textual.widgets import (
    DataTable,
    Footer,
    Header,
    Input,
    Label,
    RichLog,
    Static,
)

from enaya.cli.config import load_config
from enaya.run_agent import AIAgent, create_agent


class ChatMessage(Message):
    """Message for chat updates."""

    def __init__(self, role: str, content: str, streaming: bool = False):
        self.role = role
        self.content = content
        self.streaming = streaming
        super().__init__()


class EnayaTUI(App):
    """Enaya Agent TUI - Textual-based terminal interface."""

    CSS = """
    Screen {
        layout: vertical;
    }
    #main-container {
        layout: horizontal;
        height: 1fr;
    }
    #sidebar {
        width: 30;
        border-right: solid $primary;
        padding: 1;
    }
    #chat-area {
        width: 1fr;
        layout: vertical;
    }
    #chat-log {
        height: 1fr;
        border: solid $primary;
        padding: 1;
        overflow-y: auto;
    }
    #input-area {
        height: auto;
        min-height: 5;
        border: solid $primary;
        padding: 1;
    }
    #input-field {
        width: 1fr;
    }
    #session-list {
        height: 1fr;
    }
    .user-message {
        color: $accent;
        margin-bottom: 1;
    }
    .assistant-message {
        color: $text;
        margin-bottom: 1;
    }
    .system-message {
        color: $warning;
        margin-bottom: 1;
    }
    .streaming {
        opacity: 0.8;
    }
    #status-bar {
        height: 1;
        background: $surface;
        color: $text-muted;
        padding: 0 1;
    }
    """

    BINDINGS = [
        Binding("ctrl+q", "quit", "Quit"),
        Binding("ctrl+n", "new_session", "New Session"),
        Binding("ctrl+s", "save_session", "Save Session"),
        Binding("ctrl+l", "clear_chat", "Clear Chat"),
        Binding("ctrl+p", "command_palette", "Command Palette"),
        Binding("ctrl+t", "toggle_sidebar", "Toggle Sidebar"),
    ]

    def __init__(self):
        super().__init__()
        self.agent: AIAgent | None = None
        self.current_session_id: str | None = None
        self.streaming_buffer = ""
        self.streaming_active = False

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        with Container(id="main-container"):
            with Vertical(id="sidebar"):
                yield Label("Sessions", classes="section-title")
                yield DataTable(id="session-list", cursor_type="row")
            with Vertical(id="chat-area"):
                yield RichLog(id="chat-log", markup=True, highlight=True, wrap=True)
                with Container(id="input-area"):
                    yield Input(
                        placeholder="Type your message... (Ctrl+Enter to send)", id="input-field"
                    )
        yield Footer()
        yield Static("", id="status-bar")

    def on_mount(self) -> None:
        """Initialize the TUI."""
        self.title = "Enaya Agent"
        self.sub_title = "Task-delegation AI agent"

        # Load configuration
        config = load_config("default")

        # Create agent
        self.agent = create_agent(
            model=config.get("model", "openrouter:nvidia/nemotron-3-ultra-550b-a55b:free"),
            provider=config.get("provider", "openrouter"),
        )

        # Setup session table
        session_table = self.query_one("#session-list", DataTable)
        session_table.add_columns("Session", "Messages", "Model")
        session_table.add_row("New Session", "0", self.agent.model[:30])

        # Focus input
        self.query_one("#input-field", Input).focus()

        # Update status
        self.update_status(f"Model: {self.agent.model} | Provider: {self.agent.provider}")

    def update_status(self, message: str) -> None:
        """Update status bar."""
        self.query_one("#status-bar", Static).update(message)

    def on_input_submitted(self, event: Input.Submitted) -> None:
        """Handle user input submission."""
        if event.value.strip():
            self.send_message(event.value.strip())
            event.input.value = ""

    def send_message(self, content: str) -> None:
        """Send a message to the agent."""
        chat_log = self.query_one("#chat-log", RichLog)

        # Add user message
        chat_log.write(f"[bold cyan]You:[/bold cyan] {content}")

        # Run agent in background
        self.streaming_active = True
        self.streaming_buffer = ""

        asyncio.create_task(self._run_agent_async(content))

    async def _run_agent_async(self, content: str) -> None:
        """Run agent conversation asynchronously."""
        try:
            # Run in thread pool to avoid blocking UI
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(None, lambda: self.agent.run_conversation(content))

            # Update UI with result
            self.call_from_thread(self._on_agent_result, result)

        except Exception as e:
            self.call_from_thread(self._on_agent_error, str(e))

    def _on_agent_result(self, result: str) -> None:
        """Handle agent result."""
        chat_log = self.query_one("#chat-log", RichLog)
        chat_log.write(f"[bold green]Enaya:[/bold green] {result}")
        self.streaming_active = False
        self.update_status("Ready")

    def _on_agent_error(self, error: str) -> None:
        """Handle agent error."""
        chat_log = self.query_one("#chat-log", RichLog)
        chat_log.write(f"[bold red]Error:[/bold red] {error}")
        self.streaming_active = False
        self.update_status("Error")

    def action_new_session(self) -> None:
        """Start a new session."""
        self.current_session_id = None
        self.agent.session_id = None
        self.agent.conversation_history = []
        chat_log = self.query_one("#chat-log", RichLog)
        chat_log.clear()
        chat_log.write("[dim]New session started[/dim]")
        self.update_status("New session started")

    def action_clear_chat(self) -> None:
        """Clear chat display."""
        chat_log = self.query_one("#chat-log", RichLog)
        chat_log.clear()

    def action_toggle_sidebar(self) -> None:
        """Toggle sidebar visibility."""
        sidebar = self.query_one("#sidebar", Vertical)
        sidebar.display = not sidebar.display

    def action_command_palette(self) -> None:
        """Show command palette."""
        # TODO: Implement command palette
        self.update_status("Command palette: not yet implemented")


def run_tui():
    """Run the TUI application."""
    app = EnayaTUI()
    app.run()


if __name__ == "__main__":
    run_tui()
