"""
Document manager dialog for DocPixie CLI
Allows users to view and manage all documents (indexed and unindexed)
"""

import asyncio
from pathlib import Path
from typing import List, Optional, Set, Dict
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


class DocumentsIndexed(Message):
    """Message sent when documents are indexed"""

    def __init__(self, documents: List[Document]):
        self.documents = documents
        super().__init__()


class IndexingConfirmDialog(ModalScreen):
    """Modal dialog to confirm document indexing"""

    CSS = """
    IndexingConfirmDialog {
        align: center middle;
    }

    #confirm-container {
        width: 50;
        height: auto;
        min-height: 10;
        padding: 1;
        background: $surface;
        border: solid $success;
    }

    .confirm-title {
        height: 1;
        margin: 0 0 1 0;
        color: $success;
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
        self.parent_dialog = None  # Reference to parent DocumentManagerDialog

    def compose(self):
        """Create the confirmation dialog"""
        with Container(id="confirm-container"):
            yield Static("[bold]📚 Confirm Indexing[/bold]", classes="confirm-title")

            if self.document_count == 1:
                message = "Index 1 document?"
            else:
                message = f"Index {self.document_count} documents?"

            yield Static(message, classes="confirm-message")
            yield Static("[dim]This may take a moment depending on document size.[/dim]", classes="confirm-message")

            yield Static(
                "[dim]Press [bold]Y[/bold] to confirm or [bold]N[/bold] to cancel[/dim]",
                classes="confirm-hint"
            )

    async def on_key(self, event: events.Key) -> None:
        """Handle key events"""
        if event.key.lower() == "y":
            self.confirmed = True
            if self.parent_dialog:
                asyncio.create_task(self.parent_dialog._perform_indexing_confirmed())
            self.dismiss()
        elif event.key.lower() == "n" or event.key == "escape":
            self.confirmed = False
            self.dismiss()


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
        self.document_ids = []
        self.parent_dialog = None

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
            if self.document_ids and self.parent_dialog:
                self.app.post_message(DocumentRemoved(self.document_ids))
                # Update dialog UI immediately
                asyncio.create_task(self.parent_dialog._update_after_removal(self.document_ids))
            self.dismiss()
        elif event.key.lower() == "n" or event.key == "escape":
            self.confirmed = False
            self.dismiss()


class DocumentManagerDialog(ModalScreen):
    """Modal dialog for managing all documents (indexed and unindexed)"""

    CSS = """
    DocumentManagerDialog {
        align: center middle;
    }

    #dialog-container {
        width: 80;
        height: auto;
        max-height: 35;
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
        height: 20;
        scrollbar-background: $panel;
        scrollbar-color: $primary;
        scrollbar-size: 1 1;
        border: solid $accent;
        padding: 1;
        margin: 0;
    }

    #no-documents {
        height: 20;
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

    #progress-container {
        display: none;
        margin: 1 0;
        padding: 0;
    }

    #progress-container.visible {
        display: block;
    }
    
    #progress-display {
        height: 2;
        color: $text;
        padding: 0 1;
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

    def __init__(self, documents_folder: Path, docpixie=None):
        super().__init__()
        self.documents_folder = documents_folder
        self.docpixie = docpixie
        self.selected_items: Set[str] = set()
        self.document_items: List[ListItem] = []
        self.focused_index = 0
        self.indexing = False
        self.pending_index_files: List[Path] = []
        
        self.all_items: List[Dict] = []

    def compose(self):
        """Create the document manager dialog"""
        with Container(id="dialog-container"):
            # Title (will be updated with counts)
            yield Static("[bold]📚 Document Manager[/bold]", classes="title", id="title")

            # Document list
            yield ListView(id="document-list")

            # Empty state message (initially hidden)
            yield Static(
                "[dim]No PDF documents found in the documents folder.[/dim]",
                id="no-documents"
            )

            # Progress container for indexing
            with Container(id="progress-container"):
                yield Static("", id="progress-display")

            # Selection info
            yield Static(id="selection-info", classes="info")
            
            # Control hints
            yield Static(
                "[dim]↑↓[/dim] Navigate  [dim]Enter/Space[/dim] Toggle  [dim]I[/dim] Index Selected  [dim]D[/dim] Delete from Storage  [dim]Esc[/dim] Close",
                id="controls-hint"
            )

    async def on_mount(self):
        """Load documents when dialog mounts"""
        self._scan_and_load_documents()
        self._update_title()
        self._update_selection_info()
        
        # Set initial focus to the dialog itself
        self.focus()

    def _scan_and_load_documents(self):
        """Scan folder for PDFs and match with indexed documents"""
        self.all_items = []
        
        indexed_map = {doc.name: doc for doc in self.app.indexed_documents}
        
        if self.documents_folder.exists():
            pdf_files = sorted(self.documents_folder.glob("*.pdf"))
            
            for pdf_file in pdf_files:
                item = {
                    'name': pdf_file.stem,
                    'pdf_path': pdf_file,
                    'is_indexed': pdf_file.stem in indexed_map,
                    'document': indexed_map.get(pdf_file.stem),
                    'file_size': pdf_file.stat().st_size if pdf_file.exists() else 0
                }
                self.all_items.append(item)
        
        self._load_document_list()

    def _load_document_list(self):
        """Load and display the document list"""
        list_view = self.query_one("#document-list", ListView)
        no_docs_msg = self.query_one("#no-documents", Static)

        if not self.all_items:
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
        for i, item in enumerate(self.all_items):
            # Create document item content
            item_content = self._create_item_content(item)

            # Create list item
            list_item = ListItem(item_content, classes="document-item")
            # Store identifier for reference (use name as unique ID)
            list_item.data = item['name']

            list_view.append(list_item)
            self.document_items.append(list_item)

        # Focus first item
        if self.document_items:
            self.focused_index = 0
            self._highlight_focused()
            
    def _update_title(self):
        """Update the title with document counts"""
        title = self.query_one("#title", Static)
        total = len(self.all_items)
        indexed = sum(1 for item in self.all_items if item['is_indexed'])
        
        title.update(f"[bold]📚 Document Manager - Total: {total} docs ({indexed} indexed)[/bold]")

    def _create_item_content(self, item: Dict) -> Static:
        """Create content for a document item (indexed or unindexed)"""
        display_text = Text()
        
        # Column 1: Selection checkbox (4 chars)
        if item['name'] in self.selected_items:
            display_text.append("[✓] ", style="green bold")
        else:
            display_text.append("[ ] ", style="dim")
        
        # Column 2: Document name (35 chars fixed width to prevent wrapping)
        name_with_ext = f"{item['name']}.pdf"
        max_name_length = 35
        
        if len(name_with_ext) > max_name_length:
            # Truncate with ellipsis
            truncated_name = name_with_ext[:max_name_length-3] + "..."
        else:
            # Pad with spaces to maintain alignment
            truncated_name = name_with_ext.ljust(max_name_length)
        
        display_text.append(truncated_name, style="bold")
        
        # Column 3: Status (right side)
        display_text.append("  ", style="dim")  # Spacing
        
        if item['is_indexed']:
            # For indexed documents
            doc = item['document']
            display_text.append("✅ Indexed", style="green")
            display_text.append(" | ", style="dim")
            display_text.append(f"{doc.page_count} pages", style="dim")
        else:
            # For unindexed documents
            display_text.append("⚪ Not indexed", style="yellow")

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
        if 0 <= index < len(self.all_items):
            item = self.all_items[index]
            name = item['name']

            if name in self.selected_items:
                self.selected_items.remove(name)
            else:
                self.selected_items.add(name)

            # Update display
            self._refresh_document_item(index)
            self._update_selection_info()

    def _refresh_document_item(self, index: int):
        """Refresh a single document item display"""
        if 0 <= index < len(self.document_items):
            item = self.all_items[index]
            list_item = self.document_items[index]

            # Recreate content
            new_content = self._create_item_content(item)

            # Replace content in the list item
            list_item.remove_children()
            list_item.mount(new_content)
    
    def _refresh_specific_item(self, name: str):
        """Refresh a specific document item by name"""
        for index, item in enumerate(self.all_items):
            if item['name'] == name:
                self._refresh_document_item(index)
                break

    def _update_selection_info(self):
        """Update the selection info display"""
        info = self.query_one("#selection-info", Static)
        count = len(self.selected_items)

        if count == 0:
            info.update("[dim]No documents selected[/dim]")
        else:
            # Count how many selected are indexed vs unindexed
            indexed_count = 0
            unindexed_count = 0
            for name in self.selected_items:
                # Find the item
                for item in self.all_items:
                    if item['name'] == name:
                        if item['is_indexed']:
                            indexed_count += 1
                        else:
                            unindexed_count += 1
                        break
            
            if count == 1:
                info.update(f"[yellow]1 document selected[/yellow]")
            else:
                info.update(f"[yellow]{count} documents selected[/yellow]")


    async def _remove_selected(self):
        """Remove selected indexed documents with confirmation"""
        # Get only indexed documents that are selected
        indexed_to_remove = []
        for name in self.selected_items:
            for item in self.all_items:
                if item['name'] == name and item['is_indexed']:
                    indexed_to_remove.append(item['document'].id)
                    break
        
        if indexed_to_remove:
            confirm_dialog = DeletionConfirmDialog(len(indexed_to_remove))
            confirm_dialog.document_ids = indexed_to_remove
            confirm_dialog.parent_dialog = self
            self.app.push_screen(confirm_dialog)

    async def _index_selected(self):
        """Index selected unindexed documents"""
        if self.indexing:
            return
            
        # Get only unindexed documents that are selected
        to_index = []
        for name in self.selected_items:
            for item in self.all_items:
                if item['name'] == name and not item['is_indexed']:
                    to_index.append(item['pdf_path'])
                    break
        
        if to_index:
            # Store the files to index
            self.pending_index_files = to_index
            
            # Show confirmation dialog
            confirm_dialog = IndexingConfirmDialog(len(to_index))
            confirm_dialog.parent_dialog = self
            self.app.push_screen(confirm_dialog)
    
    async def _perform_indexing_confirmed(self):
        """Perform indexing after confirmation"""
        if hasattr(self, 'pending_index_files') and self.pending_index_files:
            self.indexing = True
            # Show progress container
            progress_container = self.query_one("#progress-container", Container)
            progress_container.add_class("visible")
            
            # Start indexing
            await self._perform_indexing(self.pending_index_files)
            
            # Clear pending files
            self.pending_index_files = []
    
    async def _update_spinner_animation(self, stop_event: asyncio.Event):
        """Background task to update spinner animation smoothly"""
        progress_display = self.query_one("#progress-display", Static)
        spinner_frames = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]
        spinner_index = 0
        
        while not stop_event.is_set():
            # Get current indexing state
            if hasattr(self, '_current_indexing_state'):
                state = self._current_indexing_state
                
                # Update spinner
                spinner = spinner_frames[spinner_index % len(spinner_frames)]
                spinner_index += 1
                
                # Create display with current state
                display_text = (
                    f"[bold rgb(147,112,219)]{spinner}[/bold rgb(147,112,219)] Indexing: {state['filename']} ({state['current']}/{state['total']})\n"
                    f"[rgb(147,112,219)]{state['bar_filled']}[/rgb(147,112,219)][dim]{state['bar_empty']}[/dim] {state['progress']}%"
                )
                
                progress_display.update(display_text)
            
            # Wait before next update
            await asyncio.sleep(0.1)
    
    async def _perform_indexing(self, pdf_files: List[Path]):
        """Perform the actual indexing of documents"""
        progress_display = self.query_one("#progress-display", Static)
        
        indexed_docs = []
        total = len(pdf_files)
        
        # Initialize indexing state
        self._current_indexing_state = {
            'filename': 'Preparing...',
            'current': 0,
            'total': total,
            'progress': 0,
            'bar_filled': '',
            'bar_empty': '░' * 30
        }
        
        # Start spinner animation task
        stop_spinner = asyncio.Event()
        spinner_task = asyncio.create_task(self._update_spinner_animation(stop_spinner))
        
        try:
            for i, pdf_file in enumerate(pdf_files, 1):
                try:
                    # Update state for current file
                    completed = i - 1
                    progress = int(completed / total * 100)
                    filled = int(progress / 100 * 30)
                    empty = 30 - filled
                    
                    # Truncate filename
                    filename = pdf_file.name
                    if len(filename) > 25:
                        filename = filename[:22] + "..."
                    
                    # Update shared state
                    self._current_indexing_state = {
                        'filename': filename,
                        'current': i,
                        'total': total,
                        'progress': progress,
                        'bar_filled': '█' * filled,
                        'bar_empty': '░' * empty
                    }
                    
                    # Run sync method in executor
                    if self.docpixie:
                        document = await asyncio.get_event_loop().run_in_executor(
                            None,
                            self.docpixie.add_document_sync,
                            str(pdf_file),
                            None,
                            pdf_file.stem
                        )
                        indexed_docs.append(document)
                        
                        # Update the item immediately
                        for item in self.all_items:
                            if item['name'] == document.name:
                                item['is_indexed'] = True
                                item['document'] = document
                                break
                        
                        # Refresh display for this item
                        self._refresh_specific_item(document.name)
                        self._update_title()
                        
                except Exception as e:
                    self.app.notify(f"Failed to index {pdf_file.name}: {e}", severity="error")
        
        finally:
            # Stop spinner animation
            stop_spinner.set()
            await spinner_task
        
        # Show 100% completion before hiding
        if indexed_docs:
            display_text = (
                f"[bold green]✅[/bold green] Completed: Indexed {len(indexed_docs)} document(s)\n"
                f"[rgb(147,112,219)]{'█' * 30}[/rgb(147,112,219)] 100%"
            )
            progress_display.update(display_text)
            await asyncio.sleep(0.5)  # Brief pause to show completion
        
        # Hide progress container
        progress_container = self.query_one("#progress-container", Container)
        progress_container.remove_class("visible")
        
        self.indexing = False
        
        if indexed_docs:
            self.app.post_message(DocumentsIndexed(indexed_docs))
            
            for doc in indexed_docs:
                if doc.name in self.selected_items:
                    self.selected_items.remove(doc.name)

    def _move_focus_up(self):
        """Move focus up"""
        if self.all_items and self.focused_index > 0:
            self.focused_index -= 1
            self._highlight_focused()

    def _move_focus_down(self):
        """Move focus down"""
        if self.all_items and self.focused_index < len(self.all_items) - 1:
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
        elif event.key.lower() == "i":
            # Index selected unindexed documents
            await self._index_selected()
        elif event.key.lower() == "d":
            # Delete selected indexed documents with confirmation
            await self._remove_selected()

    async def _update_after_removal(self, document_ids: List[str]) -> None:
        """Update UI immediately after document removal"""
        for doc_id in document_ids:
            # Find document name from current items
            doc_name = None
            for item in self.all_items:
                if item['is_indexed'] and item['document'] and item['document'].id == doc_id:
                    doc_name = item['name']
                    item['is_indexed'] = False
                    item['document'] = None
                    break
            
            # Clear from selections
            if doc_name and doc_name in self.selected_items:
                self.selected_items.remove(doc_name)
            
            # Refresh the specific item
            if doc_name:
                self._refresh_specific_item(doc_name)
        
        self._update_title()
        self._update_selection_info()

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
