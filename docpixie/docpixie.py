"""
Main DocPixie API class
Simplified multimodal RAG without embeddings or vector databases
"""

import asyncio
from typing import Optional, List, Dict, Any, Union
from pathlib import Path
import logging

from .models.document import (
    Document, Page, QueryResult, QueryMode, 
    DocumentProcessRequest, QueryRequest, DocumentStatus
)
from .core.config import DocPixieConfig
from .processors.factory import ProcessorFactory
from .storage.local import LocalStorage
from .storage.memory import InMemoryStorage
from .storage.base import BaseStorage
from .ai.summarizer import PageSummarizer
from .providers import create_provider
from .utils.async_helpers import sync_wrapper, make_sync_version

logger = logging.getLogger(__name__)


class DocPixie:
    """
    Main DocPixie API class for multimodal RAG
    
    Provides both Flash (quick) and Pro (comprehensive) modes
    without requiring vector databases or embeddings.
    """
    
    def __init__(
        self,
        config: Optional[DocPixieConfig] = None,
        storage: Optional[BaseStorage] = None,
        api_key: Optional[str] = None
    ):
        """
        Initialize DocPixie
        
        Args:
            config: Configuration object (uses defaults if None)
            storage: Storage backend (uses local storage if None)  
            api_key: API key for AI provider (can also use env vars)
        """
        # Initialize configuration
        if config is None:
            config = DocPixieConfig()
        
        # Override API key if provided
        if api_key:
            if config.provider == "openai":
                config.openai_api_key = api_key
            elif config.provider == "anthropic":
                config.anthropic_api_key = api_key
        
        self.config = config
        
        # Initialize components
        self.processor_factory = ProcessorFactory(config)
        
        # Initialize storage
        if storage is None:
            if config.storage_type == "memory":
                self.storage = InMemoryStorage(config)
            else:
                self.storage = LocalStorage(config)
        else:
            self.storage = storage
        
        # Initialize AI components
        self.summarizer = PageSummarizer(config)
        
        logger.info(f"Initialized DocPixie with {config.provider} provider and {type(self.storage).__name__} storage")
    
    # Document Management
    
    async def add_document(
        self,
        file_path: Union[str, Path],
        document_id: Optional[str] = None,
        document_name: Optional[str] = None,
        summarize: bool = True
    ) -> Document:
        """
        Add a document to the RAG system
        
        Args:
            file_path: Path to document file (PDF, image, etc.)
            document_id: Optional custom document ID
            document_name: Optional custom document name
            summarize: Whether to generate page summaries
            
        Returns:
            Processed Document object
        """
        file_path = str(file_path)
        logger.info(f"Adding document: {file_path}")
        
        # Process document
        processor = self.processor_factory.get_processor(file_path)
        document = await processor.process(file_path, document_id)
        
        # Override name if provided
        if document_name:
            document.name = document_name
        
        # Generate page summaries if requested
        if summarize and self.config.page_summary_enabled:
            logger.info(f"Generating summaries for {len(document.pages)} pages")
            document = await self.summarizer.summarize_document(document)
        
        # Save to storage
        document.status = DocumentStatus.COMPLETED
        await self.storage.save_document(document)
        
        logger.info(f"Successfully added document {document.id}: {document.name}")
        return document
    
    async def get_document(self, document_id: str) -> Optional[Document]:
        """Get a document by ID"""
        return await self.storage.get_document(document_id)
    
    async def list_documents(self, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """List all documents with metadata"""
        return await self.storage.list_documents(limit)
    
    async def delete_document(self, document_id: str) -> bool:
        """Delete a document and its associated files"""
        return await self.storage.delete_document(document_id)
    
    async def search_documents(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Search documents by name and summary"""
        return await self.storage.search_documents(query, limit)
    
    # Query Processing (Phase 2 - TODO: Will implement vision-based RAG)
    
    async def query(
        self,
        question: str,
        mode: QueryMode = QueryMode.AUTO,
        document_ids: Optional[List[str]] = None,
        max_pages: Optional[int] = None,
        stream: bool = False
    ) -> QueryResult:
        """
        Query documents with a question
        
        Args:
            question: User's question
            mode: Query mode (Flash, Pro, or Auto)
            document_ids: Specific documents to search (None = all)
            max_pages: Maximum pages to analyze
            stream: Whether to stream the response
            
        Returns:
            QueryResult with answer and metadata
            
        Note: This is a Phase 1 placeholder. Full implementation in Phase 2.
        """
        logger.info(f"Query: {question} (mode: {mode})")
        
        # For Phase 1, return a placeholder response
        # Phase 2 will implement vision-based page selection and answer generation
        
        # Get documents to search
        if document_ids:
            documents = await self.storage.get_documents_by_ids(document_ids)
        else:
            doc_metadata = await self.list_documents()
            document_ids = [doc['id'] for doc in doc_metadata]
            documents = await self.storage.get_documents_by_ids(document_ids)
        
        if not documents:
            return QueryResult(
                query=question,
                answer="No documents found to search.",
                selected_pages=[],
                mode=mode,
                confidence=0.0,
                metadata={'documents_searched': 0}
            )
        
        # Placeholder: return first few pages from first document
        # Phase 2 will implement proper vision-based selection
        first_doc = documents[0]
        selected_pages = first_doc.pages[:3]  # Temporary placeholder
        
        return QueryResult(
            query=question,
            answer=f"[Phase 1 Placeholder] Found {len(documents)} documents to search. Question: '{question}'. This will be implemented in Phase 2 with vision-based page selection and answer generation.",
            selected_pages=selected_pages,
            mode=mode,
            confidence=0.8,
            metadata={
                'documents_searched': len(documents),
                'total_pages_available': sum(len(doc.pages) for doc in documents),
                'phase': 'Phase 1 - Basic functionality'
            }
        )
    
    # Convenience Methods
    
    def supports_file(self, file_path: str) -> bool:
        """Check if file type is supported"""
        return self.processor_factory.supports_file(file_path)
    
    def get_supported_extensions(self) -> Dict[str, str]:
        """Get all supported file extensions"""
        return self.processor_factory.get_supported_extensions()
    
    def get_stats(self) -> Dict[str, Any]:
        """Get system statistics"""
        storage_stats = self.storage.get_storage_stats()
        summarizer_stats = self.summarizer.get_summary_stats()
        
        return {
            'docpixie_version': '0.1.0',
            'config': {
                'provider': self.config.provider,
                'storage_type': self.config.storage_type,
                'flash_max_pages': self.config.flash_max_pages,
                'pro_max_pages': self.config.pro_max_pages
            },
            'storage': storage_stats,
            'summarizer': summarizer_stats,
            'supported_extensions': list(self.get_supported_extensions().keys())
        }
    
    # Synchronous API for easier adoption
    
    def add_document_sync(
        self,
        file_path: Union[str, Path],
        document_id: Optional[str] = None,
        document_name: Optional[str] = None,
        summarize: bool = True
    ) -> Document:
        """Synchronous version of add_document"""
        return sync_wrapper(self.add_document(file_path, document_id, document_name, summarize))
    
    def get_document_sync(self, document_id: str) -> Optional[Document]:
        """Synchronous version of get_document"""
        return sync_wrapper(self.get_document(document_id))
    
    def list_documents_sync(self, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """Synchronous version of list_documents"""
        return sync_wrapper(self.list_documents(limit))
    
    def delete_document_sync(self, document_id: str) -> bool:
        """Synchronous version of delete_document"""
        return sync_wrapper(self.delete_document(document_id))
    
    def query_sync(
        self,
        question: str,
        mode: QueryMode = QueryMode.AUTO,
        document_ids: Optional[List[str]] = None,
        max_pages: Optional[int] = None
    ) -> QueryResult:
        """Synchronous version of query"""
        return sync_wrapper(self.query(question, mode, document_ids, max_pages, stream=False))
    
    def search_documents_sync(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Synchronous version of search_documents"""
        return sync_wrapper(self.search_documents(query, limit))
    
    # Context manager support
    
    async def __aenter__(self):
        """Async context manager entry"""
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        # Cleanup if needed
        pass
    
    def __enter__(self):
        """Sync context manager entry"""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Sync context manager exit"""
        # Cleanup if needed
        pass


# Convenience factory functions

def create_docpixie(
    provider: str = "openai",
    api_key: Optional[str] = None,
    storage_path: Optional[str] = None
) -> DocPixie:
    """
    Create a DocPixie instance with simple configuration
    
    Args:
        provider: AI provider ("openai" or "anthropic")
        api_key: API key for the provider
        storage_path: Local storage path (uses default if None)
        
    Returns:
        Configured DocPixie instance
    """
    config = DocPixieConfig(
        provider=provider,
        local_storage_path=storage_path or "./docpixie_data"
    )
    
    return DocPixie(config=config, api_key=api_key)


def create_memory_docpixie(
    provider: str = "openai",
    api_key: Optional[str] = None
) -> DocPixie:
    """
    Create DocPixie instance with in-memory storage for testing
    
    Args:
        provider: AI provider
        api_key: API key for the provider
        
    Returns:
        DocPixie instance with memory storage
    """
    config = DocPixieConfig(
        provider=provider,
        storage_type="memory"
    )
    
    return DocPixie(config=config, api_key=api_key)