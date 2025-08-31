"""
Conversation list dialog for DocPixie CLI
Shows all local conversations and allows switching between them
"""

from typing import List, Optional
from datetime import datetime
from textual.widgets import Static, ListView, ListItem, Label, Button
from textual.containers import Container, Vertical, Horizontal
from textual.screen import ModalScreen
from textual.message import Message
from textual import events
from rich.text import Text
from rich.table import Table

from ..conversation_storage import ConversationStorage, ConversationMetadata


class ConversationSelected(Message):
    """Message sent when a conversation is selected"""
    
    def __init__(self, conversation_id: str):
        self.conversation_id = conversation_id
        super().__init__()


class ConversationDeleted(Message):
    """Message sent when a conversation is deleted"""
    
    def __init__(self, conversation_id: str):
        self.conversation_id = conversation_id
        super().__init__()


class ConversationListDialog(ModalScreen):
    """Modal dialog for managing conversations"""
    
    CSS = """
    ConversationListDialog {
        align: center middle;
    }
    
    #dialog-container {
        width: 80;
        height: 25;
        padding: 2;
        background: $surface;
        border: solid $primary;
    }
    
    #conversation-list {
        height: 18;
        scrollbar-background: $panel;
        scrollbar-color: $primary;
        border: solid $accent;
        margin: 1 0;
    }
    
    .conversation-item {
        height: auto;
        min-height: 3;
        padding: 1;
        margin: 0 0 1 0;
        border: solid $panel;
    }
    
    .conversation-item.--highlight {
        background: $accent;
        color: $text;
    }
    
    .conversation-item-selected {
        background: $primary;
        color: $text;
        border: solid $success;
    }
    
    .conversation-item-current {
        border: solid $warning;
        background: $warning 20%;
    }
    
    #button-container {
        align: center middle;
        margin-top: 1;
    }
    
    #no-conversations {
        align: center middle;
        height: 100%;
        color: $text-muted;
    }
    
    .conversation-meta {
        color: $text-muted;
        margin-top: 1;
    }
    """
    
    def __init__(self, current_conversation_id: Optional[str] = None):
        super().__init__()
        self.conversation_storage = ConversationStorage()
        self.conversations: List[ConversationMetadata] = []
        self.selected_index = 0
        self.current_conversation_id = current_conversation_id
        self.conversation_items: List[ListItem] = []
    
    def compose(self):
        """Create the conversation list dialog"""
        with Container(id="dialog-container"):
            yield Static("[bold]💬 Local Conversations[/bold]\n", classes="title")
            
            # Instructions
            yield Static(
                "Select a conversation to load. Current conversation marked with ⭐\n",
                classes="instructions"
            )
            
            # Conversation list
            yield ListView(id="conversation-list")
            
            # Empty state message (initially hidden)
            yield Static(
                "[dim]No conversations found in this directory.\nStart a new conversation to create one![/dim]",
                id="no-conversations"
            )
            
            # Action buttons
            with Horizontal(id="button-container"):
                yield Button("Load Selected", variant="primary", id="load-btn")
                yield Button("Delete Selected", variant="error", id="delete-btn")
                yield Button("New Conversation", variant="success", id="new-btn")
                yield Button("Cancel", variant="default", id="cancel-btn")
    
    def on_mount(self):
        """Load conversations when dialog mounts"""
        self._load_conversations()
    
    def _load_conversations(self):
        """Load and display conversations"""
        self.conversations = self.conversation_storage.list_local_conversations()
        
        list_view = self.query_one("#conversation-list", ListView)
        no_conv_msg = self.query_one("#no-conversations", Static)
        
        if not self.conversations:
            # Show empty state
            list_view.display = False
            no_conv_msg.display = True
            
            # Disable load and delete buttons
            self.query_one("#load-btn", Button).disabled = True
            self.query_one("#delete-btn", Button).disabled = True
            return
        
        # Hide empty state, show list
        list_view.display = True
        no_conv_msg.display = False
        
        # Enable buttons
        self.query_one("#load-btn", Button).disabled = False
        self.query_one("#delete-btn", Button).disabled = False
        
        # Clear existing items
        list_view.clear()
        self.conversation_items = []
        
        # Add conversation items
        for i, conv in enumerate(self.conversations):
            # Create conversation item content
            item_content = self._create_conversation_content(conv)
            
            # Create list item with styling
            list_item = ListItem(item_content, classes="conversation-item")
            
            # Mark current conversation
            if conv.id == self.current_conversation_id:
                list_item.add_class("conversation-item-current")
            
            list_view.append(list_item)
            self.conversation_items.append(list_item)
        
        # Select the first item
        self.selected_index = 0
        self._highlight_selected()
    
    def _create_conversation_content(self, conv: ConversationMetadata) -> Vertical:
        """Create content for a conversation item"""
        # Conversation name with current marker
        name_text = Text()
        if conv.id == self.current_conversation_id:
            name_text.append("⭐ ", style="yellow")
        name_text.append(conv.name, style="bold white")
        
        # Metadata
        created_date = datetime.fromisoformat(conv.created_at).strftime("%Y-%m-%d %H:%M")
        updated_date = datetime.fromisoformat(conv.updated_at).strftime("%Y-%m-%d %H:%M")
        
        meta_text = Text()
        meta_text.append(f"Created: {created_date}", style="dim")
        meta_text.append(f" | Updated: {updated_date}", style="dim")
        meta_text.append(f" | {conv.message_count} messages", style="dim")
        
        if conv.indexed_documents:
            meta_text.append(f" | {len(conv.indexed_documents)} docs", style="dim")
        
        # Create and return the container with both elements
        container = Vertical(
            Static(name_text),
            Static(meta_text, classes="conversation-meta")
        )
        return container
    
    def _highlight_selected(self):
        """Highlight the currently selected conversation"""
        # Remove previous highlights
        for item in self.conversation_items:
            item.remove_class("conversation-item-selected")
        
        # Highlight current selection
        if 0 <= self.selected_index < len(self.conversation_items):
            self.conversation_items[self.selected_index].add_class("conversation-item-selected")
            
            # Scroll to selected item
            list_view = self.query_one("#conversation-list", ListView)
            list_view.scroll_to_widget(self.conversation_items[self.selected_index])
    
    def _move_selection_up(self):
        """Move selection up"""
        if self.conversations:
            self.selected_index = max(0, self.selected_index - 1)
            self._highlight_selected()
    
    def _move_selection_down(self):
        """Move selection down"""
        if self.conversations:
            self.selected_index = min(len(self.conversations) - 1, self.selected_index + 1)
            self._highlight_selected()
    
    def _get_selected_conversation(self) -> Optional[ConversationMetadata]:
        """Get the currently selected conversation"""
        if 0 <= self.selected_index < len(self.conversations):
            return self.conversations[self.selected_index]
        return None
    
    def _load_selected_conversation(self):
        """Load the selected conversation"""
        selected = self._get_selected_conversation()
        if selected:
            self.post_message(ConversationSelected(selected.id))
            self.dismiss()
    
    def _delete_selected_conversation(self):
        """Delete the selected conversation"""
        selected = self._get_selected_conversation()
        if selected:
            # Don't allow deleting current conversation
            if selected.id == self.current_conversation_id:
                self.notify("Cannot delete the current conversation", severity="warning")
                return
            
            # Delete the conversation
            success = self.conversation_storage.delete_conversation(selected.id)
            if success:
                self.post_message(ConversationDeleted(selected.id))
                self.notify(f"Deleted conversation: {selected.name}", severity="success")
                # Reload the list
                self._load_conversations()
            else:
                self.notify("Failed to delete conversation", severity="error")
    
    async def on_key(self, event: events.Key) -> None:
        """Handle key events"""
        if event.key == "escape":
            self.dismiss()
            event.prevent_default()
        elif event.key == "up":
            self._move_selection_up()
            event.prevent_default()
        elif event.key == "down":
            self._move_selection_down()
            event.prevent_default()
        elif event.key == "enter":
            self._load_selected_conversation()
            event.prevent_default()
        elif event.key == "delete":
            self._delete_selected_conversation()
            event.prevent_default()
        elif event.key.lower() == "d":
            self._delete_selected_conversation()
            event.prevent_default()
        elif event.key.lower() == "n":
            # New conversation
            self.post_message(ConversationSelected("new"))
            self.dismiss()
            event.prevent_default()
    
    async def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button clicks"""
        if event.button.id == "load-btn":
            self._load_selected_conversation()
        
        elif event.button.id == "delete-btn":
            self._delete_selected_conversation()
        
        elif event.button.id == "new-btn":
            self.post_message(ConversationSelected("new"))
            self.dismiss()
        
        elif event.button.id == "cancel-btn":
            self.dismiss()