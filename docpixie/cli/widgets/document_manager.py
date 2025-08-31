"""
Document manager dialog for DocPixie CLI
Allows users to view and manage indexed documents
"""

from typing import List, Optional, Set
from datetime import datetime
from textual.widgets import Static, ListView, ListItem, Label
from textual.containers import Container, Horizontal, Vertical
from textual.screen import ModalScreen
from textual.message import Message
from textual import events
from rich.text import Text

from docpixie.models.document import Document


class DocumentRemoved(Message):
    """Message sent when documents are removed"""

    def __init__(self, document_ids: List[str]):
        self.document_ids = document_ids
        super().__init__()


class DeletionConfirmDialog(ModalScreen):
    """Modal dialog to confirm document deletion"""

    CSS = """
    DeletionConfirmDialog {
        align: center middle;
    }

    #confirm-container {
        width: 50;
        height: auto;
        min-height: 10;
        padding: 1;
        background: $surface;
        border: solid $error;
    }

    .confirm-title {
        height: 1;
        margin: 0 0 1 0;
        color: $error;
    }

    .confirm-message {
        height: 2;
        margin: 0 0 1 0;
    }

    .confirm-hint {
        height: 1;
        align: center middle;
        color: $text-muted;
        margin-top: 1;
    }
    """

    def __init__(self, document_count: int):
        super().__init__()
        self.document_count = document_count
        self.confirmed = False
        self.document_ids = []  # Will be set by parent dialog
        self.parent_dialog = None  # Reference to parent DocumentManagerDialog

    def compose(self):
        """Create the confirmation dialog"""
        with Container(id="confirm-container"):
            yield Static("[bold]⚠️ Confirm Deletion[/bold]", classes="confirm-title")

            if self.document_count == 1:
                message = "Are you sure you want to delete 1 document?"
            else:
                message = f"Are you sure you want to delete {self.document_count} documents?"

            yield Static(message, classes="confirm-message")
            yield Static("[bold]This action cannot be undone.[/bold]", classes="confirm-message")

            yield Static(
                "[dim]Press [bold]Y[/bold] to confirm or [bold]N[/bold] to cancel[/dim]",
                classes="confirm-hint"
            )

    async def on_key(self, event: events.Key) -> None:
        """Handle key events"""
        if event.key.lower() == "y":
            self.confirmed = True
            # Send removal message if we have document IDs
            if self.document_ids and self.parent_dialog:
                self.parent_dialog.post_message(DocumentRemoved(self.document_ids))
                # Dismiss both dialogs
                self.dismiss()
                self.parent_dialog.dismiss()
            else:
                self.dismiss()
        elif event.key.lower() == "n" or event.key == "escape":
            self.confirmed = False
            self.dismiss()


