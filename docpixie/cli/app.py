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
from textual.containers import Container, Horizontal, Vertical, ScrollableContainer
from textual.widgets import Header, Footer, Input, Static, RichLog, Button, Label, ProgressBar
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
    ConversationListDialog, ConversationSelected, ConversationDeleted
)


class IndexConfirmDialog(ModalScreen):
    """Modal dialog to confirm document indexing"""

    CSS = """
    IndexConfirmDialog {
        align: center middle;
    }

    #dialog-container {
        width: 60;
        height: auto;
        padding: 2;
        background: $surface;
        border: solid $primary;
    }

    #button-container {
        align: center middle;
        margin-top: 1;
    }

    #progress-container {
        display: none;
        margin-top: 1;
    }

    #progress-container.visible {
        display: block;
    }
    """

    def __init__(self, pdf_files: List[Path]):
        super().__init__()
        self.pdf_files = pdf_files
        self.indexing = False

    def compose(self) -> ComposeResult:
        with Container(id="dialog-container"):
            # Check if these are all new files or just some new files
            title = "[bold]📚 New PDF files to index:[/bold]\n" if len(self.pdf_files) <= 5 else f"[bold]📚 Found {len(self.pdf_files)} new PDF file(s):[/bold]\n"
            yield Static(title)

            # List files
            file_list = "\n".join(f"  • {pdf.name}" for pdf in self.pdf_files[:5])
            if len(self.pdf_files) > 5:
                file_list += f"\n  ... and {len(self.pdf_files) - 5} more"
            yield Static(file_list + "\n")

            yield Static("[yellow]Index these new documents now?[/yellow]\n")

            with Container(id="progress-container"):
                yield Static("[dim]Indexing documents...[/dim]", id="progress-text")
                yield ProgressBar(total=len(self.pdf_files), id="index-progress")

            with Horizontal(id="button-container"):
                yield Button("Yes, Index Now", variant="primary", id="yes-btn")
                yield Button("Skip for Now", variant="default", id="skip-btn")

    async def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "yes-btn" and not self.indexing:
            self.indexing = True
            # Hide buttons, show progress
            self.query_one("#button-container").display = False
            self.query_one("#progress-container").add_class("visible")

            # Start indexing in background
            asyncio.create_task(self.start_indexing())

        elif event.button.id == "skip-btn":
            self.app.pop_screen()
            chat_log = self.app.query_one("#chat-log", RichLog)
            chat_log.write("[dim]Document indexing skipped. Use /index to index documents later.[/dim]\n")

    async def start_indexing(self):
        """Start the indexing process"""
        progress_bar = self.query_one("#index-progress", ProgressBar)
        progress_text = self.query_one("#progress-text", Static)

        # Index documents
        indexed_count = 0
        for i, pdf_file in enumerate(self.pdf_files, 1):
            try:
                progress_text.update(f"Indexing ({i}/{len(self.pdf_files)}): {pdf_file.name}...")

                # Run sync method in executor
                document = await asyncio.get_event_loop().run_in_executor(
                    None,
                    self.app.docpixie.add_document_sync,
                    str(pdf_file),
                    None,
                    pdf_file.stem
                )

                self.app.indexed_documents.append(document)
                indexed_count += 1
                progress_bar.advance(1)

                # Yield control to allow UI updates
                await asyncio.sleep(0.01)

            except Exception as e:
                self.app.notify(f"Failed to index {pdf_file.name}: {e}", severity="error")

        # Update app status and close dialog
        self.app.pop_screen()

        # Update status bar
        status_label = self.app.query_one("#status-label", Label)
        status_label.update(self.app.get_status_text())

        # Show success message
        chat_log = self.app.query_one("#chat-log", RichLog)
        chat_log.write(f"\n✅ Successfully indexed {indexed_count} document(s)\n")


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
    }

    #chat-log {
        height: 1fr;
        border: solid $primary;
        padding: 1;
    }

    #input-container {
        height: 3;
        padding: 0 1;
    }

    #status-bar {
        height: 1;
        background: $boost;
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
        ("ctrl+c", "quit", "Quit"),
        ("ctrl+n", "new_conversation", "New Conversation"),
        ("ctrl+d", "toggle_dark", "Toggle Dark Mode"),
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

    def compose(self) -> ComposeResult:
        """Create the main UI layout"""
        yield Header(show_clock=True)

        with Container(id="chat-container"):
            yield RichLog(id="chat-log", wrap=True, markup=True, auto_scroll=True)

            with Horizontal(id="status-bar"):
                yield Label(self.get_status_text(), id="status-label")

            with Horizontal(id="input-container"):
                yield Input(
                    placeholder="Type your message or / for commands...",
                    id="chat-input"
                )

        # Command palette (initially hidden)
        yield CommandPalette(id="command-palette")

        yield Footer()

    def get_status_text(self) -> str:
        """Get current status bar text"""
        text_model, vision_model = self.config_manager.get_models()
        doc_count = len(self.indexed_documents)

        # Add conversation info
        conversation_info = ""
        if self.current_conversation_id:
            conversations = self.conversation_storage.list_local_conversations()
            current_conv = next(
                (conv for conv in conversations if conv.id == self.current_conversation_id),
                None
            )
            if current_conv:
                conversation_info = f" | 💬 {current_conv.name[:20]}" + ("..." if len(current_conv.name) > 20 else "")

        return f"📚 Docs: {doc_count} | 🤖 {text_model.split('/')[-1]} | 👁️ {vision_model.split('/')[-1]}{conversation_info}"

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

    async def initialize_docpixie(self) -> None:
        """Initialize DocPixie with configured settings"""
        chat_log = self.query_one("#chat-log", RichLog)

        try:
            api_key = self.config_manager.get_api_key()
            if not api_key:
                chat_log.write("[error]❌ No API key configured. Please restart and configure.[/error]")
                return

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

            # Check for documents and ask user
            await self.check_and_prompt_for_documents()

            # Load last conversation or create new one
            await self.load_or_create_conversation()

            # Show welcome message
            self.show_welcome_message()

        except Exception as e:
            chat_log.write(f"[error]❌ Failed to initialize: {e}[/error]")

    async def check_and_prompt_for_documents(self) -> None:
        """Check for documents and prompt user to index them"""
        chat_log = self.query_one("#chat-log", RichLog)

        # Create documents folder if it doesn't exist
        if not self.documents_folder.exists():
            self.documents_folder.mkdir(parents=True)
            chat_log.write(f"📁 Created documents folder: {self.documents_folder.absolute()}\n")
            chat_log.write("💡 Add PDF files to the documents folder and use /index to index them.\n")
            return

        # Load already indexed documents from LocalStorage
        try:
            existing_docs = await self.docpixie.list_documents()
            indexed_names = {doc['name'] for doc in existing_docs}

            # Load full document objects for already indexed ones
            for doc_meta in existing_docs:
                doc = await self.docpixie.get_document(doc_meta['id'])
                if doc:
                    self.indexed_documents.append(doc)

            if self.indexed_documents:
                chat_log.write(f"📚 Loaded {len(self.indexed_documents)} indexed document(s) from storage\n")
        except Exception as e:
            indexed_names = set()
            chat_log.write(f"[dim]Note: Could not load existing documents: {e}[/dim]\n")

        # Find all PDF files in documents folder
        pdf_files = list(self.documents_folder.glob("*.pdf"))

        if not pdf_files:
            if not self.indexed_documents:
                chat_log.write(f"📭 No PDF files found in {self.documents_folder.absolute()}\n")
                chat_log.write("💡 Add PDF files to the documents folder and use /index to index them.\n")
            return

        # Check for new files that aren't indexed yet
        new_pdf_files = []
        for pdf in pdf_files:
            # Check if this PDF is already indexed (by name)
            if pdf.stem not in indexed_names:
                new_pdf_files.append(pdf)

        # Only prompt if there are new files to index
        if new_pdf_files:
            chat_log.write(f"📄 Found {len(new_pdf_files)} new PDF file(s) to index\n")
            await self.push_screen(IndexConfirmDialog(new_pdf_files))
        elif not self.indexed_documents:
            # No indexed documents and no new files means all PDFs are somehow orphaned
            # This shouldn't happen normally, but offer to index anyway
            await self.push_screen(IndexConfirmDialog(pdf_files))
        else:
            # All documents already indexed
            chat_log.write(f"✅ All documents already indexed\n")

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
        chat_log = self.query_one("#chat-log", RichLog)

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
        chat_log.write("\n")

    async def on_input_changed(self, event: Input.Changed) -> None:
        """Handle input changes for command palette"""
        user_input = event.value

        if user_input.startswith("/"):
            # Show command palette with current filter
            command_palette = self.query_one("#command-palette", CommandPalette)
            if not self.command_palette_active:
                self.command_palette_active = True
                command_palette.show(user_input)
            else:
                command_palette.update_filter(user_input)
        else:
            # Hide command palette if not a command
            if self.command_palette_active:
                command_palette = self.query_one("#command-palette", CommandPalette)
                command_palette.hide()
                self.command_palette_active = False

    async def on_key(self, event: events.Key) -> None:
        """Handle key events for command palette navigation"""
        if self.command_palette_active:
            command_palette = self.query_one("#command-palette", CommandPalette)

            if event.key == "escape":
                command_palette.hide()
                self.command_palette_active = False
                # Clear the slash from input
                input_widget = self.query_one("#chat-input", Input)
                input_widget.value = ""
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
                    input_widget = self.query_one("#chat-input", Input)
                    input_widget.value = selected.command
                    input_widget.cursor_position = len(selected.command)
                event.prevent_default()

            elif event.key == "enter":
                # Select command if palette is open
                selected_command = command_palette.select_current_command()
                if selected_command:
                    command_palette.hide()
                    self.command_palette_active = False
                    # Clear input and execute
                    input_widget = self.query_one("#chat-input", Input)
                    input_widget.value = ""
                    await self.handle_command(selected_command)
                event.prevent_default()

    async def on_input_submitted(self, event: Input.Submitted) -> None:
        """Handle input submission"""
        if self.processing:
            return

        input_widget = self.query_one("#chat-input", Input)
        chat_log = self.query_one("#chat-log", RichLog)

        user_input = event.value.strip()
        if not user_input:
            return

        # Hide command palette if active
        if self.command_palette_active:
            command_palette = self.query_one("#command-palette", CommandPalette)
            command_palette.hide()
            self.command_palette_active = False

        # Clear input
        input_widget.value = ""

        # Check for commands
        if user_input.startswith("/"):
            await self.handle_command(user_input.lower())
            return

        # Display user message
        chat_log.write(f"[bold green]👤 You:[/bold green] {user_input}\n")

        # Process query
        await self.process_query(user_input)

    async def on_command_selected(self, event: CommandSelected) -> None:
        """Handle command selection from palette"""
        # Hide the command palette
        command_palette = self.query_one("#command-palette", CommandPalette)
        command_palette.hide()
        self.command_palette_active = False

        # Clear input and execute command
        input_widget = self.query_one("#chat-input", Input)
        input_widget.value = ""

        await self.handle_command(event.command)

    async def on_command_auto_complete(self, event: CommandAutoComplete) -> None:
        """Handle command auto-completion"""
        # Fill input with the command
        input_widget = self.query_one("#chat-input", Input)
        input_widget.value = event.command
        input_widget.cursor_position = len(event.command)

    async def on_conversation_selected(self, event: ConversationSelected) -> None:
        """Handle conversation selection from dialog"""
        chat_log = self.query_one("#chat-log", RichLog)

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
                        chat_log.write(f"[bold green]👤 You:[/bold green] {msg.content}\n")
                    else:
                        chat_log.write(f"[bold blue]🤖 Assistant:[/bold blue]\n")
                        md = Markdown(msg.content)
                        chat_log.write(md)
                        chat_log.write("\n")

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
        chat_log = self.query_one("#chat-log", RichLog)
        chat_log.write("[success]✅ Conversation deleted[/success]\n\n")

    async def handle_command(self, command: str) -> None:
        """Handle slash commands"""
        chat_log = self.query_one("#chat-log", RichLog)

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
            # Show conversation list dialog
            await self.push_screen(ConversationListDialog(self.current_conversation_id))

        elif command == "/index":
            # Re-scan and index documents
            # Create documents folder if it doesn't exist
            if not self.documents_folder.exists():
                self.documents_folder.mkdir(parents=True)
                chat_log.write(f"📁 Created documents folder: {self.documents_folder.absolute()}\n")
                chat_log.write("💡 Add PDF files to the documents folder and use /index again.\n")
                return

            # Get already indexed document names
            indexed_names = {doc.name for doc in self.indexed_documents}

            # Find all PDF files
            pdf_files = list(self.documents_folder.glob("*.pdf"))

            if not pdf_files:
                chat_log.write(f"📭 No PDF files found in {self.documents_folder.absolute()}\n")
                chat_log.write("💡 Add PDF files to the documents folder first.\n")
                return

            # Check for new files that aren't indexed yet
            new_pdf_files = []
            for pdf in pdf_files:
                if pdf.stem not in indexed_names:
                    new_pdf_files.append(pdf)

            if new_pdf_files:
                chat_log.write(f"📄 Found {len(new_pdf_files)} new PDF file(s) to index\n")
                await self.push_screen(IndexConfirmDialog(new_pdf_files))
            else:
                chat_log.write("✅ All documents are already indexed\n")
                chat_log.write(f"📚 Currently indexed: {', '.join(indexed_names)}\n")

        elif command == "/help":
            chat_log.write("\n[bold]Available Commands:[/bold]\n")
            chat_log.write("  /new   - Start a new conversation\n")
            chat_log.write("  /clear - Clear the chat display\n")
            chat_log.write("  /index - Index documents in the documents folder\n")
            chat_log.write("  /exit  - Exit the program\n")
            chat_log.write("  /help  - Show this help message\n\n")
            chat_log.write("[dim]More commands coming in Phase 2![/dim]\n\n")

        else:
            chat_log.write(f"[warning]Unknown command: {command}[/warning]\n")
            chat_log.write("Type /help for available commands\n\n")

    async def process_query(self, query: str) -> None:
        """Process user query with DocPixie"""
        chat_log = self.query_one("#chat-log", RichLog)

        if not self.docpixie:
            chat_log.write("[error]❌ DocPixie not initialized[/error]\n")
            return

        if not self.indexed_documents:
            chat_log.write("[warning]⚠️ No documents indexed yet. Use /index to index documents first.[/warning]\n")
            return

        self.processing = True
        chat_log = self.query_one("#chat-log", RichLog)

        try:
            chat_log.write("[dim]⏳ Processing query...[/dim]\n")

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

            # Display result
            chat_log.write(f"\n[bold blue]🤖 Assistant:[/bold blue]\n")

            # Use Rich Markdown for better formatting
            md = Markdown(result.answer)
            chat_log.write(md)
            chat_log.write("\n")

            # Add metadata if available
            if hasattr(result, 'page_numbers') and result.page_numbers:
                chat_log.write(f"[dim]📄 Analyzed pages: {result.page_numbers}[/dim]\n")

            if hasattr(result, 'processing_time') and result.processing_time > 0:
                chat_log.write(f"[dim]⏱️ Processing time: {result.processing_time:.2f}s[/dim]\n")

            chat_log.write("\n")

            # Update conversation history
            self.conversation_history.append(
                ConversationMessage(role="user", content=query)
            )
            self.conversation_history.append(
                ConversationMessage(role="assistant", content=result.answer)
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
        chat_log = self.query_one("#chat-log", RichLog)

        if event_type == 'plan_created':
            plan = data
            chat_log.write("\n[yellow]📋 Task Plan:[/yellow]\n")
            for task in plan.tasks:
                chat_log.write(f"  • {task.name}\n")

        elif event_type == 'task_started':
            task = data['task']
            chat_log.write(f"[yellow]🔄 {task.name}...[/yellow]\n")

        elif event_type == 'task_completed':
            task = data['task']
            result = data.get('result', {})
            pages = result.pages_analyzed if hasattr(result, 'pages_analyzed') else 0
            chat_log.write(f"[green]✅ Completed ({pages} pages)[/green]\n")

    def action_quit(self) -> None:
        """Quit the application"""
        self.exit()

    def action_new_conversation(self) -> None:
        """Start a new conversation"""
        asyncio.create_task(self.handle_command("/new"))

    def action_toggle_dark(self) -> None:
        """Toggle dark mode"""
        self.dark = not self.dark


def main():
    """Main entry point for Textual CLI"""
    app = DocPixieTUI()
    app.run()


if __name__ == "__main__":
    main()
