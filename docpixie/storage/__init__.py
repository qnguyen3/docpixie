"""Storage backends for documents and metadata"""

from .base import BaseStorage
from .local import LocalStorage
from .memory import InMemoryStorage

__all__ = [
    "BaseStorage",
    "LocalStorage",
    "InMemoryStorage"
]