#!/usr/bin/env python3
"""
DocPixie Textual CLI - Modern terminal interface for document chat
"""

import asyncio
import sys
from pathlib import Path
from typing import List, Optional, Any
from datetime import datetime

from textual import events
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Container, Horizontal, Vertical, ScrollableContainer
from textual.widgets import Header, Footer, Input, Static, Button, Label, ProgressBar, TextArea
from textual.screen import Screen, ModalScreen
from textual.reactive import reactive
from textual.message import Message
from textual.timer import Timer
from rich.markdown import Markdown
from rich.panel import Panel
from rich.text import Text
import pyfiglet

from docpixie import DocPixie, ConversationMessage
from docpixie.core.config import DocPixieConfig
from docpixie.models.document import Document, QueryResult
from docpixie.models.agent import TaskStatus

from .config import get_config_manager
from .conversation_storage import ConversationStorage
from .state_manager import AppStateManager
from .commands import CommandHandler
from .docpixie_manager import DocPixieManager
from .task_display import TaskDisplayManager
from .event_handlers import (
    CommandEventMixin, ConversationEventMixin,
    ModelEventMixin, DocumentEventMixin
)
from .styles import SETUP_SCREEN_CSS, MAIN_APP_CSS
from .widgets import (
    CommandPalette, CommandSelected, CommandAutoComplete,
    ConversationManagerDialog, ConversationSelected, ConversationDeleted,
    ModelSelectorDialog, ModelSelected,
    DocumentManagerDialog, DocumentRemoved, DocumentsIndexed,
    ChatArea
)


class ChatInput(TextArea):
    """Custom TextArea for chat input with Enter to submit"""

    # Override default TextArea bindings with priority
    BINDINGS = [
        # Important: handle Shift+Enter before Enter so newline takes precedence
        Binding("shift+enter", "add_newline", "New line", priority=True),
        # Common terminal fallbacks for newline when Shift+Enter isn't distinct
        Binding("ctrl+j", "add_newline", "New line", priority=True),
        Binding("meta+enter", "add_newline", "New line", priority=True),
        Binding("enter", "submit_message", "Submit", priority=True),
    ]

    def action_submit_message(self) -> None:
        """Submit on Enter"""
        app = self.app
        if hasattr(app, 'submit_chat_message'):
            asyncio.create_task(app.submit_chat_message())

    def action_add_newline(self) -> None:
        """Add a newline on Shift+Enter"""
        self.insert("\n")


class SetupScreen(Screen):
    """First-time setup screen for API key configuration"""

    CSS = SETUP_SCREEN_CSS

    def compose(self) -> ComposeResult:
        with Container(id="setup-container"):
            yield Static("[bold]Welcome to DocPixie![/bold]\n", classes="title")
            yield Static("DocPixie needs an OpenRouter API key to work with documents.\n")
            yield Static("Get your API key from: [link]https://openrouter.ai/keys[/link]\n")
            yield Input(placeholder="Enter your OpenRouter API key...", id="api-input", password=True)
            with Horizontal(id="button-container"):
                yield Button("Save & Continue", variant="primary", id="save-btn")
                yield Button("Exit", variant="error", id="exit-btn")

    async def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "save-btn":
            api_input = self.query_one("#api-input", Input)
            api_key = api_input.value.strip()

            if not api_key:
                api_input.placeholder = "API key cannot be empty!"
                return

            # Save API key
            config_manager = get_config_manager()
            config_manager.set_api_key(api_key)

            # Return to main app
            self.app.pop_screen()
            await self.app.docpixie_manager.initialize_docpixie()

        elif event.button.id == "exit-btn":
            self.app.exit()


