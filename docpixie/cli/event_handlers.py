"""
Event handling mixins for DocPixie CLI
"""

from typing import TYPE_CHECKING
from textual import events
from textual.widgets import TextArea, Label
from .widgets import (
    CommandPalette, CommandSelected, CommandAutoComplete,
    ConversationSelected, ConversationDeleted, 
    ModelSelected, DocumentRemoved, DocumentsIndexed,
    ChatArea
)

if TYPE_CHECKING:
    from .app import DocPixieTUI


class CommandEventMixin:
    """Handles command palette and text input events"""
    
    async def on_text_area_changed(self: 'DocPixieTUI', event: TextArea.Changed) -> None:
        """Handle text area changes for command palette"""
        if event.text_area.id != "chat-input":
            return

        lines = event.text_area.text.split('\\n')
        if lines:
            current_line = lines[-1] if lines else ""

            if current_line.startswith("/"):
                command_palette = self.query_one("#command-palette", CommandPalette)
                if not self.state_manager.command_palette_active:
                    self.state_manager.command_palette_active = True
                    command_palette.show(current_line)
                else:
                    command_palette.update_filter(current_line)
            else:
                if self.state_manager.command_palette_active:
                    command_palette = self.query_one("#command-palette", CommandPalette)
                    command_palette.hide()
                    self.state_manager.command_palette_active = False

    async def on_key(self: 'DocPixieTUI', event: events.Key) -> None:
        """Handle key events for command palette navigation"""
        if self.state_manager.command_palette_active:
            command_palette = self.query_one("#command-palette", CommandPalette)

            if event.key == "escape":
                command_palette.hide()
                self.state_manager.command_palette_active = False
                text_area = self.query_one("#chat-input")
                text_area.clear()
                event.prevent_default()

            elif event.key == "up":
                command_palette.move_selection_up()
                event.prevent_default()

            elif event.key == "down":
                command_palette.move_selection_down()
                event.prevent_default()

            elif event.key == "tab":
                selected = command_palette.get_selected_command()
                if selected:
                    text_area = self.query_one("#chat-input")
                    text_area.text = selected.command
                    text_area.cursor_location = (0, len(selected.command))
                event.prevent_default()

    async def on_command_selected(self: 'DocPixieTUI', event: CommandSelected) -> None:
        """Handle command selection from palette"""
        command_palette = self.query_one("#command-palette", CommandPalette)
        command_palette.hide()
        self.state_manager.command_palette_active = False

        text_area = self.query_one("#chat-input")
        text_area.clear()

        await self.handle_command(event.command)

    async def on_command_auto_complete(self: 'DocPixieTUI', event: CommandAutoComplete) -> None:
        """Handle command auto-completion"""
        text_area = self.query_one("#chat-input")
        text_area.text = event.command
        text_area.cursor_location = (0, len(event.command))


class ConversationEventMixin:
    """Handles conversation-related events"""

    async def on_conversation_selected(self: 'DocPixieTUI', event: ConversationSelected) -> None:
        """Handle conversation selection from dialog"""
        chat_log = self.query_one("#chat-log", ChatArea)

        if event.conversation_id == "new":
            await self.handle_command("/new")
            return

        try:
            self.state_manager.save_current_conversation()

            if self.state_manager.load_conversation(event.conversation_id):
                conversations = self.state_manager.conversation_storage.list_local_conversations()
                metadata = next(
                    (conv for conv in conversations if conv.id == event.conversation_id),
                    None
                )
                
                chat_log.clear()

                for msg in self.state_manager.conversation_history:
                    if msg.role == "user":
                        chat_log.add_user_message(msg.content)
                    else:
                        chat_log.add_assistant_message(msg.content)

                status_label = self.query_one("#status-label", Label)
                status_label.update(self.state_manager.get_status_text())

                conv_name = metadata.name if metadata else "Unknown"
                chat_log.write(f"[green bold]●[/green bold] Loaded conversation: {conv_name}\n\n")
            else:
                chat_log.write("[red bold]●[/red bold] Failed to load conversation\n\n")

        except Exception as e:
            chat_log.write(f"[red bold]●[/red bold] Error loading conversation: {e}\n\n")

    async def on_conversation_deleted(self: 'DocPixieTUI', event: ConversationDeleted) -> None:
        """Handle conversation deletion"""
        chat_log = self.query_one("#chat-log", ChatArea)
        chat_log.write("[green bold]●[/green bold] Conversation deleted\n\n")


class ModelEventMixin:
    """Handles model selection events"""

    async def on_model_selected(self: 'DocPixieTUI', event: ModelSelected) -> None:
        """Handle model selection"""
        chat_log = self.query_one("#chat-log", ChatArea)

        if event.old_text_model and event.text_model != event.old_text_model:
            chat_log.write(f"[green bold]●[/green bold] Planning model switched to {event.text_model}\n\n")
            await self.docpixie_manager.switch_models()
        elif event.old_vision_model and event.vision_model != event.old_vision_model:
            chat_log.write(f"[green bold]●[/green bold] Vision model switched to {event.vision_model}\n\n")
            await self.docpixie_manager.switch_models()
        else:
            chat_log.write("[dim]No model changes made[/dim]\n\n")

        status_label = self.query_one("#status-label", Label)
        status_label.update(self.state_manager.get_status_text())


class DocumentEventMixin:
    """Handles document management events"""

    async def on_document_removed(self: 'DocPixieTUI', event: DocumentRemoved) -> None:
        """Handle document removal"""
        chat_log = self.query_one("#chat-log", ChatArea)

        removed_count = 0
        for doc_id in event.document_ids:
            if self.state_manager.remove_document(doc_id):
                removed_count += 1

                if self.docpixie:
                    try:
                        success = self.docpixie_manager.delete_document_sync(doc_id)
                        if not success:
                            doc_name = f"Document {doc_id}"  # Fallback name
                            chat_log.write(f"[warning]Warning: Could not delete {doc_name} from storage[/warning]\n")
                    except Exception as e:
                        doc_name = f"Document {doc_id}"  # Fallback name
                        chat_log.write(f"[error]Error deleting {doc_name}: {e}[/error]\n")

        if removed_count == 1:
            chat_log.write(f"[green bold]●[/green bold] Removed 1 document from index\n\n")
        else:
            chat_log.write(f"[green bold]●[/green bold] Removed {removed_count} documents from index\n\n")

        status_label = self.query_one("#status-label", Label)
        status_label.update(self.state_manager.get_status_text())

    async def on_documents_indexed(self: 'DocPixieTUI', event: DocumentsIndexed) -> None:
        """Handle documents being indexed"""
        chat_log = self.query_one("#chat-log", ChatArea)

        indexed_count = 0
        for doc in event.documents:
            if not any(existing.id == doc.id for existing in self.state_manager.indexed_documents):
                self.state_manager.add_document(doc)
                indexed_count += 1

        if indexed_count == 1:
            chat_log.write(f"[green bold]●[/green bold] Successfully indexed 1 document\n\n")
        else:
            chat_log.write(f"[green bold]●[/green bold] Successfully indexed {indexed_count} documents\n\n")

        status_label = self.query_one("#status-label", Label)
        status_label.update(self.state_manager.get_status_text())