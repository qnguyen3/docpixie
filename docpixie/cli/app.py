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

from docpixie import DocPixie, ConversationMessage
from docpixie.core.config import DocPixieConfig
from docpixie.models.document import Document, QueryResult
from docpixie.models.agent import TaskStatus

from .config import get_config_manager
from .conversation_storage import ConversationStorage
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

    CSS = """
    SetupScreen {
        align: center middle;
    }

    #setup-container {
        width: 80;
        height: auto;
        padding: 2;
        border: solid $primary;
    }

    #api-input {
        margin: 1 0;
    }

    #button-container {
        align: center middle;
        margin-top: 1;
    }
    """

    def compose(self) -> ComposeResult:
        with Container(id="setup-container"):
            yield Static("[bold]🧚 Welcome to DocPixie![/bold]\n", classes="title")
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
            await self.app.initialize_docpixie()

        elif event.button.id == "exit-btn":
            self.app.exit()


class DocPixieTUI(App):
    """Main DocPixie Terminal UI Application"""

    CSS = """
    #chat-container {
        height: 100%;
        layout: vertical;
        background: #2d1f2d;
        padding: 0 1 1 1;
    }

    #chat-log {
        border: solid #4a3344;
        background: #2d1f2d;
    }

    #input-container {
        height: auto;
        min-height: 3;
        max-height: 12;
        padding: 0 0 0 1;
        margin: 0;
        background: #2d1f2d;
        border: solid #ff99cc;
    }

    #prompt-indicator {
        width: 2;
        color: #ff99cc;
        padding: 0;
        background: #2d1f2d;
        margin: 0;
    }

    #chat-input {
        background: #2d1f2d;
        min-height: 1;
        max-height: 10;
        height: auto;
        border: none;
        padding: 0;
        margin: 0;
        scrollbar-background: #2d1f2d;
        scrollbar-color: #ff99cc;
        scrollbar-size: 1 1;
    }

    #chat-input:focus {
        border: none;
    }

    /* Override TextArea internal component backgrounds */
    #chat-input > .text-area--scrollbar {
        background: #2d1f2d;
    }

    #chat-input > ScrollableContainer {
        background: #2d1f2d;
    }

    ChatInput {
        background: #2d1f2d !important;
    }

    ChatInput > .text-area--scrollbar {
        background: #2d1f2d;
    }

    ChatInput .text-area--cursor-line {
        background: #2d1f2d;
    }

    /* Target TextArea document and container but preserve cursor */
    #chat-input .text-area--document {
        background: #2d1f2d;
    }

    #chat-input .text-area--selection {
        background: #4a3344;
    }

    /* Cursor should remain visible - this comes last to override */
    #chat-input .text-area--cursor {
        background: #ff99cc;
    }

    #input-hint {
        height: 1;
        color: #bda6b6;
        background: #2d1f2d;
        padding: 0 1;
        margin: 0;
    }

    #status-bar {
        height: 1;
        background: #2d1f2d;
        color: $text;
        padding: 0 1;
    }

    .user-message {
        color: $success;
        margin: 0 0 1 0;
    }

    .assistant-message {
        color: $primary;
        margin: 0 0 1 0;
    }

    .task-update {
        color: $warning;
        margin: 0 0 1 0;
    }

    .error-message {
        color: $error;
        margin: 0 0 1 0;
    }
    """

    BINDINGS = [
        ("ctrl+q", "quit", "Quit"),
        ("ctrl+n", "new_conversation", "New Conversation"),
        ("ctrl+l", "show_conversations", "Conversations"),
        ("ctrl+o", "show_models", "Model Config"),
        ("ctrl+d", "show_documents", "Documents"),
        ("ctrl+slash", "toggle_palette", "Commands"),
        # Convenience: copy selected text from chat log (macOS cmd+c)
        ("meta+c", "screen.copy_text", "Copy Text"),
    ]

    def __init__(self):
        super().__init__()
        self.docpixie: Optional[DocPixie] = None
        self.indexed_documents: List[Document] = []
        self.conversation_history: List[ConversationMessage] = []
        self.config_manager = get_config_manager()
        self.documents_folder = Path("./documents")
        self.processing = False

        # Conversation management
        self.conversation_storage = ConversationStorage()
        self.current_conversation_id: Optional[str] = None

        # Command palette state
        self.command_palette_active = False
        self.partial_command = ""
        # Default hint shown under the chat input
        self.default_input_hint = (
            "Press / for commands • Shift+Enter: new line • Shift+Tab: switch panel"
        )

    def compose(self) -> ComposeResult:
        """Create the main UI layout"""
        yield Header(show_clock=True)

        with Container(id="chat-container"):
            yield ChatArea(id="chat-log")

            with Horizontal(id="status-bar"):
                yield Label(self.get_status_text(), id="status-label")

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
            yield Label(self.default_input_hint, id="input-hint")


        # Command palette (initially hidden)
        yield CommandPalette(id="command-palette")

        yield Footer()

    def get_status_text(self) -> str:
        """Get current status bar text"""
        text_model, vision_model = self.config_manager.get_models()
        doc_count = len(self.indexed_documents)

        # Add conversation info and cost
        conversation_info = ""
        cost_info = ""
        if self.current_conversation_id:
            conversations = self.conversation_storage.list_local_conversations()
            current_conv = next(
                (conv for conv in conversations if conv.id == self.current_conversation_id),
                None
            )
            if current_conv:
                conversation_info = f" | 💬 {current_conv.name[:20]}" + ("..." if len(current_conv.name) > 20 else "")
                # Always show cost, default to 0
                total_cost = getattr(current_conv, 'total_cost', 0.0) or 0.0
                # Format cost based on size
                if total_cost < 0.01:
                    cost_info = f" | 💰 ${total_cost:.6f}"
                else:
                    cost_info = f" | 💰 ${total_cost:.4f}"

        return f"📚 Docs: {doc_count} | 🤖 {text_model.split('/')[-1]} | 👁️ {vision_model.split('/')[-1]}{conversation_info}{cost_info}"

    async def on_mount(self) -> None:
        """Initialize the app when mounted"""
        # Defer initialization to allow UI to render first
        self.set_timer(0.1, self.deferred_init)

    async def deferred_init(self) -> None:
        """Deferred initialization to allow UI to render"""
        # Check if API key is configured
        if not self.config_manager.has_api_key():
            await self.push_screen(SetupScreen())
        else:
            await self.initialize_docpixie()

    async def create_docpixie_instance(self) -> bool:
        """Create or recreate DocPixie instance with current configuration.
        Returns True if successful, False otherwise."""
        try:
            api_key = self.config_manager.get_api_key()
            if not api_key:
                return False

            text_model, vision_model = self.config_manager.get_models()

            # Configure DocPixie
            config = DocPixieConfig(
                provider="openrouter",
                model=text_model,
                vision_model=vision_model,
                storage_type="local",  # Using LocalStorage for persistence
                local_storage_path="./.docpixie/documents",  # Project-local storage
                openrouter_api_key=api_key,
                jpeg_quality=85,
                max_pages_per_task=4
            )

            # Initialize DocPixie
            self.docpixie = DocPixie(config=config)

            # Note: Documents are persisted in storage, no need to re-add them
            # They will be loaded from storage when needed

            return True
        except Exception as e:
            # Only log error if we can access the chat log
            try:
                chat_log = self.query_one("#chat-log", ChatArea)
                chat_log.write(f"[error]❌ Failed to create DocPixie instance: {e}[/error]")
            except:
                pass  # Silently fail if UI not ready
            return False

    async def initialize_docpixie(self, show_welcome: bool = True) -> None:
        """Full initialization of DocPixie on app start"""
        chat_log = self.query_one("#chat-log", ChatArea)

        # Create DocPixie instance
        if not await self.create_docpixie_instance():
            chat_log.write("[error]❌ No API key configured. Please restart and configure.[/error]")
            return

        try:
            # Check for documents and ask user
            await self.check_and_prompt_for_documents()

            # Load last conversation or create new one
            await self.load_or_create_conversation()

            # Show welcome message (only if requested)
            if show_welcome:
                self.show_welcome_message()

            # Display loaded conversation history after welcome message
            if self.current_conversation_id and self.conversation_history:
                chat_log.add_static_text("[dim]━━━ Restored previous conversation ━━━[/dim]\n\n")

                # Display conversation history
                for msg in self.conversation_history:
                    if msg.role == "user":
                        chat_log.add_user_message(msg.content)
                    else:
                        chat_log.add_assistant_message(msg.content)

                chat_log.add_static_text("[dim]━━━ Continue your conversation below ━━━[/dim]\n\n")

        except Exception as e:
            chat_log.write(f"[error]❌ Failed to initialize: {e}[/error]")

    async def switch_models(self) -> None:
        """Switch models without reloading documents or conversations"""
        # Just recreate the DocPixie instance with new models
        # Documents stay in self.indexed_documents
        # Conversation history stays in self.conversation_history
        await self.create_docpixie_instance()

    async def check_and_prompt_for_documents(self) -> None:
        """Check for documents and prompt user to index them"""
        chat_log = self.query_one("#chat-log", ChatArea)

        # Create documents folder if it doesn't exist
        if not self.documents_folder.exists():
            self.documents_folder.mkdir(parents=True)
            chat_log.write(f"📁 Created documents folder: {self.documents_folder.absolute()}\n")
            chat_log.write("💡 Add PDF files to the documents folder and use /documents to manage them.\n")
            return

        # Clear existing indexed documents to prevent duplicates when reinitializing
        self.indexed_documents.clear()

        # Load already indexed documents from LocalStorage
        try:
            existing_docs = await self.docpixie.list_documents()
            indexed_names = {doc['name'] for doc in existing_docs}

            # Load full document objects for already indexed ones
            for doc_meta in existing_docs:
                doc = await self.docpixie.get_document(doc_meta['id'])
                if doc:
                    self.indexed_documents.append(doc)

        except Exception as e:
            indexed_names = set()
            chat_log.write(f"[dim]Note: Could not load existing documents: {e}[/dim]\n")

        # Find all PDF files in documents folder
        pdf_files = list(self.documents_folder.glob("*.pdf"))

        if not pdf_files:
            if not self.indexed_documents:
                chat_log.write(f"📭 No PDF files found in {self.documents_folder.absolute()}\n")
                chat_log.write("💡 Add PDF files to the documents folder and use /documents to manage them.\n")
            return

        # Check for new files that aren't indexed yet
        new_pdf_files = []
        for pdf in pdf_files:
            # Check if this PDF is already indexed (by name)
            if pdf.stem not in indexed_names:
                new_pdf_files.append(pdf)

        # Only prompt if there are new files to index
        if new_pdf_files:
            chat_log.write(f"📄 Found {len(new_pdf_files)} new PDF file(s)\n")
            # Show document manager for user to select which ones to index
            await self.push_screen(DocumentManagerDialog(
                self.documents_folder,
                self.docpixie
            ))

    async def load_or_create_conversation(self):
        """Load the last conversation or create a new one"""
        try:
            # Get document IDs for context
            doc_ids = [doc.id for doc in self.indexed_documents]

            # Try to load the last conversation
            last_conversation_id = self.conversation_storage.get_last_conversation()

            if last_conversation_id:
                result = self.conversation_storage.load_conversation(last_conversation_id)
                if result:
                    metadata, messages = result
                    self.current_conversation_id = last_conversation_id
                    self.conversation_history = messages

                    # Update status bar
                    status_label = self.query_one("#status-label", Label)
                    status_label.update(self.get_status_text())
                    return

            # Create new conversation if no existing one
            self.current_conversation_id = self.conversation_storage.create_new_conversation(doc_ids)

            # Update status bar
            status_label = self.query_one("#status-label", Label)
            status_label.update(self.get_status_text())

        except Exception as e:
            print(f"Error loading conversation: {e}")
            # Fallback to no conversation
            self.current_conversation_id = None

    def show_welcome_message(self) -> None:
        """Display welcome message and instructions"""
        chat_log = self.query_one("#chat-log", ChatArea)

        from rich.panel import Panel
        from rich.align import Align
        from rich.text import Text

        # Create colorful ASCII art
        ascii_art = Text()

        ascii_art.append(" ____             ____  _      _          ____ _     ___\n", style="bold cyan")
        ascii_art.append("|  _ \  ___   ___|  _ \(_)_  _(_) ___    / ___| |   |_ _|\n", style="bold magenta")
        ascii_art.append("| | | |/ _ \ / __| |_) | \ \/ / |/ _ \  | |   | |    | |\n", style="bold cyan")
        ascii_art.append("| |_| | (_) | (__|  __/| |>  <| |  __/  | |___| |___ | |\n", style="bold magenta")
        ascii_art.append("|____/ \___/ \___|_|   |_/_/\_\_|\___|   \____|_____|___|\n", style="bold cyan")

        # Create welcome content
        welcome_content = Text()
        welcome_content.append("\n")
        welcome_content.append(ascii_art)
        welcome_content.append("\n\n")

        # Status message
        if self.indexed_documents:
            welcome_content.append(f"📚 {len(self.indexed_documents)} document(s) indexed and ready!\n\n", style="bold green")
        else:
            welcome_content.append("📭 No documents indexed yet\n", style="yellow")
            welcome_content.append("💡 Add PDFs to ./documents and type ", style="dim")
            welcome_content.append("/index", style="bold yellow")
            welcome_content.append(" to get started\n\n", style="dim")

        # Prompt to start
        welcome_content.append("✨ Start chatting with your documents or type ", style="white")
        welcome_content.append("/", style="bold cyan")
        welcome_content.append(" to see all commands", style="white")

        # Create panel with the welcome message
        panel = Panel(
            Align.center(welcome_content),
            title="🧚 [bold magenta]DocPixie[/bold magenta] 🧚",
            border_style="bright_blue",
            padding=(1, 2),
            expand=False
        )

        chat_log.write(panel)
        chat_log.add_static_text("\n")

    async def on_text_area_changed(self, event: TextArea.Changed) -> None:
        """Handle text area changes for command palette"""
        if event.text_area.id != "chat-input":
            return

        # Get the current line (where cursor is)
        lines = event.text_area.text.split('\n')
        if lines:
            current_line = lines[-1] if lines else ""

            if current_line.startswith("/"):
                # Show command palette with current filter
                command_palette = self.query_one("#command-palette", CommandPalette)
                if not self.command_palette_active:
                    self.command_palette_active = True
                    command_palette.show(current_line)
                else:
                    command_palette.update_filter(current_line)
            else:
                # Hide command palette if not a command
                if self.command_palette_active:
                    command_palette = self.query_one("#command-palette", CommandPalette)
                    command_palette.hide()
                    self.command_palette_active = False

    async def submit_chat_message(self) -> None:
        """Submit the chat message from the TextArea"""
        if self.command_palette_active:
            # If command palette is active, select the current command instead
            command_palette = self.query_one("#command-palette", CommandPalette)
            selected_command = command_palette.select_current_command()
            if selected_command:
                command_palette.hide()
                self.command_palette_active = False
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

    async def on_key(self, event: events.Key) -> None:
        """Handle key events for command palette navigation"""
        if self.command_palette_active:
            command_palette = self.query_one("#command-palette", CommandPalette)

            if event.key == "escape":
                command_palette.hide()
                self.command_palette_active = False
                # Clear the slash from input
                text_area = self.query_one("#chat-input", ChatInput)
                text_area.clear()
                event.prevent_default()

            elif event.key == "up":
                command_palette.move_selection_up()
                event.prevent_default()

            elif event.key == "down":
                command_palette.move_selection_down()
                event.prevent_default()

            elif event.key == "tab":
                # Auto-complete with selected command
                selected = command_palette.get_selected_command()
                if selected:
                    text_area = self.query_one("#chat-input", ChatInput)
                    text_area.text = selected.command
                    # Move cursor to end
                    text_area.cursor_location = (0, len(selected.command))
                event.prevent_default()

            # Do not handle Enter here. Let ChatInput's bindings
            # manage Enter vs Shift+Enter (submit vs newline)

    async def submit_text(self, user_input: str) -> None:
        """Handle text submission from TextArea"""
        if self.processing:
            return

        chat_log = self.query_one("#chat-log", ChatArea)

        if not user_input:
            return

        # Hide command palette if active
        if self.command_palette_active:
            command_palette = self.query_one("#command-palette", CommandPalette)
            command_palette.hide()
            self.command_palette_active = False

        # Check for commands
        if user_input.startswith("/"):
            await self.handle_command(user_input.lower())
            return

        # Display user message using ChatArea method
        chat_log.add_user_message(user_input)

        # Disable input while processing, then re-enable after
        self.set_chat_input_enabled(False)
        try:
            await self.process_query(user_input)
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
            hint.update(self.default_input_hint)
        else:
            hint.update("⏳ Agent is working… input disabled until response.")

    async def on_command_selected(self, event: CommandSelected) -> None:
        """Handle command selection from palette"""
        # Hide the command palette
        command_palette = self.query_one("#command-palette", CommandPalette)
        command_palette.hide()
        self.command_palette_active = False

        # Clear input and execute command
        text_area = self.query_one("#chat-input", ChatInput)
        text_area.clear()

        await self.handle_command(event.command)

    async def on_command_auto_complete(self, event: CommandAutoComplete) -> None:
        """Handle command auto-completion"""
        # Fill input with the command
        text_area = self.query_one("#chat-input", ChatInput)
        text_area.text = event.command
        # Move cursor to end
        text_area.cursor_location = (0, len(event.command))

    async def on_conversation_selected(self, event: ConversationSelected) -> None:
        """Handle conversation selection from dialog"""
        chat_log = self.query_one("#chat-log", ChatArea)

        if event.conversation_id == "new":
            # Create new conversation (same as /new command)
            await self.handle_command("/new")
            return

        try:
            # Save current conversation before switching
            if self.current_conversation_id and self.conversation_history:
                doc_ids = [doc.id for doc in self.indexed_documents]
                self.conversation_storage.save_conversation(
                    self.current_conversation_id,
                    self.conversation_history,
                    doc_ids
                )

            # Load selected conversation
            result = self.conversation_storage.load_conversation(event.conversation_id)
            if result:
                metadata, messages = result
                self.current_conversation_id = event.conversation_id
                self.conversation_history = messages

                # Clear and reload chat display
                chat_log.clear()

                # Display conversation history
                for msg in messages:
                    if msg.role == "user":
                        chat_log.add_user_message(msg.content)
                    else:
                        chat_log.add_assistant_message(msg.content)

                # Update status bar
                status_label = self.query_one("#status-label", Label)
                status_label.update(self.get_status_text())

                chat_log.write(f"[success]✅ Loaded conversation: {metadata.name}[/success]\n\n")
            else:
                chat_log.write("[error]❌ Failed to load conversation[/error]\n\n")

        except Exception as e:
            chat_log.write(f"[error]❌ Error loading conversation: {e}[/error]\n\n")

    async def on_conversation_deleted(self, event: ConversationDeleted) -> None:
        """Handle conversation deletion"""
        # Just show a confirmation message
        chat_log = self.query_one("#chat-log", ChatArea)
        chat_log.write("[success]✅ Conversation deleted[/success]\n\n")

    async def on_model_selected(self, event: ModelSelected) -> None:
        """Handle model selection"""
        chat_log = self.query_one("#chat-log", ChatArea)

        # Check what changed using the old values from the event
        if event.old_text_model and event.text_model != event.old_text_model:
            chat_log.write(f"[green]✅ Planning model switched to {event.text_model}[/green]\n\n")
            # Just switch models - no document reloading
            await self.switch_models()
        elif event.old_vision_model and event.vision_model != event.old_vision_model:
            chat_log.write(f"[green]✅ Vision model switched to {event.vision_model}[/green]\n\n")
            # Just switch models - no document reloading
            await self.switch_models()
        else:
            chat_log.write("[dim]No model changes made[/dim]\n\n")

        # Update status bar
        status_label = self.query_one("#status-label", Label)
        status_label.update(self.get_status_text())

    async def on_document_removed(self, event: DocumentRemoved) -> None:
        """Handle document removal"""
        chat_log = self.query_one("#chat-log", ChatArea)

        removed_count = 0
        for doc_id in event.document_ids:
            for doc in self.indexed_documents[:]:
                if doc.id == doc_id:
                    self.indexed_documents.remove(doc)
                    removed_count += 1

                    if self.docpixie:
                        try:
                            success = self.docpixie.delete_document_sync(doc_id)
                            if not success:
                                chat_log.write(f"[warning]Warning: Could not delete {doc.name} from storage[/warning]\n")
                        except Exception as e:
                            chat_log.write(f"[error]Error deleting {doc.name}: {e}[/error]\n")

        if removed_count == 1:
            chat_log.write(f"[success]✅ Removed 1 document from index[/success]\n\n")
        else:
            chat_log.write(f"[success]✅ Removed {removed_count} documents from index[/success]\n\n")

        status_label = self.query_one("#status-label", Label)
        status_label.update(self.get_status_text())

    async def on_documents_indexed(self, event: DocumentsIndexed) -> None:
        """Handle documents being indexed"""
        chat_log = self.query_one("#chat-log", ChatArea)

        indexed_count = 0
        for doc in event.documents:
            if not any(existing.id == doc.id for existing in self.indexed_documents):
                self.indexed_documents.append(doc)
                indexed_count += 1

        if indexed_count == 1:
            chat_log.write(f"[success]✅ Successfully indexed 1 document[/success]\n\n")
        else:
            chat_log.write(f"[success]✅ Successfully indexed {indexed_count} documents[/success]\n\n")

        status_label = self.query_one("#status-label", Label)
        status_label.update(self.get_status_text())

    async def handle_command(self, command: str) -> None:
        """Handle slash commands"""
        chat_log = self.query_one("#chat-log", ChatArea)

        if command == "/exit":
            # Save current conversation before exiting
            if self.current_conversation_id and self.conversation_history:
                doc_ids = [doc.id for doc in self.indexed_documents]
                self.conversation_storage.save_conversation(
                    self.current_conversation_id,
                    self.conversation_history,
                    doc_ids
                )
            self.exit()

        elif command == "/new":
            # Save current conversation if exists
            if self.current_conversation_id and self.conversation_history:
                doc_ids = [doc.id for doc in self.indexed_documents]
                self.conversation_storage.save_conversation(
                    self.current_conversation_id,
                    self.conversation_history,
                    doc_ids
                )

            # Create new conversation
            doc_ids = [doc.id for doc in self.indexed_documents]
            self.current_conversation_id = self.conversation_storage.create_new_conversation(doc_ids)
            self.conversation_history = []

            # Update UI
            chat_log.clear()
            self.show_welcome_message()
            chat_log.write("🔄 Started new conversation\n\n")

            # Update status bar
            status_label = self.query_one("#status-label", Label)
            status_label.update(self.get_status_text())

        elif command == "/clear":
            chat_log.clear()
            self.show_welcome_message()

        elif command == "/save":
            # Save conversation with custom name (placeholder for now)
            if self.current_conversation_id and self.conversation_history:
                doc_ids = [doc.id for doc in self.indexed_documents]
                self.conversation_storage.save_conversation(
                    self.current_conversation_id,
                    self.conversation_history,
                    doc_ids
                )
                chat_log.write("💾 Conversation saved!\n\n")
            else:
                chat_log.write("[warning]No conversation to save[/warning]\n\n")

        elif command == "/conversations":
            # Show conversation manager dialog
            await self.push_screen(ConversationManagerDialog(self.current_conversation_id))

        elif command == "/model":
            # Show model selector dialog
            await self.push_screen(ModelSelectorDialog())

        elif command == "/documents":
            # Show document manager dialog with all necessary parameters
            await self.push_screen(DocumentManagerDialog(
                self.documents_folder,
                self.docpixie
            ))

        elif command == "/help":
            chat_log.write("\n[bold]Available Commands:[/bold]\n")
            chat_log.write("  /new          - Start a new conversation (Ctrl+N)\n")
            chat_log.write("  /conversations - Switch between conversations (Ctrl+L)\n")
            chat_log.write("  /save         - Save current conversation\n")
            chat_log.write("  /clear        - Clear the chat display\n")
            chat_log.write("  /model        - Configure AI models (Ctrl+O)\n")
            chat_log.write("  /documents    - Manage and index documents (Ctrl+D)\n")
            chat_log.write("  /help         - Show this help message\n")
            chat_log.write("  /exit         - Exit the program (Ctrl+Q)\n\n")
            chat_log.write("[dim]Press Ctrl+/ to open command palette[/dim]\n\n")

        else:
            chat_log.write(f"[warning]Unknown command: {command}[/warning]\n")
            chat_log.write("Type /help for available commands\n\n")

    async def process_query(self, query: str) -> None:
        """Process user query with DocPixie"""
        chat_log = self.query_one("#chat-log", ChatArea)

        if not self.docpixie:
            chat_log.write("[error]❌ DocPixie not initialized[/error]\n")
            return

        if not self.indexed_documents:
            chat_log.write("[warning]⚠️ No documents indexed yet. Use /index to index documents first.[/warning]\n")
            return

        self.processing = True
        chat_log = self.query_one("#chat-log", ChatArea)

        try:
            # Show reactive processing status
            chat_log.show_processing_status()

            # Create task update callback
            async def task_callback(event_type: str, data: Any):
                self.display_task_update(event_type, data)

            # Run query in executor to avoid blocking
            result = await asyncio.get_event_loop().run_in_executor(
                None,
                self.docpixie.query_sync,
                query,
                None,  # mode
                None,  # document_ids
                None,  # max_pages
                self.conversation_history,
                task_callback
            )

            # Processing status already hidden when plan was created

            # Display result using ChatArea method
            chat_log.add_assistant_message(result.answer)

            # Add metadata if available
            if hasattr(result, 'get_pages_by_document'):
                pages_by_doc = result.get_pages_by_document()
                if pages_by_doc:
                    chat_log.write("[dim]📄 Analyzed documents:[/dim]\n")
                    for doc_name, page_nums in pages_by_doc.items():
                        pages_str = ", ".join(str(p) for p in page_nums)
                        chat_log.write(f"[dim]  • {doc_name}: Pages {pages_str}[/dim]\n")
            elif hasattr(result, 'page_numbers') and result.page_numbers:
                # Fallback to old format if method not available
                chat_log.write(f"[dim]📄 Analyzed pages: {result.page_numbers}[/dim]\n")

            if hasattr(result, 'processing_time') and result.processing_time > 0:
                chat_log.write(f"[dim]⏱️ Processing time: {result.processing_time:.2f}s[/dim]\n")

            # Always display cost (default to 0 if not available)
            cost = getattr(result, 'total_cost', 0.0) or 0.0
            # Format based on size
            if cost < 0.01:
                chat_log.write(f"[dim]💰 Cost: ${cost:.6f}[/dim]\n")
            else:
                chat_log.write(f"[dim]💰 Cost: ${cost:.4f}[/dim]\n")

            chat_log.write("\n")

            # Update conversation history with cost
            self.conversation_history.append(
                ConversationMessage(role="user", content=query)
            )
            self.conversation_history.append(
                ConversationMessage(role="assistant", content=result.answer,
                                  cost=getattr(result, 'total_cost', 0.0) or 0.0)
            )

            # Limit conversation history
            if len(self.conversation_history) > 20:
                self.conversation_history = self.conversation_history[-20:]

            # Auto-save conversation
            if self.current_conversation_id:
                doc_ids = [doc.id for doc in self.indexed_documents]
                self.conversation_storage.save_conversation(
                    self.current_conversation_id,
                    self.conversation_history,
                    doc_ids
                )

                # Update status bar to reflect any name changes
                status_label = self.query_one("#status-label", Label)
                status_label.update(self.get_status_text())

        except Exception as e:
            chat_log.write(f"[error]❌ Error: {e}[/error]\n\n")

        finally:
            self.processing = False

    def display_task_update(self, event_type: str, data: Any) -> None:
        """Display task plan updates"""
        chat_log = self.query_one("#chat-log", ChatArea)

        if event_type == 'plan_created':
            plan = data
            # Hide processing status and mark as done immediately when plan is created
            chat_log.hide_processing_status(mark_done=True, final_text="Planning")
            # Show plan using reactive method
            chat_log.show_plan(plan)

        elif event_type == 'plan_updated':
            # Handle plan updates with completed tasks marked
            plan = data['plan']
            completed_tasks = data.get('completed_tasks', [])
            chat_log.show_plan(plan, is_update=True, completed_tasks=completed_tasks)

        elif event_type == 'task_started':
            task = data['task']
            # Extract task info for display
            task_name = task.name if hasattr(task, 'name') else str(task)
            
            # Try to get pages count and document name from task
            pages_count = getattr(task, 'pages_count', 1)  # Default to 1
            doc_name = getattr(task, 'document_name', 'document')  # Default name
            
            # Show task progress with spinner
            chat_log.show_task_progress(task_name, pages_count, doc_name)

        elif event_type == 'task_completed':
            task = data['task']
            task_name = task.name if hasattr(task, 'name') else str(task)
            
            # Mark task as done
            chat_log.update_task_status(task_name, done=True)

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
        if self.processing:
            return
        command_palette = self.query_one("#command-palette", CommandPalette)
        text_area = self.query_one("#chat-input", ChatInput)

        if self.command_palette_active:
            command_palette.hide()
            self.command_palette_active = False
        else:
            command_palette.show("/")
            self.command_palette_active = True
            text_area.text = "/"
            text_area.cursor_location = (0, 1)


def main():
    """Main entry point for Textual CLI"""
    app = DocPixieTUI()
    app.run()


if __name__ == "__main__":
    main()