class DocPixieTUI(
    App,
    CommandEventMixin,
    ConversationEventMixin,
    ModelEventMixin,
    DocumentEventMixin
):
    """Main DocPixie Terminal UI Application"""

    CSS = MAIN_APP_CSS

    BINDINGS = [
        ("ctrl+q", "quit", "Quit"),
        ("ctrl+n", "new_conversation", "New Conversation"),
        ("ctrl+l", "show_conversations", "Conversations"),
        ("ctrl+o", "show_models", "Model Config"),
        ("ctrl+d", "show_documents", "Documents"),
        ("ctrl+slash", "toggle_palette", "Commands"),
    ]

    def __init__(self):
        super().__init__()
        self.docpixie: Optional[DocPixie] = None
        self.state_manager = AppStateManager()
        self.config_manager = get_config_manager()
        self.command_handler = CommandHandler(self, self.state_manager)
        self.docpixie_manager = DocPixieManager(self, self.state_manager)
        self.task_display_manager = TaskDisplayManager(self, self.state_manager)

    def compose(self) -> ComposeResult:
        """Create the main UI layout"""
        yield Header(show_clock=True)

        with Container(id="chat-container"):
            yield ChatArea(id="chat-log")

            with Horizontal(id="status-bar"):
                yield Label(self.state_manager.get_status_text(), id="status-label")

            with Horizontal(id="input-container"):
                yield Static(">", id="prompt-indicator")
                text_area = ChatInput(
                    "",
                    id="chat-input",
                    language=None,
                    tab_behavior="indent"
                )
                # Set a placeholder-like initial hint
                text_area.show_line_numbers = False
                yield text_area

            # Control hints below the input
            yield Label(self.state_manager.default_input_hint, id="input-hint")


        # Command palette (initially hidden)
        yield CommandPalette(id="command-palette")

        yield Footer()


    async def on_mount(self) -> None:
        """Initialize the app when mounted"""
        # Defer initialization to allow UI to render first
        self.set_timer(0.1, self.deferred_init)
        # Ensure initial keyboard focus is on the chat input
        try:
            self.call_after_refresh(
                lambda: self.query_one("#chat-input", ChatInput).focus()
            )
        except Exception:
            pass

    async def deferred_init(self) -> None:
        """Deferred initialization to allow UI to render"""
        # Check if API key is configured
        if not self.config_manager.has_api_key():
            await self.push_screen(SetupScreen())
        else:
            await self.docpixie_manager.initialize_docpixie()






    def show_welcome_message(self) -> None:
        """Display welcome message and instructions"""
        chat_log = self.query_one("#chat-log", ChatArea)

        from rich.panel import Panel
        from rich.align import Align
        from rich.text import Text

        # Create colorful ASCII art using pyfiglet
        ascii_art = Text()
        figlet_text = pyfiglet.figlet_format("DocPixie CLI", font="big")

        # Define gradient colors (purple → pink)
        colors = [
            "dark_violet", "medium_violet_red", "magenta",
            "orchid", "deep_pink1", "pink1"
        ]

        # Split into lines and apply gradient
        lines = figlet_text.split("\n")
        for line in lines:
            if line.strip():  # Only process non-empty lines
                colored_line = Text()
                chars = list(line)
                for i, char in enumerate(chars):
                    if char != " " and char != "\n":  # Only color non-space characters
                        color_index = (i * (len(colors) - 1)) // max(len(chars) - 1, 1)
                        colored_line.append(char, style=colors[color_index] + " bold")
                    else:
                        colored_line.append(char)
                ascii_art.append(colored_line)
                ascii_art.append("\n")

        # Create welcome content
        welcome_content = Text()
        welcome_content.append("\n")
        welcome_content.append(ascii_art)
        welcome_content.append("\n\n")

        # Status message
        if self.state_manager.indexed_documents:
            welcome_content.append(f"{len(self.state_manager.indexed_documents)} document(s) indexed and ready!\n\n", style="bold green")
        else:
            welcome_content.append("No documents indexed yet\n", style="yellow")
            welcome_content.append("Add PDFs to ./documents and type ", style="dim")
            welcome_content.append("/index", style="bold yellow")
            welcome_content.append(" to get started\n\n", style="dim")

        # Prompt to start
        welcome_content.append("Start chatting with your documents or type ", style="white")
        welcome_content.append("/", style="bold cyan")
        welcome_content.append(" to see all commands", style="white")

        # Create panel with the welcome message
        panel = Panel(
            Align.center(welcome_content),
            title="[bold magenta]DocPixie[/bold magenta]",
            border_style="bright_blue",
            padding=(1, 2),
            expand=False
        )

        chat_log.write(panel)
        chat_log.add_static_text("\n")


    async def submit_chat_message(self) -> None:
        """Submit the chat message from the TextArea"""
        if self.state_manager.command_palette_active:
            # If command palette is active, select the current command instead
            command_palette = self.query_one("#command-palette", CommandPalette)
            selected_command = command_palette.select_current_command()
            if selected_command:
                command_palette.hide()
                self.state_manager.command_palette_active = False
                text_area = self.query_one("#chat-input", ChatInput)
                text_area.clear()
                await self.handle_command(selected_command)
            return

        text_area = self.query_one("#chat-input", ChatInput)
        user_input = text_area.text.strip()

        if user_input:
            # Clear immediately for better UX, then process
            text_area.clear()
            await self.submit_text(user_input)


    async def submit_text(self, user_input: str) -> None:
        """Handle text submission from TextArea"""
        if self.state_manager.processing:
            return

        chat_log = self.query_one("#chat-log", ChatArea)

        if not user_input:
            return

        # Hide command palette if active
        if self.state_manager.command_palette_active:
            command_palette = self.query_one("#command-palette", CommandPalette)
            command_palette.hide()
            self.state_manager.command_palette_active = False

        # Check for commands
        if user_input.startswith("/"):
            await self.handle_command(user_input.lower())
            return

        # Display user message using ChatArea method
        chat_log.add_user_message(user_input)

        # Disable input while processing, then re-enable after
        self.set_chat_input_enabled(False)
        try:
            # Create task update callback for DocPixie processing
            async def task_callback(event_type: str, data: Any):
                def _update():
                    try:
                        self.task_display_manager.display_task_update(event_type, data)
                    except Exception:
                        pass
                try:
                    self.call_from_thread(_update)
                except Exception:
                    _update()

            await self.docpixie_manager.process_query(user_input, task_callback)
        finally:
            self.set_chat_input_enabled(True)

    def set_chat_input_enabled(self, enabled: bool) -> None:
        """Enable or disable the chat input and update hint text."""
        try:
            text_area = self.query_one("#chat-input", ChatInput)
            hint = self.query_one("#input-hint", Label)
        except Exception:
            return

        # Toggle disabled state
        try:
            text_area.disabled = not enabled
        except Exception:
            # Fallback if widget doesn't support disabled for some reason
            pass

        # Update hint text to reflect state
        if enabled:
            hint.update(self.state_manager.default_input_hint)
            # Return keyboard focus to the chat input after processing completes
            try:
                self.call_after_refresh(lambda: text_area.focus())
            except Exception:
                try:
                    text_area.focus()
                except Exception:
                    pass
        else:
            hint.update("⏳ Agent is working… input disabled until response.")








    async def handle_command(self, command: str) -> None:
        """Handle slash commands"""
        await self.command_handler.handle_command(command)



    def action_quit(self) -> None:
        """Quit the application"""
        self.exit()

    def action_new_conversation(self) -> None:
        """Start a new conversation"""
        asyncio.create_task(self.handle_command("/new"))

    def action_show_conversations(self) -> None:
        """Show conversation list"""
        asyncio.create_task(self.handle_command("/conversations"))

    def action_show_models(self) -> None:
        """Show model selector"""
        asyncio.create_task(self.handle_command("/model"))

    def action_show_documents(self) -> None:
        """Show document manager"""
        asyncio.create_task(self.handle_command("/documents"))

    def action_toggle_palette(self) -> None:
        """Toggle command palette"""
        if self.state_manager.processing:
            return
        command_palette = self.query_one("#command-palette", CommandPalette)
        text_area = self.query_one("#chat-input", ChatInput)

        if self.state_manager.command_palette_active:
            command_palette.hide()
            self.state_manager.command_palette_active = False
        else:
            command_palette.show("/")
            self.state_manager.command_palette_active = True
            text_area.text = "/"
            text_area.cursor_location = (0, 1)


def main():
    """Main entry point for Textual CLI"""
    app = DocPixieTUI()
    app.run()


if __name__ == "__main__":
    main()
