"""
State management for DocPixie CLI application
"""

from pathlib import Path
from typing import List, Optional, Any, Set
from docpixie import ConversationMessage
from docpixie.models.document import Document
from .config import get_config_manager
from .conversation_storage import ConversationStorage


class AppStateManager:
    """Manages application state including conversations, documents, and UI state"""
    
    def __init__(self):
        self.indexed_documents: List[Document] = []
        self.conversation_history: List[ConversationMessage] = []
        self.current_conversation_id: Optional[str] = None
        self.documents_folder = Path("./documents")
        self.processing = False
        
        self.command_palette_active = False
        self.partial_command = ""
        self.default_input_hint = (
            "Press / for commands • Shift+Enter: new line • Shift+Tab: switch panel"
        )
        
        self.current_plan: Optional[Any] = None
        self.completed_tasks: Set = set()
        
        self.config_manager = get_config_manager()
        self.conversation_storage = ConversationStorage()
    
    def get_status_text(self) -> str:
        """Get current status bar text with emoji prefixes"""
        text_model, vision_model = self.config_manager.get_models()
        doc_count = len(self.indexed_documents)

        segments = [
            f"📄: {doc_count}",
            f"🧠: {text_model.split('/')[-1]}",
            f"👁️: {vision_model.split('/')[-1]}",
        ]

        if self.current_conversation_id:
            conversations = self.conversation_storage.list_local_conversations()
            current_conv = next(
                (conv for conv in conversations if conv.id == self.current_conversation_id),
                None,
            )
            if current_conv:
                # Conversation name (truncate to 20 chars, add ellipsis if longer)
                conv_name = current_conv.name[:20] + ("..." if len(current_conv.name) > 20 else "")
                segments.append(f"💬: {conv_name}")

                # Total cost formatting
                total_cost = getattr(current_conv, "total_cost", 0.0) or 0.0
                if total_cost < 0.01:
                    segments.append(f"💰: {total_cost:.6f}")
                else:
                    segments.append(f"💰: {total_cost:.4f}")

        return " | ".join(segments)
    
    def add_document(self, document: Document) -> None:
        """Add a document to the indexed documents list"""
        if not any(existing.id == document.id for existing in self.indexed_documents):
            self.indexed_documents.append(document)
    
    def remove_document(self, document_id: str) -> bool:
        """Remove a document from the indexed documents list"""
        for doc in self.indexed_documents[:]:
            if doc.id == document_id:
                self.indexed_documents.remove(doc)
                return True
        return False
    
    def clear_documents(self) -> None:
        """Clear all indexed documents"""
        self.indexed_documents.clear()
    
    def add_conversation_message(self, message: ConversationMessage) -> None:
        """Add a message to conversation history"""
        self.conversation_history.append(message)
    
    def limit_conversation_history(self, max_messages: int = 20) -> None:
        """Limit conversation history to maximum number of messages"""
        if len(self.conversation_history) > max_messages:
            self.conversation_history = self.conversation_history[-max_messages:]
    
    def clear_conversation_history(self) -> None:
        """Clear conversation history"""
        self.conversation_history = []
    
    def set_current_conversation(self, conversation_id: Optional[str]) -> None:
        """Set the current conversation ID"""
        self.current_conversation_id = conversation_id
    
    def create_new_conversation(self) -> str:
        """Create a new conversation and return its ID"""
        doc_ids = [doc.id for doc in self.indexed_documents]
        self.current_conversation_id = self.conversation_storage.create_new_conversation(doc_ids)
        self.conversation_history = []
        return self.current_conversation_id
    
    def load_conversation(self, conversation_id: str) -> bool:
        """Load a conversation by ID"""
        result = self.conversation_storage.load_conversation(conversation_id)
        if result:
            metadata, messages = result
            self.current_conversation_id = conversation_id
            self.conversation_history = messages
            return True
        return False
    
    def save_current_conversation(self) -> None:
        """Save the current conversation if it exists"""
        if self.current_conversation_id and self.conversation_history:
            doc_ids = [doc.id for doc in self.indexed_documents]
            self.conversation_storage.save_conversation(
                self.current_conversation_id,
                self.conversation_history,
                doc_ids
            )
    
    def get_last_conversation_id(self) -> Optional[str]:
        """Get the ID of the last conversation"""
        return self.conversation_storage.get_last_conversation()
    
    def set_processing(self, processing: bool) -> None:
        """Set processing state"""
        self.processing = processing
    
    def is_processing(self) -> bool:
        """Check if currently processing"""
        return self.processing
    
    def set_command_palette_active(self, active: bool) -> None:
        """Set command palette active state"""
        self.command_palette_active = active
    
    def is_command_palette_active(self) -> bool:
        """Check if command palette is active"""
        return self.command_palette_active
    
    def set_partial_command(self, command: str) -> None:
        """Set partial command text"""
        self.partial_command = command
    
    def get_partial_command(self) -> str:
        """Get partial command text"""
        return self.partial_command
    
    def set_current_plan(self, plan: Optional[Any]) -> None:
        """Set current task plan"""
        self.current_plan = plan
    
    def get_current_plan(self) -> Optional[Any]:
        """Get current task plan"""
        return self.current_plan
    
    def clear_task_plan(self) -> None:
        """Clear current task plan and completed tasks"""
        self.current_plan = None
        self.completed_tasks.clear()
    
    def add_completed_task(self, task_name: str) -> None:
        """Mark a task as completed"""
        self.completed_tasks.add(task_name)
    
    def get_completed_tasks(self) -> List[str]:
        """Get list of completed task names"""
        return list(self.completed_tasks)
    
    def has_documents(self) -> bool:
        """Check if any documents are indexed"""
        return len(self.indexed_documents) > 0
    
    def has_conversation_history(self) -> bool:
        """Check if conversation history exists"""
        return len(self.conversation_history) > 0