class DocumentManagerDialog(ModalScreen):
    """Modal dialog for managing indexed documents"""

    CSS = """
    DocumentManagerDialog {
        align: center middle;
    }

    #dialog-container {
        width: 80;
        height: auto;
        max-height: 30;
        min-height: 26;
        padding: 1;
        background: $surface;
        border: solid $primary;
        overflow-y: auto;
    }

    .title {
        height: 1;
        margin: 0 0 1 0;
    }

    #document-list {
        height: 17;
        scrollbar-background: $panel;
        scrollbar-color: $primary;
        scrollbar-size: 1 1;
        border: solid $accent;
        padding: 1;
        margin: 0;
    }

    #no-documents {
        height: 17;
        align: center middle;
        color: $text-muted;
        border: solid $accent;
        padding: 1;
        margin: 0;
    }

    .document-item {
        height: auto;
        padding: 0 1;
        margin: 0;
    }

    .document-item.--highlight {
        background: $primary;
        color: $text;
    }

    .document-item-selected {
        background: $success 30%;
        border-left: thick $success;
    }

    .document-meta {
        color: $text-muted;
        margin: 0;
    }

    #selection-info {
        height: 1;
        margin: 1 0;
        color: $warning;
    }

    #controls-hint {
        height: 2;
        align: center middle;
        color: $text-muted;
    }
    """

    def __init__(self, documents: List[Document]):
        super().__init__()
        self.documents = documents
        self.selected_documents: Set[str] = set()
        self.document_items: List[ListItem] = []
        self.focused_index = 0

    def compose(self):
        """Create the document manager dialog"""
        with Container(id="dialog-container"):
            # Title
            yield Static("[bold]📚 Document Manager[/bold]", classes="title")

            # Document list
            yield ListView(id="document-list")

            # Empty state message (initially hidden)
            yield Static(
                "[dim]No documents indexed yet.\nUse /index to add documents from the documents folder.[/dim]",
                id="no-documents"
            )

            # Selection info
            yield Static(id="selection-info", classes="info")
            
            # Control hints
            yield Static(
                "[dim]↑↓[/dim] Navigate  [dim]Enter[/dim] Toggle Select  [dim]D[/dim] Delete Selected  [dim]Esc[/dim] Close",
                id="controls-hint"
            )

    async def on_mount(self):
        """Load documents when dialog mounts"""
        self._update_selection_info()
        self._load_documents()

        # Set initial focus to the dialog itself
        self.focus()

    def _load_documents(self):
        """Load and display documents"""
        list_view = self.query_one("#document-list", ListView)
        no_docs_msg = self.query_one("#no-documents", Static)

        if not self.documents:
            # Show empty state
            list_view.display = False
            no_docs_msg.display = True
            return

        # Hide empty state, show list
        list_view.display = True
        no_docs_msg.display = False

        # Clear existing items
        list_view.clear()
        self.document_items = []

        # Add document items
        for i, doc in enumerate(self.documents):
            # Create document item content
            item_content = self._create_document_content(doc)

            # Create list item
            list_item = ListItem(item_content, classes="document-item")
            list_item.data = doc.id  # Store document ID for reference

            list_view.append(list_item)
            self.document_items.append(list_item)

        # Focus first item
        if self.document_items:
            self.focused_index = 0
            self._highlight_focused()

    def _create_document_content(self, doc: Document) -> Static:
        """Create content for a document item"""
        # Create compact single-line display
        display_text = Text()

        # Selection checkbox
        if doc.id in self.selected_documents:
            display_text.append("[✓] ", style="green bold")
        else:
            display_text.append("[ ] ", style="dim")

        # Document name
        display_text.append(f"{doc.name}", style="bold")

        # Metadata on same line
        display_text.append(f"  ", style="dim")
        display_text.append(f"({doc.page_count} pages", style="dim")

        if hasattr(doc, 'file_size'):
            # Convert bytes to human readable
            size = doc.file_size if hasattr(doc, 'file_size') else 0
            if size > 1024 * 1024:
                size_str = f"{size / (1024 * 1024):.1f}MB"
            elif size > 1024:
                size_str = f"{size / 1024:.1f}KB"
            else:
                size_str = f"{size}B"
            display_text.append(f", {size_str}", style="dim")

        display_text.append(")", style="dim")

        return Static(display_text)

    def _highlight_focused(self):
        """Highlight the currently focused document"""
        # Remove previous highlights
        for item in self.document_items:
            item.remove_class("document-item-selected")

        # Highlight current focus
        if 0 <= self.focused_index < len(self.document_items):
            self.document_items[self.focused_index].add_class("document-item-selected")

            # Scroll to focused item
            list_view = self.query_one("#document-list", ListView)
            list_view.scroll_to_widget(self.document_items[self.focused_index])

    def _toggle_selection(self, index: int):
        """Toggle selection for a document"""
        if 0 <= index < len(self.documents):
            doc = self.documents[index]

            if doc.id in self.selected_documents:
                self.selected_documents.remove(doc.id)
            else:
                self.selected_documents.add(doc.id)

            # Update display
            self._refresh_document_item(index)
            self._update_selection_info()

    def _refresh_document_item(self, index: int):
        """Refresh a single document item display"""
        if 0 <= index < len(self.document_items):
            doc = self.documents[index]
            list_item = self.document_items[index]

            # Recreate content
            new_content = self._create_document_content(doc)

            # Replace content in the list item
            list_item.remove_children()
            list_item.mount(new_content)

    def _update_selection_info(self):
        """Update the selection info display"""
        info = self.query_one("#selection-info", Static)
        count = len(self.selected_documents)

        if count == 0:
            info.update("[dim]No documents selected[/dim]")
        elif count == 1:
            info.update(f"[yellow]1 document selected[/yellow]")
        else:
            info.update(f"[yellow]{count} documents selected[/yellow]")


    async def _remove_selected(self):
        """Remove selected documents with confirmation"""
        if self.selected_documents:
            # Show confirmation dialog without waiting
            confirm_dialog = DeletionConfirmDialog(len(self.selected_documents))

            # Store the selected document IDs in the confirm dialog
            confirm_dialog.document_ids = list(self.selected_documents)
            confirm_dialog.parent_dialog = self

            # Push the screen without waiting
            self.app.push_screen(confirm_dialog)

    def _move_focus_up(self):
        """Move focus up"""
        if self.documents and self.focused_index > 0:
            self.focused_index -= 1
            self._highlight_focused()

    def _move_focus_down(self):
        """Move focus down"""
        if self.documents and self.focused_index < len(self.documents) - 1:
            self.focused_index += 1
            self._highlight_focused()

    async def on_key(self, event: events.Key) -> None:
        """Handle key events"""
        # Always prevent default to stop ListView from handling keys
        event.prevent_default()
        event.stop()

        if event.key == "escape":
            self.dismiss()
        elif event.key == "up":
            self._move_focus_up()
        elif event.key == "down":
            self._move_focus_down()
        elif event.key == "enter" or event.key == "space":
            # Toggle selection for focused item
            self._toggle_selection(self.focused_index)
        elif event.key.lower() == "d":
            # Delete selected documents with confirmation
            if self.selected_documents:
                await self._remove_selected()

    async def on_list_view_selected(self, event: ListView.Selected) -> None:
        """Handle list item click"""
        # Get the index of the clicked item
        index = event.list_view.index
        if index is not None:
            # Update focus
            self.focused_index = index
            self._highlight_focused()

            # Toggle selection
            self._toggle_selection(index)
