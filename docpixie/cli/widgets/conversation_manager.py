"""
Conversation manager dialog for DocPixie CLI
Allows users to view and manage all conversations with a compact design
"""

import asyncio
from typing import List, Optional, Set
from datetime import datetime
from textual.widgets import Static, ListView, ListItem, Label
from textual.containers import Container, Horizontal, Vertical
from textual.screen import ModalScreen
from textual.message import Message
from textual import events
from rich.text import Text

from ..conversation_storage import ConversationStorage, ConversationMetadata


class ConversationSelected(Message):
    """Message sent when a conversation is selected"""
    
    def __init__(self, conversation_id: str):
        self.conversation_id = conversation_id
        super().__init__()


class ConversationDeleted(Message):
    """Message sent when conversations are deleted"""
    
    def __init__(self, conversation_ids: List[str]):
        self.conversation_ids = conversation_ids
        super().__init__()


class DeletionConfirmDialog(ModalScreen):
    """Modal dialog to confirm conversation deletion"""

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

    def __init__(self, conversation_count: int):
        super().__init__()
        self.conversation_count = conversation_count
        self.confirmed = False
        self.conversation_ids = []  # Will be set by parent dialog
        self.parent_dialog = None  # Reference to parent ConversationManagerDialog

    def compose(self):
        """Create the confirmation dialog"""
        with Container(id="confirm-container"):
            yield Static("[bold]⚠️ Confirm Deletion[/bold]", classes="confirm-title")

            if self.conversation_count == 1:
                message = "Are you sure you want to delete 1 conversation?"
            else:
                message = f"Are you sure you want to delete {self.conversation_count} conversations?"

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
            # Send removal message if we have conversation IDs
            if self.conversation_ids and self.parent_dialog:
                self.parent_dialog.post_message(ConversationDeleted(self.conversation_ids))
            # Only dismiss the confirmation dialog, not the parent
            self.dismiss()
        elif event.key.lower() == "n" or event.key == "escape":
            self.confirmed = False
            self.dismiss()


