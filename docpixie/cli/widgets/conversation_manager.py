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
        self.conversation_ids = []
        self.parent_dialog = None

    def compose(self):
        """Create the confirmation dialog"""
        with Container(id="confirm-container"):
            yield Static("[bold]Confirm Deletion[/bold]", classes="confirm-title")

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
            if self.conversation_ids and self.parent_dialog:
                self.parent_dialog.post_message(ConversationDeleted(self.conversation_ids))
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
        width: 66;
        height: auto;
        max-height: 35;
        min-height: 26;
        padding: 1;
        background: #2d1f2d;
        border: solid #ff99cc;
        overflow-y: auto;
    }

    .title {
        height: 1;
        margin: 0 0 1 0;
    }

    #conversation-list {
        height: 20;
        scrollbar-background: #2d1f2d;
        scrollbar-color: #ff99cc;
        scrollbar-size: 1 1;
        border: solid #4a3344;
        padding: 1;
        margin: 0;
        content-align: left top;
        text-align: left;
    }

    #no-conversations {
        height: 20;
        align: center middle;
        color: $text-muted;
        border: solid #4a3344;
        padding: 1;
        margin: 0;
    }

    .conversation-item {
        height: auto;
        padding: 0 0 0 1;
        margin: 0;
        content-align: left middle;
        text-align: left;
    }

    .conversation-content {
        text-align: left;
        width: 100%;
    }

    .conversation-item.--highlight {
        background: #4a3344;
        color: $text;
    }

    .conversation-item-selected {
        background: #4a3344;
        border-left: thick #ff99cc;
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
        self.multi_select_mode: bool = False

    def compose(self):
        """Create the conversation manager dialog"""
        with Container(id="dialog-container"):
            yield Static("[bold]💬 Conversation Manager[/bold]", classes="title", id="title")

            yield ListView(id="conversation-list")

            yield Static(
                "[dim]No conversations found in this project.[/dim]",
                id="no-conversations"
            )

            yield Static(id="selection-info", classes="info")

            yield Static(id="controls-hint")

    async def on_mount(self):
        """Load conversations when dialog mounts"""
        self._load_conversations()
        self._update_title()
        self._update_selection_info()
        self._update_controls_hint()

        self.focus()

    def _load_conversations(self):
        """Load and display conversations"""
        self.conversations = self.conversation_storage.list_local_conversations()

        list_view = self.query_one("#conversation-list", ListView)
        no_conv_msg = self.query_one("#no-conversations", Static)

        if not self.conversations:
            list_view.display = False
            no_conv_msg.display = True
            return

        list_view.display = True
        no_conv_msg.display = False

        list_view.clear()
        self.conversation_items = []

        for i, conv in enumerate(self.conversations):
            item_content = self._create_item_content(conv)

            list_item = ListItem(item_content, classes="conversation-item")
            list_item.data = conv.id

            if conv.id == self.current_conversation_id:
                list_item.add_class("conversation-item-current")

            list_view.append(list_item)
            self.conversation_items.append(list_item)

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
        display_text.justify = "left"

        if self.multi_select_mode:
            if conv.id in self.selected_items:
                display_text.append("[✓] ", style="green bold")
            else:
                display_text.append("[ ] ", style="dim")

        if conv.id == self.current_conversation_id:
            display_text.append("⭐ ", style="yellow")
        else:
            display_text.append("  ", style="dim")

        name = conv.name
        max_name_length = 30

        if len(name) > max_name_length:
            truncated_name = name[:max_name_length-3] + "..."
        else:
            truncated_name = name.ljust(max_name_length)

        display_text.append(truncated_name, style="bold")

        display_text.append("  ", style="dim")

        updated_time = datetime.fromisoformat(conv.updated_at)
        now = datetime.now()
        time_diff = now - updated_time

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

        display_text.append(f"{conv.message_count} msgs", style="dim cyan")
        display_text.append(" | ", style="dim")
        display_text.append(time_str, style="dim")

        return Static(display_text, classes="conversation-content")

    def _highlight_focused(self):
        """Highlight the currently focused conversation"""
        for item in self.conversation_items:
            item.remove_class("conversation-item-selected")

        if 0 <= self.focused_index < len(self.conversation_items):
            self.conversation_items[self.focused_index].add_class("conversation-item-selected")

            list_view = self.query_one("#conversation-list", ListView)
            list_view.scroll_to_widget(self.conversation_items[self.focused_index])

    def _toggle_selection(self, index: int):
        """Toggle selection for a conversation"""
        if not self.multi_select_mode:
            return

        if 0 <= index < len(self.conversations):
            conv = self.conversations[index]
            conv_id = conv.id

            if conv_id == self.current_conversation_id:
                self.app.notify("Cannot select the current conversation", severity="warning")
                return

            if conv_id in self.selected_items:
                self.selected_items.remove(conv_id)
            else:
                self.selected_items.add(conv_id)

            self._refresh_conversation_item(index)
            self._update_selection_info()

    def _refresh_all_conversation_items(self):
        """Refresh all conversation items (e.g., when mode changes)"""
        for i in range(len(self.conversation_items)):
            self._refresh_conversation_item(i)

    def _refresh_conversation_item(self, index: int):
        """Refresh a single conversation item display"""
        if 0 <= index < len(self.conversation_items):
            conv = self.conversations[index]
            list_item = self.conversation_items[index]

            new_content = self._create_item_content(conv)

            list_item.remove_children()
            list_item.mount(new_content)

    def _update_selection_info(self):
        """Update the selection info display"""
        info = self.query_one("#selection-info", Static)
        count = len(self.selected_items)

        if not self.multi_select_mode:
            info.update("[dim]Single-select mode[/dim]")
        else:
            if count == 0:
                info.update("[dim]Multi-select: No conversations selected[/dim]")
            elif count == 1:
                info.update(f"[yellow]Multi-select: 1 conversation selected[/yellow]")
            else:
                info.update(f"[yellow]Multi-select: {count} conversations selected[/yellow]")

    def _update_controls_hint(self):
        """Update the controls hint based on selection mode"""
        hint = self.query_one("#controls-hint", Static)
        if not self.multi_select_mode:
            hint.update(
                "[dim]↑↓[/dim] Navigate  [dim]Enter[/dim] Open  [dim]D/Delete[/dim] Delete  [dim]S[/dim] Toggle Select Mode  [dim]N[/dim] New  [dim]Esc[/dim] Close"
            )
        else:
            hint.update(
                "[dim]↑↓[/dim] Navigate  [dim]Space[/dim] Select/Deselect  [dim]L[/dim] Load Selected  [dim]D[/dim] Delete Selected  [dim]S[/dim] Exit Select Mode  [dim]Esc[/dim] Close"
            )

    async def _load_selected_conversation(self):
        """Load the first selected conversation (multi-select) or focused one (fallback)"""
        if self.multi_select_mode and self.selected_items:
            conv_id = next(iter(self.selected_items))
        elif 0 <= self.focused_index < len(self.conversations):
            conv_id = self.conversations[self.focused_index].id
        else:
            return

        self.post_message(ConversationSelected(conv_id))
        self.dismiss()

    async def _load_focused_conversation(self):
        """Load the focused conversation, ignoring any selections"""
        if 0 <= self.focused_index < len(self.conversations):
            conv_id = self.conversations[self.focused_index].id
            self.post_message(ConversationSelected(conv_id))
            self.dismiss()

    async def _delete_selected(self):
        """Delete selected conversations with confirmation"""
        if self.multi_select_mode:
            if not self.selected_items:
                self.app.notify("No conversations selected", severity="warning")
                return
            to_delete = list(self.selected_items)
        else:
            if 0 <= self.focused_index < len(self.conversations):
                conv = self.conversations[self.focused_index]
                if conv.id == self.current_conversation_id:
                    self.app.notify("Cannot delete the current conversation", severity="warning")
                    return
                to_delete = [conv.id]
            else:
                return

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
        event.prevent_default()
        event.stop()

        if event.key == "escape":
            self.dismiss()
        elif event.key == "up":
            self._move_focus_up()
        elif event.key == "down":
            self._move_focus_down()
        elif event.key == "enter":
            await self._load_focused_conversation()
        elif event.key == "space":
            self._toggle_selection(self.focused_index)
        elif event.key.lower() == "l":
            await self._load_selected_conversation()
        elif event.key.lower() == "d" or event.key == "delete" or event.key == "backspace":
            await self._delete_selected()
        elif event.key.lower() == "s":
            self.multi_select_mode = not self.multi_select_mode
            if not self.multi_select_mode and self.selected_items:
                self.selected_items.clear()
            self._refresh_all_conversation_items()
            self._update_selection_info()
            self._update_controls_hint()
        elif event.key.lower() == "n":
            self.post_message(ConversationSelected("new"))
            self.dismiss()

    async def on_conversation_deleted(self, event: ConversationDeleted) -> None:
        """Handle conversation deletion message"""
        deleted_count = 0
        for conv_id in event.conversation_ids:
            success = self.conversation_storage.delete_conversation(conv_id)
            if success:
                deleted_count += 1
                if conv_id in self.selected_items:
                    self.selected_items.remove(conv_id)

        if deleted_count == 1:
            self.app.notify("Deleted 1 conversation", severity="success")
        else:
            self.app.notify(f"Deleted {deleted_count} conversations", severity="success")

        self._load_conversations()
        self._update_title()
        self._update_selection_info()

    async def on_list_view_selected(self, event: ListView.Selected) -> None:
        """Handle list item click"""
        index = event.list_view.index
        if index is not None:
            self.focused_index = index
            self._highlight_focused()

            if self.multi_select_mode:
                self._toggle_selection(index)
