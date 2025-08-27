"""
In-memory storage backend for testing
"""

import asyncio
from typing import List, Dict, Any, Optional
from datetime import datetime
import logging
import copy

from .base import BaseStorage, StorageError
from ..models.document import Document
from ..core.config import DocPixieConfig

logger = logging.getLogger(__name__)


class InMemoryStorage(BaseStorage):
    """In-memory storage backend for testing and development"""
    
    def __init__(self, config: DocPixieConfig):
        self.config = config
        self._documents: Dict[str, Document] = {}
        self._document_summaries: Dict[str, str] = {}
        self._created_at = datetime.now()
        logger.info("Initialized in-memory storage")
    
    async def save_document(self, document: Document) -> str:
        """Save document to memory"""
        try:
            # Deep copy to avoid external modifications
            stored_document = copy.deepcopy(document)
            
            # Store document
            self._documents[document.id] = stored_document
            
            # Store summary separately for quick access
            if document.summary:
                self._document_summaries[document.id] = document.summary
            
            logger.info(f"Saved document {document.id} to memory ({len(document.pages)} pages)")
            return document.id
            
        except Exception as e:
            logger.error(f"Failed to save document {document.id} to memory: {e}")
            raise StorageError(f"Failed to save document: {e}", document.id)
    
    async def get_document(self, document_id: str) -> Optional[Document]:
        """Retrieve document from memory"""
        try:
            document = self._documents.get(document_id)
            if document:
                # Return a deep copy to avoid external modifications
                return copy.deepcopy(document)
            return None
            
        except Exception as e:
            logger.error(f"Failed to get document {document_id} from memory: {e}")
            raise StorageError(f"Failed to get document: {e}", document_id)
    
    async def list_documents(self, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """List all documents in memory"""
        try:
            documents = []
            
            for doc_id, document in self._documents.items():
                doc_info = {
                    'id': document.id,
                    'name': document.name,
                    'summary': self._document_summaries.get(doc_id),
                    'page_count': len(document.pages),
                    'created_at': document.created_at.isoformat(),
                    'updated_at': document.created_at.isoformat(),  # No update tracking in memory
                    'status': document.status.value
                }
                documents.append(doc_info)
                
                if limit and len(documents) >= limit:
                    break
            
            # Sort by creation time (newest first)
            documents.sort(key=lambda x: x['created_at'], reverse=True)
            return documents
            
        except Exception as e:
            logger.error(f"Failed to list documents in memory: {e}")
            raise StorageError(f"Failed to list documents: {e}")
    
    async def delete_document(self, document_id: str) -> bool:
        """Delete document from memory"""
        try:
            if document_id in self._documents:
                del self._documents[document_id]
                self._document_summaries.pop(document_id, None)
                logger.info(f"Deleted document {document_id} from memory")
                return True
            else:
                logger.warning(f"Document {document_id} not found in memory")
                return False
                
        except Exception as e:
            logger.error(f"Failed to delete document {document_id} from memory: {e}")
            raise StorageError(f"Failed to delete document: {e}", document_id)
    
    async def document_exists(self, document_id: str) -> bool:
        """Check if document exists in memory"""
        return document_id in self._documents
    
    async def get_document_summary(self, document_id: str) -> Optional[str]:
        """Get document summary from memory"""
        return self._document_summaries.get(document_id)
    
    async def update_document_summary(self, document_id: str, summary: str) -> bool:
        """Update document summary in memory"""
        try:
            if document_id in self._documents:
                # Update summary in both document and summary cache
                self._documents[document_id].summary = summary
                self._document_summaries[document_id] = summary
                logger.info(f"Updated summary for document {document_id} in memory")
                return True
            else:
                logger.warning(f"Document {document_id} not found for summary update")
                return False
                
        except Exception as e:
            logger.error(f"Failed to update summary for {document_id} in memory: {e}")
            return False
    
    async def search_documents(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Search documents in memory"""
        try:
            matching_docs = []
            query_lower = query.lower()
            
            for doc_id, document in self._documents.items():
                # Check name match
                name_match = query_lower in document.name.lower()
                
                # Check summary match
                summary = self._document_summaries.get(doc_id, '')
                summary_match = query_lower in summary.lower()
                
                # Check page summaries
                page_summary_match = False
                for page in document.pages:
                    if page.content_summary and query_lower in page.content_summary.lower():
                        page_summary_match = True
                        break
                
                if name_match or summary_match or page_summary_match:
                    doc_info = {
                        'id': document.id,
                        'name': document.name,
                        'summary': summary,
                        'page_count': len(document.pages),
                        'created_at': document.created_at.isoformat(),
                        'status': document.status.value,
                        'relevance_score': self._calculate_relevance(
                            query_lower, document, summary
                        )
                    }
                    matching_docs.append(doc_info)
                    
                    if len(matching_docs) >= limit:
                        break
            
            # Sort by relevance score
            matching_docs.sort(key=lambda x: x['relevance_score'], reverse=True)
            return matching_docs
            
        except Exception as e:
            logger.error(f"Failed to search documents in memory: {e}")
            return []
    
    def _calculate_relevance(self, query: str, document: Document, summary: str) -> float:
        """Calculate simple relevance score for search results"""
        score = 0.0
        
        # Name matches are highly relevant
        if query in document.name.lower():
            score += 10.0
        
        # Summary matches are relevant
        summary_matches = summary.lower().count(query)
        score += summary_matches * 2.0
        
        # Page summary matches
        page_matches = sum(
            1 for page in document.pages
            if page.content_summary and query in page.content_summary.lower()
        )
        score += page_matches * 1.0
        
        return score
    
    def get_storage_stats(self) -> Dict[str, Any]:
        """Get storage statistics"""
        try:
            total_pages = sum(len(doc.pages) for doc in self._documents.values())
            
            return {
                'backend': 'InMemoryStorage',
                'total_documents': len(self._documents),
                'total_pages': total_pages,
                'created_at': self._created_at.isoformat(),
                'features': ['in_memory', 'fast_access', 'search', 'testing']
            }
            
        except Exception as e:
            return {
                'backend': 'InMemoryStorage',
                'error': str(e)
            }
    
    def clear_all(self):
        """Clear all documents (useful for testing)"""
        self._documents.clear()
        self._document_summaries.clear()
        logger.info("Cleared all documents from memory")
    
    def get_document_count(self) -> int:
        """Get total number of documents in memory"""
        return len(self._documents)
    
    def get_total_pages(self) -> int:
        """Get total number of pages across all documents"""
        return sum(len(doc.pages) for doc in self._documents.values())