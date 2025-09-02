"""
DocPixie CLI Widgets
"""

from .command_palette import DocPixieCommandPalette as CommandPalette, CommandSelected, CommandAutoComplete
from .conversation_manager import ConversationManagerDialog, ConversationSelected, ConversationDeleted
from .model_selector import ModelSelectorDialog, ModelSelected
from .document_manager import DocumentManagerDialog, DocumentRemoved, DocumentsIndexed
from .chat_area import ChatArea

__all__ = [
    "CommandPalette", "CommandSelected", "CommandAutoComplete",
    "ConversationManagerDialog", "ConversationSelected", "ConversationDeleted",
    "ModelSelectorDialog", "ModelSelected",
    "DocumentManagerDialog", "DocumentRemoved", "DocumentsIndexed",
    "ChatArea"
]