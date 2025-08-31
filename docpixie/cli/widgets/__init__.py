"""
DocPixie CLI Widgets
"""

from .command_palette import CommandPalette, CommandSelected, CommandAutoComplete
from .conversation_manager import ConversationManagerDialog, ConversationSelected, ConversationDeleted
from .model_selector import ModelSelectorDialog, ModelSelected
from .document_manager import DocumentManagerDialog, DocumentRemoved, DocumentsIndexed

__all__ = [
    "CommandPalette", "CommandSelected", "CommandAutoComplete",
    "ConversationManagerDialog", "ConversationSelected", "ConversationDeleted",
    "ModelSelectorDialog", "ModelSelected",
    "DocumentManagerDialog", "DocumentRemoved", "DocumentsIndexed"
]