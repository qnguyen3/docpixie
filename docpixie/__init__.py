"""
DocPixie - Simplified Multimodal RAG Library

A lightweight, vision-based document question-answering system
that doesn't require vector databases or embedding models.
"""

__version__ = "0.1.0"

from .docpixie import DocPixie
from .models.document import Document, Page, QueryResult, QueryMode
from .models.agent import ConversationMessage
from .core.config import DocPixieConfig
from .providers import BaseProvider, create_provider

__all__ = [
    "DocPixie",
    "Document",
    "Page", 
    "QueryResult",
    "QueryMode",
    "ConversationMessage",
    "DocPixieConfig",
    "BaseProvider",
    "create_provider"
]