class ConversationManagerDialog(ModalScreen):
    """Modal dialog for managing conversations with compact design"""

    CSS = """
    ConversationManagerDialog {
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

    #conversation-list {
        height: 20;
        scrollbar-background: $panel;
        scrollbar-color: $primary;
        scrollbar-size: 1 1;
        border: solid $accent;
        padding: 1;
        margin: 0;
    }

    #no-conversations {
        height: 20;
        align: center middle;
        color: $text-muted;
        border: solid $accent;
        padding: 1;
        margin: 0;
    }

    .conversation-item {
        height: auto;
        padding: 0 1;
        margin: 0;
    }

    .conversation-item.--highlight {
        background: $primary;
        color: $text;
    }

    .conversation-item-selected {
        background: $success 30%;
        border-left: thick $success;
    }

    .conversation-item-current {
        background: $warning 20%;
    }

    .conversation-meta {
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

    def __init__(self, current_conversation_id: Optional[str] = None):
        super().__init__()
        self.conversation_storage = ConversationStorage()
        self.conversations: List[ConversationMetadata] = []
        self.current_conversation_id = current_conversation_id
        self.selected_items: Set[str] = set()  # Conversation IDs
        self.conversation_items: List[ListItem] = []
        self.focused_index = 0

    def compose(self):
        """Create the conversation manager dialog"""
        with Container(id="dialog-container"):
            # Title (will be updated with counts)
            yield Static("[bold]💬 Conversation Manager[/bold]", classes="title", id="title")

            # Conversation list
            yield ListView(id="conversation-list")

            # Empty state message (initially hidden)
            yield Static(
                "[dim]No conversations found in this project.[/dim]",
                id="no-conversations"
            )

            # Selection info
            yield Static(id="selection-info", classes="info")
            
            # Control hints
            yield Static(
                "[dim]↑↓[/dim] Navigate  [dim]Enter/Space[/dim] Toggle  [dim]L[/dim] Load Selected  [dim]D[/dim] Delete Selected  [dim]N[/dim] New Conversation  [dim]Esc[/dim] Close",
                id="controls-hint"
            )

    async def on_mount(self):
        """Load conversations when dialog mounts"""
        self._load_conversations()
        self._update_title()
        self._update_selection_info()
        
        # Set initial focus to the dialog itself
        self.focus()

    def _load_conversations(self):
        """Load and display conversations"""
        self.conversations = self.conversation_storage.list_local_conversations()
        
        list_view = self.query_one("#conversation-list", ListView)
        no_conv_msg = self.query_one("#no-conversations", Static)

        if not self.conversations:
            # Show empty state
            list_view.display = False
            no_conv_msg.display = True
            return

        # Hide empty state, show list
        list_view.display = True
        no_conv_msg.display = False

        # Clear existing items
        list_view.clear()
        self.conversation_items = []

        # Add conversation items
        for i, conv in enumerate(self.conversations):
            # Create conversation item content
            item_content = self._create_item_content(conv)

            # Create list item
            list_item = ListItem(item_content, classes="conversation-item")
            # Store conversation ID for reference
            list_item.data = conv.id

            # Mark current conversation
            if conv.id == self.current_conversation_id:
                list_item.add_class("conversation-item-current")

            list_view.append(list_item)
            self.conversation_items.append(list_item)

        # Focus first item
        if self.conversation_items:
            self.focused_index = 0
            self._highlight_focused()

    def _update_title(self):
        """Update the title with conversation count"""
        title = self.query_one("#title", Static)
        total = len(self.conversations)
        
        if total == 0:
            title.update(f"[bold]💬 Conversation Manager - No conversations[/bold]")
        elif total == 1:
            title.update(f"[bold]💬 Conversation Manager - 1 conversation[/bold]")
        else:
            title.update(f"[bold]💬 Conversation Manager - {total} conversations[/bold]")

    def _create_item_content(self, conv: ConversationMetadata) -> Static:
        """Create content for a conversation item (compact design)"""
        display_text = Text()
        
        # Column 1: Selection checkbox (4 chars)
        if conv.id in self.selected_items:
            display_text.append("[✓] ", style="green bold")
        else:
            display_text.append("[ ] ", style="dim")
        
        # Column 2: Current marker (3 chars)
        if conv.id == self.current_conversation_id:
            display_text.append("⭐ ", style="yellow")
        else:
            display_text.append("   ", style="dim")
        
        # Column 3: Conversation name (30 chars fixed width to prevent wrapping)
        name = conv.name
        max_name_length = 30
        
        if len(name) > max_name_length:
            # Truncate with ellipsis
            truncated_name = name[:max_name_length-3] + "..."
        else:
            # Pad with spaces to maintain alignment
            truncated_name = name.ljust(max_name_length)
        
        display_text.append(truncated_name, style="bold")
        
        # Column 4: Metadata (right side)
        display_text.append("  ", style="dim")  # Spacing
        
        # Format time as relative
        updated_time = datetime.fromisoformat(conv.updated_at)
        now = datetime.now()
        time_diff = now - updated_time
        
        # Calculate relative time
        if time_diff.total_seconds() < 60:
            time_str = "just now"
        elif time_diff.total_seconds() < 3600:
            minutes = int(time_diff.total_seconds() / 60)
            time_str = f"{minutes}m ago"
        elif time_diff.total_seconds() < 86400:
            hours = int(time_diff.total_seconds() / 3600)
            time_str = f"{hours}h ago"
        elif time_diff.days < 7:
            time_str = f"{time_diff.days}d ago"
        elif time_diff.days < 30:
            weeks = int(time_diff.days / 7)
            time_str = f"{weeks}w ago"
        else:
            months = int(time_diff.days / 30)
            time_str = f"{months}mo ago"
        
        # Add metadata
        display_text.append(f"{conv.message_count} msgs", style="dim cyan")
        display_text.append(" | ", style="dim")
        display_text.append(time_str, style="dim")
        
        if conv.indexed_documents:
            display_text.append(" | ", style="dim")
            display_text.append(f"{len(conv.indexed_documents)} docs", style="dim green")

        return Static(display_text)

    def _highlight_focused(self):
        """Highlight the currently focused conversation"""
        # Remove previous highlights
        for item in self.conversation_items:
            item.remove_class("conversation-item-selected")

        # Highlight current focus
        if 0 <= self.focused_index < len(self.conversation_items):
            self.conversation_items[self.focused_index].add_class("conversation-item-selected")

            # Scroll to focused item
            list_view = self.query_one("#conversation-list", ListView)
            list_view.scroll_to_widget(self.conversation_items[self.focused_index])

    def _toggle_selection(self, index: int):
        """Toggle selection for a conversation"""
        if 0 <= index < len(self.conversations):
            conv = self.conversations[index]
            conv_id = conv.id

            # Don't allow selecting current conversation for deletion
            if conv_id == self.current_conversation_id:
                self.app.notify("Cannot select the current conversation", severity="warning")
                return

            if conv_id in self.selected_items:
                self.selected_items.remove(conv_id)
            else:
                self.selected_items.add(conv_id)

            # Update display
            self._refresh_conversation_item(index)
            self._update_selection_info()

    def _refresh_conversation_item(self, index: int):
        """Refresh a single conversation item display"""
        if 0 <= index < len(self.conversation_items):
            conv = self.conversations[index]
            list_item = self.conversation_items[index]

            # Recreate content
            new_content = self._create_item_content(conv)

            # Replace content in the list item
            list_item.remove_children()
            list_item.mount(new_content)

    def _update_selection_info(self):
        """Update the selection info display"""
        info = self.query_one("#selection-info", Static)
        count = len(self.selected_items)

        if count == 0:
            info.update("[dim]No conversations selected[/dim]")
        elif count == 1:
            info.update(f"[yellow]1 conversation selected[/yellow]")
        else:
            info.update(f"[yellow]{count} conversations selected[/yellow]")

    async def _load_selected_conversation(self):
        """Load the first selected conversation or the focused one"""
        if self.selected_items:
            # Load the first selected conversation
            conv_id = next(iter(self.selected_items))
        elif 0 <= self.focused_index < len(self.conversations):
            # Load the focused conversation
            conv_id = self.conversations[self.focused_index].id
        else:
            return

        self.post_message(ConversationSelected(conv_id))
        self.dismiss()

    async def _delete_selected(self):
        """Delete selected conversations with confirmation"""
        if not self.selected_items:
            # If nothing selected, try to delete the focused item
            if 0 <= self.focused_index < len(self.conversations):
                conv = self.conversations[self.focused_index]
                if conv.id == self.current_conversation_id:
                    self.app.notify("Cannot delete the current conversation", severity="warning")
                    return
                to_delete = [conv.id]
            else:
                return
        else:
            to_delete = list(self.selected_items)

        # Show confirmation dialog
        confirm_dialog = DeletionConfirmDialog(len(to_delete))
        confirm_dialog.conversation_ids = to_delete
        confirm_dialog.parent_dialog = self
        self.app.push_screen(confirm_dialog)

    def _move_focus_up(self):
        """Move focus up"""
        if self.conversations and self.focused_index > 0:
            self.focused_index -= 1
            self._highlight_focused()

    def _move_focus_down(self):
        """Move focus down"""
        if self.conversations and self.focused_index < len(self.conversations) - 1:
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
        elif event.key.lower() == "l":
            # Load selected or focused conversation
            await self._load_selected_conversation()
        elif event.key.lower() == "d":
            # Delete selected conversations with confirmation
            await self._delete_selected()
        elif event.key.lower() == "n":
            # New conversation
            self.post_message(ConversationSelected("new"))
            self.dismiss()

    async def on_conversation_deleted(self, event: ConversationDeleted) -> None:
        """Handle conversation deletion message"""
        # Delete the conversations
        deleted_count = 0
        for conv_id in event.conversation_ids:
            success = self.conversation_storage.delete_conversation(conv_id)
            if success:
                deleted_count += 1
                # Remove from selected items
                if conv_id in self.selected_items:
                    self.selected_items.remove(conv_id)

        if deleted_count == 1:
            self.app.notify("Deleted 1 conversation", severity="success")
        else:
            self.app.notify(f"Deleted {deleted_count} conversations", severity="success")

        # Reload the list
        self._load_conversations()
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