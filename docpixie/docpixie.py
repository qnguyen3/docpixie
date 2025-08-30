"""
Main DocPixie API class
Simplified multimodal RAG without embeddings or vector databases
"""

import asyncio
from typing import Optional, List, Dict, Any, Union, Callable
from pathlib import Path
import logging

from .models.document import (
    Document, Page, QueryResult, QueryMode, 
    DocumentProcessRequest, QueryRequest, DocumentStatus
)
from .models.agent import ConversationMessage
from .core.config import DocPixieConfig
from .processors.factory import ProcessorFactory
from .storage.local import LocalStorage
from .storage.memory import InMemoryStorage
from .storage.base import BaseStorage
from .ai.summarizer import PageSummarizer
from .ai.agent import PixieRAGAgent
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
        self.provider = create_provider(config)
        self.summarizer = PageSummarizer(config)
        self.agent = PixieRAGAgent(self.provider, self.storage, config)
        
        logger.info(f"Initialized DocPixie with {config.provider} provider and {type(self.storage).__name__} storage")
    
    # Document Management
    
    async def add_document(
        self,
        file_path: Union[str, Path],
        document_id: Optional[str] = None,
        document_name: Optional[str] = None
    ) -> Document:
        """
        Add a document to the RAG system
        
        Args:
            file_path: Path to document file (PDF, image, etc.)
            document_id: Optional custom document ID
            document_name: Optional custom document name
            
        Returns:
            Processed Document object with summary
        """
        file_path = str(file_path)
        logger.info(f"Adding document: {file_path}")
        
        # Process document
        processor = self.processor_factory.get_processor(file_path)
        document = await processor.process(file_path, document_id)
        
        # Override name if provided
        if document_name:
            document.name = document_name
        
        # Always generate document summary
        logger.info(f"Generating document summary for {document.name}")
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
    
    # Query Processing (Phase 2 - Vision-based RAG with Adaptive Agent)
    
    async def query(
        self,
        question: str,
        mode: QueryMode = QueryMode.AUTO,
        document_ids: Optional[List[str]] = None,
        max_pages: Optional[int] = None,
        stream: bool = False,
        conversation_history: Optional[List[ConversationMessage]] = None,
        task_update_callback: Optional[Any] = None
    ) -> QueryResult:
        """
        Query documents with a question using adaptive vision-based RAG
        
        Args:
            question: User's question
            mode: Query mode (Flash, Pro, or Auto) - currently all use adaptive mode
            document_ids: Specific documents to search (None = all) - currently searches all
            max_pages: Maximum pages to analyze (uses config setting)
            stream: Whether to stream the response (not implemented)
            conversation_history: Previous conversation context
            
        Returns:
            QueryResult with answer and metadata
        """
        logger.info(f"Processing query with adaptive RAG agent: {question}")
        
        try:
            # Use the adaptive RAG agent for processing
            agent_result = await self.agent.process_query(question, conversation_history, task_update_callback)
            
            # Convert agent QueryResult to API QueryResult format
            return QueryResult(
                query=agent_result.query,
                answer=agent_result.answer,
                selected_pages=agent_result.get_unique_pages(),
                mode=mode,  # Keep the requested mode for compatibility
                confidence=self._calculate_confidence(agent_result),
                processing_time=agent_result.processing_time_seconds,
                metadata={
                    'agent_iterations': agent_result.total_iterations,
                    'tasks_completed': len(agent_result.task_results),
                    'total_pages_analyzed': agent_result.get_total_pages_analyzed(),
                    'agent_mode': 'adaptive',
                    'phase': 'Phase 2 - Adaptive Vision RAG'
                }
            )
            
        except Exception as e:
            logger.error(f"Query processing failed: {e}")
            return QueryResult(
                query=question,
                answer=f"I encountered an error while processing your query: {str(e)}",
                selected_pages=[],
                mode=mode,
                confidence=0.0,
                processing_time=0.0,
                metadata={'error': str(e)}
            )
    
    def _calculate_confidence(self, agent_result) -> float:
        """Calculate confidence score based on agent execution"""
        # Simple confidence calculation based on successful completion
        if not agent_result.task_results:
            return 0.0
        
        # Base confidence on task completion and page analysis
        task_success_rate = len([r for r in agent_result.task_results 
                               if r.analysis and not r.analysis.startswith("Task execution failed")]) / len(agent_result.task_results)
        
        # Boost confidence if we analyzed pages
        page_boost = min(0.2, agent_result.get_total_pages_analyzed() * 0.02)
        
        # Cap at 1.0
        return min(1.0, 0.6 + (task_success_rate * 0.3) + page_boost)
    
    async def query_with_conversation(
        self,
        question: str,
        conversation_history: List[ConversationMessage],
        mode: QueryMode = QueryMode.AUTO
    ) -> QueryResult:
        """
        Convenience method for conversation-aware queries
        
        Args:
            question: Current user question
            conversation_history: Previous conversation messages
            mode: Query mode
            
        Returns:
            QueryResult with conversation context
        """
        return await self.query(
            question=question, 
            mode=mode, 
            conversation_history=conversation_history
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
        agent_stats = self.agent.get_agent_stats()
        
        return {
            'docpixie_version': '0.1.0',
            'config': {
                'provider': self.config.provider,
                'storage_type': self.config.storage_type,
                'max_agent_iterations': self.config.max_agent_iterations,
                'max_pages_per_task': self.config.max_pages_per_task
            },
            'storage': storage_stats,
            'summarizer': summarizer_stats,
            'agent': agent_stats,
            'supported_extensions': list(self.get_supported_extensions().keys()),
            'features': ['adaptive_rag', 'vision_page_selection', 'task_planning', 'conversation_aware']
        }
    
    # Synchronous API for easier adoption
    
    def add_document_sync(
        self,
        file_path: Union[str, Path],
        document_id: Optional[str] = None,
        document_name: Optional[str] = None
    ) -> Document:
        """Synchronous version of add_document"""
        return sync_wrapper(self.add_document(file_path, document_id, document_name))
    
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
        max_pages: Optional[int] = None,
        conversation_history: Optional[List[ConversationMessage]] = None,
        task_update_callback: Optional[Any] = None
    ) -> QueryResult:
        """Synchronous version of query"""
        return sync_wrapper(self.query(question, mode, document_ids, max_pages, stream=False, conversation_history=conversation_history, task_update_callback=task_update_callback))
    
    def search_documents_sync(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Synchronous version of search_documents"""
        return sync_wrapper(self.search_documents(query, limit))
    
    def query_with_conversation_sync(
        self,
        question: str,
        conversation_history: List[ConversationMessage],
        mode: QueryMode = QueryMode.AUTO
    ) -> QueryResult:
        """Synchronous version of query_with_conversation"""
        return sync_wrapper(self.query_with_conversation(question, conversation_history, mode))
    
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