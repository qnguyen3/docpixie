"""
Base storage interface for documents
"""

from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any
import logging

from ..models.document import Document, Page

logger = logging.getLogger(__name__)


class BaseStorage(ABC):
    """Base class for storage backends"""
    
    @abstractmethod
    async def save_document(self, document: Document) -> str:
        """
        Save a processed document
        
        Args:
            document: Document to save
            
        Returns:
            Document ID
        """
        pass
    
    @abstractmethod
    async def get_document(self, document_id: str) -> Optional[Document]:
        """
        Retrieve a document by ID
        
        Args:
            document_id: ID of document to retrieve
            
        Returns:
            Document or None if not found
        """
        pass
    
    @abstractmethod
    async def list_documents(self, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        List all documents with metadata
        
        Args:
            limit: Maximum number of documents to return
            
        Returns:
            List of document metadata dicts
        """
        pass
    
    @abstractmethod
    async def delete_document(self, document_id: str) -> bool:
        """
        Delete a document and its associated files
        
        Args:
            document_id: ID of document to delete
            
        Returns:
            True if deletion was successful
        """
        pass
    
    @abstractmethod
    async def document_exists(self, document_id: str) -> bool:
        """
        Check if document exists
        
        Args:
            document_id: Document ID to check
            
        Returns:
            True if document exists
        """
        pass
    
    @abstractmethod
    async def get_document_summary(self, document_id: str) -> Optional[str]:
        """
        Get document summary without loading full document
        
        Args:
            document_id: Document ID
            
        Returns:
            Document summary or None
        """
        pass
    
    @abstractmethod
    async def update_document_summary(self, document_id: str, summary: str) -> bool:
        """
        Update document summary
        
        Args:
            document_id: Document ID
            summary: New summary text
            
        Returns:
            True if update was successful
        """
        pass
    
    @abstractmethod
    async def get_all_documents(self) -> List[Document]:
        """
        Get all documents for agent processing
        
        Returns:
            List of all documents in storage
        """
        pass
    
    @abstractmethod
    async def get_all_pages(self) -> List[Page]:
        """
        Get all pages from all documents for agent processing
        
        Returns:
            List of all pages across all documents
        """
        pass
    
    async def get_documents_by_ids(self, document_ids: List[str]) -> List[Document]:
        """
        Get multiple documents by IDs
        
        Args:
            document_ids: List of document IDs
            
        Returns:
            List of documents (may be fewer than requested if some not found)
        """
        documents = []
        for doc_id in document_ids:
            doc = await self.get_document(doc_id)
            if doc:
                documents.append(doc)
        return documents
    
    async def search_documents(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Simple text search in document names and summaries
        Default implementation - subclasses can override for better search
        
        Args:
            query: Search query
            limit: Maximum results
            
        Returns:
            List of matching document metadata
        """
        all_docs = await self.list_documents()
        matching_docs = []
        query_lower = query.lower()
        
        for doc_meta in all_docs:
            name_match = query_lower in doc_meta.get('name', '').lower()
            summary_match = query_lower in doc_meta.get('summary', '').lower()
            
            if name_match or summary_match:
                matching_docs.append(doc_meta)
            
            if len(matching_docs) >= limit:
                break
        
        return matching_docs
    
    def get_storage_stats(self) -> Dict[str, Any]:
        """
        Get storage statistics
        Default implementation - subclasses can override
        
        Returns:
            Dictionary with storage statistics
        """
        return {
            'backend': self.__class__.__name__,
            'features': ['basic_storage']
        }


class StorageError(Exception):
    """Exception raised by storage operations"""
    
    def __init__(self, message: str, document_id: Optional[str] = None):
        self.document_id = document_id
        super().__init__(message)