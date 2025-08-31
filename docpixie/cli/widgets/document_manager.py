"""
Document manager dialog for DocPixie CLI
Allows users to view and manage indexed documents
"""

from typing import List, Optional, Set
from datetime import datetime
from textual.widgets import Static, ListView, ListItem, Label, Button, DataTable
from textual.containers import Container, Vertical, Horizontal, ScrollableContainer
from textual.screen import ModalScreen
from textual.message import Message
from textual import events
from rich.text import Text
from rich.panel import Panel

from docpixie.models.document import Document


class DocumentRemoved(Message):
    """Message sent when documents are removed"""
    
    def __init__(self, document_ids: List[str]):
        self.document_ids = document_ids
        super().__init__()


class DocumentManagerDialog(ModalScreen):
    """Modal dialog for managing indexed documents"""
    
    CSS = """
    DocumentManagerDialog {
        align: center middle;
    }
    
    #dialog-container {
        width: 90;
        height: 35;
        padding: 2;
        background: $surface;
        border: solid $primary;
    }
    
    #document-list {
        height: 22;
        scrollbar-background: $panel;
        scrollbar-color: $primary;
        border: solid $accent;
        margin: 1 0;
    }
    
    .document-item {
        height: auto;
        min-height: 4;
        padding: 1;
        margin: 0 0 1 0;
        border: solid $panel;
    }
    
    .document-item.--highlight {
        background: $accent;
        color: $text;
    }
    
    .document-item-selected {
        background: $primary 20%;
        border: solid $primary;
    }
    
    #button-container {
        align: center middle;
        margin-top: 1;
    }
    
    #no-documents {
        align: center middle;
        height: 100%;
        color: $text-muted;
    }
    
    .document-meta {
        color: $text-muted;
        margin-top: 1;
    }
    
    .document-summary {
        margin-top: 1;
        padding: 1;
        background: $panel;
        border: solid $primary-darken-1;
    }
    
    #selection-info {
        color: $warning;
        height: 1;
        margin: 1 0;
    }
    
    .select-checkbox {
        width: 3;
        align: left middle;
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
            yield Static("[bold]📚 Document Manager[/bold]\n", classes="title")
            
            # Instructions
            yield Static(
                "Manage your indexed documents. Press [bold]Space[/bold] to select/deselect, [bold]Enter[/bold] to remove selected.\n",
                classes="instructions"
            )
            
            # Selection info
            yield Static("", id="selection-info")
            
            # Document list
            yield ListView(id="document-list")
            
            # Empty state message (initially hidden)
            yield Static(
                "[dim]No documents indexed yet.\nUse /index to add documents from the documents folder.[/dim]",
                id="no-documents"
            )
            
            # Action buttons
            with Horizontal(id="button-container"):
                yield Button("Remove Selected", variant="error", id="remove-btn", disabled=True)
                yield Button("Select All", variant="primary", id="select-all-btn")
                yield Button("Deselect All", variant="default", id="deselect-all-btn", disabled=True)
                yield Button("Close", variant="default", id="close-btn")
    
    def on_mount(self):
        """Load documents when dialog mounts"""
        self._load_documents()
    
    def _load_documents(self):
        """Load and display documents"""
        list_view = self.query_one("#document-list", ListView)
        no_docs_msg = self.query_one("#no-documents", Static)
        
        if not self.documents:
            # Show empty state
            list_view.display = False
            no_docs_msg.display = True
            
            # Disable action buttons
            self.query_one("#select-all-btn", Button).disabled = True
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
    
    def _create_document_content(self, doc: Document) -> Vertical:
        """Create content for a document item"""
        # Document name with selection indicator
        name_text = Text()
        
        # Selection checkbox
        if doc.id in self.selected_documents:
            name_text.append("[✓] ", style="green bold")
        else:
            name_text.append("[ ] ", style="dim")
        
        name_text.append(doc.name, style="bold white")
        
        # Metadata
        meta_text = Text()
        meta_text.append(f"Pages: {doc.page_count}", style="dim")
        
        if hasattr(doc, 'created_at'):
            created_date = doc.created_at.strftime("%Y-%m-%d %H:%M") if isinstance(doc.created_at, datetime) else str(doc.created_at)
            meta_text.append(f" | Added: {created_date}", style="dim")
        
        if hasattr(doc, 'file_size'):
            # Convert bytes to human readable
            size = doc.file_size if hasattr(doc, 'file_size') else 0
            if size > 1024 * 1024:
                size_str = f"{size / (1024 * 1024):.1f} MB"
            elif size > 1024:
                size_str = f"{size / 1024:.1f} KB"
            else:
                size_str = f"{size} bytes"
            meta_text.append(f" | Size: {size_str}", style="dim")
        
        # Summary preview (first 150 chars)
        summary_preview = ""
        if doc.summary:
            summary_preview = doc.summary[:150]
            if len(doc.summary) > 150:
                summary_preview += "..."
        
        # Build list of widgets for container
        widgets = [
            Static(name_text),
            Static(meta_text, classes="document-meta")
        ]
        
        # Add summary if available
        if summary_preview:
            summary_text = Text()
            summary_text.append("Summary: ", style="dim italic")
            summary_text.append(summary_preview, style="italic")
            widgets.append(Static(summary_text, classes="document-summary"))
        
        # Create container with all widgets
        container = Vertical(*widgets)
        
        return container
    
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
            self._update_button_states()
    
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
            info.update("")
        elif count == 1:
            info.update(f"[yellow]1 document selected[/yellow]")
        else:
            info.update(f"[yellow]{count} documents selected[/yellow]")
    
    def _update_button_states(self):
        """Update button enabled/disabled states"""
        remove_btn = self.query_one("#remove-btn", Button)
        select_all_btn = self.query_one("#select-all-btn", Button)
        deselect_all_btn = self.query_one("#deselect-all-btn", Button)
        
        # Enable remove button if any selected
        remove_btn.disabled = len(self.selected_documents) == 0
        
        # Enable/disable select/deselect buttons
        select_all_btn.disabled = len(self.selected_documents) == len(self.documents)
        deselect_all_btn.disabled = len(self.selected_documents) == 0
    
    def _select_all(self):
        """Select all documents"""
        for doc in self.documents:
            self.selected_documents.add(doc.id)
        
        # Refresh all items
        for i in range(len(self.document_items)):
            self._refresh_document_item(i)
        
        self._update_selection_info()
        self._update_button_states()
    
    def _deselect_all(self):
        """Deselect all documents"""
        self.selected_documents.clear()
        
        # Refresh all items
        for i in range(len(self.document_items)):
            self._refresh_document_item(i)
        
        self._update_selection_info()
        self._update_button_states()
    
    def _remove_selected(self):
        """Remove selected documents"""
        if self.selected_documents:
            # Convert set to list for the message
            doc_ids_to_remove = list(self.selected_documents)
            
            # Send removal message
            self.post_message(DocumentRemoved(doc_ids_to_remove))
            
            # Close dialog
            self.dismiss()
    
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
        if event.key == "escape":
            self.dismiss()
            event.prevent_default()
        elif event.key == "up":
            self._move_focus_up()
            event.prevent_default()
        elif event.key == "down":
            self._move_focus_down()
            event.prevent_default()
        elif event.key == "space":
            # Toggle selection for focused item
            self._toggle_selection(self.focused_index)
            event.prevent_default()
        elif event.key == "enter":
            # Remove selected documents
            if self.selected_documents:
                self._remove_selected()
            event.prevent_default()
        elif event.key.lower() == "a":
            # Select all
            self._select_all()
            event.prevent_default()
        elif event.key.lower() == "d":
            # Deselect all
            self._deselect_all()
            event.prevent_default()
    
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
    
    async def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button clicks"""
        if event.button.id == "remove-btn":
            self._remove_selected()
        elif event.button.id == "select-all-btn":
            self._select_all()
        elif event.button.id == "deselect-all-btn":
            self._deselect_all()
        elif event.button.id == "close-btn":
            self.dismiss()