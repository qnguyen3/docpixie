"""
Command handling for DocPixie CLI
"""

from typing import TYPE_CHECKING, Optional
from pathlib import Path
from docpixie import DocPixie
from .state_manager import AppStateManager
from .widgets import (
    ConversationManagerDialog, ModelSelectorDialog, DocumentManagerDialog,
    ChatArea
)

if TYPE_CHECKING:
    from .app import DocPixieTUI


class CommandHandler:
    """Handles all slash commands for the CLI application"""
    
    def __init__(self, app: 'DocPixieTUI', state_manager: AppStateManager):
        self.app = app
        self.state_manager = state_manager
    
    async def handle_command(self, command: str) -> None:
        """Handle slash commands"""
        chat_log = self.app.query_one("#chat-log", ChatArea)
        
        if command == "/exit":
            self.state_manager.save_current_conversation()
            self.app.exit()
        
        elif command == "/new":
            await self._handle_new_command(chat_log)
        
        elif command == "/clear":
            self._handle_clear_command(chat_log)
        
        elif command == "/save":
            self._handle_save_command(chat_log)
        
        elif command == "/conversations":
            await self._handle_conversations_command()
        
        elif command == "/model":
            await self._handle_model_command()
        
        elif command == "/documents":
            await self._handle_documents_command()
        
        elif command == "/help":
            self._handle_help_command(chat_log)
        
        else:
            chat_log.write(f"[warning]Unknown command: {command}[/warning]\n")
            chat_log.write("Type /help for available commands\n\n")
    
    async def _handle_new_command(self, chat_log: ChatArea) -> None:
        """Handle /new command"""
        self.state_manager.save_current_conversation()
        self.state_manager.create_new_conversation()
        self.state_manager.clear_task_plan()
        
        chat_log.clear()
        self.app.show_welcome_message()
        chat_log.write("[green bold]●[/green bold] Started new conversation\n\n")
        
        status_label = self.app.query_one("#status-label")
        status_label.update(self.state_manager.get_status_text())
    
    def _handle_clear_command(self, chat_log: ChatArea) -> None:
        """Handle /clear command"""
        self.state_manager.clear_task_plan()
        chat_log.clear()
        self.app.show_welcome_message()
    
    def _handle_save_command(self, chat_log: ChatArea) -> None:
        """Handle /save command"""
        if self.state_manager.current_conversation_id and self.state_manager.conversation_history:
            self.state_manager.save_current_conversation()
            chat_log.write("[green bold]●[/green bold] Conversation saved!\n\n")
        else:
            chat_log.write("[warning]No conversation to save[/warning]\n\n")
    
    async def _handle_conversations_command(self) -> None:
        """Handle /conversations command"""
        await self.app.push_screen(ConversationManagerDialog(
            self.state_manager.current_conversation_id
        ))
    
    async def _handle_model_command(self) -> None:
        """Handle /model command"""
        await self.app.push_screen(ModelSelectorDialog())
    
    async def _handle_documents_command(self) -> None:
        """Handle /documents command"""
        await self.app.push_screen(DocumentManagerDialog(
            self.state_manager.documents_folder,
            self.app.docpixie
        ))
    
    def _handle_help_command(self, chat_log: ChatArea) -> None:
        """Handle /help command"""
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