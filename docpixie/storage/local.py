"""
Local file system storage backend
Adapted from production LocalStorage but simplified for open-source version
"""

import os
import json
import shutil
import asyncio
from typing import List, Dict, Any, Optional
from pathlib import Path
import logging
from datetime import datetime

from .base import BaseStorage, StorageError
from ..models.document import Document, Page
from ..core.config import DocPixieConfig

logger = logging.getLogger(__name__)


class LocalStorage(BaseStorage):
    """Local file system storage backend"""
    
    def __init__(self, config: DocPixieConfig):
        self.config = config
        self.base_path = Path(config.local_storage_path)
        self.base_path.mkdir(parents=True, exist_ok=True)
        logger.info(f"Initialized local storage at: {self.base_path}")
    
    def _doc_dir(self, document_id: str) -> Path:
        """Get document directory path"""
        return self.base_path / document_id
    
    def _metadata_path(self, document_id: str) -> Path:
        """Get metadata file path"""
        return self._doc_dir(document_id) / "metadata.json"
    
    def _pages_dir(self, document_id: str) -> Path:
        """Get pages directory path"""
        return self._doc_dir(document_id) / "pages"
    
    async def save_document(self, document: Document) -> str:
        """Save document to local storage"""
        try:
            doc_dir = self._doc_dir(document.id)
            pages_dir = self._pages_dir(document.id)
            
            # Create directories
            doc_dir.mkdir(parents=True, exist_ok=True)
            pages_dir.mkdir(parents=True, exist_ok=True)
            
            # Copy page images to storage
            stored_pages = []
            for page in document.pages:
                if os.path.exists(page.image_path):
                    # Copy page image to storage
                    page_filename = f"page_{page.page_number:03d}.jpg"
                    dest_path = pages_dir / page_filename
                    
                    await asyncio.get_event_loop().run_in_executor(
                        None, shutil.copy2, page.image_path, dest_path
                    )
                    
                    # Update page with new path
                    stored_page = Page(
                        page_number=page.page_number,
                        image_path=str(dest_path),
                        content_summary=page.content_summary,
                        metadata=page.metadata
                    )
                    stored_pages.append(stored_page)
                else:
                    logger.warning(f"Page image not found: {page.image_path}")
            
            # Create metadata
            metadata = {
                "id": document.id,
                "name": document.name,
                "summary": document.summary,
                "status": document.status.value,
                "page_count": len(stored_pages),
                "pages": [
                    {
                        "page_number": page.page_number,
                        "image_path": page.image_path,
                        "content_summary": page.content_summary,
                        "metadata": page.metadata
                    }
                    for page in stored_pages
                ],
                "metadata": document.metadata,
                "created_at": document.created_at.isoformat(),
                "updated_at": datetime.now().isoformat()
            }
            
            # Save metadata
            metadata_path = self._metadata_path(document.id)
            with open(metadata_path, 'w') as f:
                json.dump(metadata, f, indent=2)
            
            logger.info(f"Saved document {document.id} with {len(stored_pages)} pages")
            return document.id
            
        except Exception as e:
            logger.error(f"Failed to save document {document.id}: {e}")
            # Clean up on error
            doc_dir = self._doc_dir(document.id)
            if doc_dir.exists():
                shutil.rmtree(doc_dir, ignore_errors=True)
            raise StorageError(f"Failed to save document: {e}", document.id)
    
    async def get_document(self, document_id: str) -> Optional[Document]:
        """Retrieve document from local storage"""
        try:
            metadata_path = self._metadata_path(document_id)
            if not metadata_path.exists():
                return None
            
            # Load metadata
            with open(metadata_path, 'r') as f:
                metadata = json.load(f)
            
            # Reconstruct pages
            pages = []
            for page_data in metadata.get('pages', []):
                page = Page(
                    page_number=page_data['page_number'],
                    image_path=page_data['image_path'],
                    content_summary=page_data.get('content_summary'),
                    metadata=page_data.get('metadata', {})
                )
                pages.append(page)
            
            # Reconstruct document
            document = Document(
                id=metadata['id'],
                name=metadata['name'],
                pages=pages,
                summary=metadata.get('summary'),
                metadata=metadata.get('metadata', {}),
                created_at=datetime.fromisoformat(metadata['created_at'])
            )
            
            return document
            
        except Exception as e:
            logger.error(f"Failed to load document {document_id}: {e}")
            raise StorageError(f"Failed to load document: {e}", document_id)
    
    async def list_documents(self, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """List all documents"""
        try:
            documents = []
            
            if not self.base_path.exists():
                return documents
            
            for doc_dir in self.base_path.iterdir():
                if not doc_dir.is_dir():
                    continue
                
                metadata_path = doc_dir / "metadata.json"
                if not metadata_path.exists():
                    continue
                
                try:
                    with open(metadata_path, 'r') as f:
                        metadata = json.load(f)
                    
                    # Return summary info
                    doc_info = {
                        'id': metadata['id'],
                        'name': metadata['name'],
                        'summary': metadata.get('summary'),
                        'page_count': metadata.get('page_count', 0),
                        'created_at': metadata['created_at'],
                        'updated_at': metadata.get('updated_at'),
                        'status': metadata.get('status', 'unknown')
                    }
                    documents.append(doc_info)
                    
                except Exception as e:
                    logger.warning(f"Failed to read metadata for {doc_dir.name}: {e}")
                    continue
                
                if limit and len(documents) >= limit:
                    break
            
            # Sort by creation time (newest first)
            documents.sort(key=lambda x: x['created_at'], reverse=True)
            return documents
            
        except Exception as e:
            logger.error(f"Failed to list documents: {e}")
            raise StorageError(f"Failed to list documents: {e}")
    
    async def delete_document(self, document_id: str) -> bool:
        """Delete document and all associated files"""
        try:
            doc_dir = self._doc_dir(document_id)
            if doc_dir.exists():
                await asyncio.get_event_loop().run_in_executor(
                    None, shutil.rmtree, doc_dir
                )
                logger.info(f"Deleted document {document_id}")
                return True
            else:
                logger.warning(f"Document directory not found: {document_id}")
                return False
                
        except Exception as e:
            logger.error(f"Failed to delete document {document_id}: {e}")
            raise StorageError(f"Failed to delete document: {e}", document_id)
    
    async def document_exists(self, document_id: str) -> bool:
        """Check if document exists"""
        metadata_path = self._metadata_path(document_id)
        return metadata_path.exists()
    
    async def get_document_summary(self, document_id: str) -> Optional[str]:
        """Get document summary without loading full document"""
        try:
            metadata_path = self._metadata_path(document_id)
            if not metadata_path.exists():
                return None
            
            with open(metadata_path, 'r') as f:
                metadata = json.load(f)
            
            return metadata.get('summary')
            
        except Exception as e:
            logger.error(f"Failed to get summary for {document_id}: {e}")
            return None
    
    async def update_document_summary(self, document_id: str, summary: str) -> bool:
        """Update document summary"""
        try:
            metadata_path = self._metadata_path(document_id)
            if not metadata_path.exists():
                return False
            
            # Load existing metadata
            with open(metadata_path, 'r') as f:
                metadata = json.load(f)
            
            # Update summary and timestamp
            metadata['summary'] = summary
            metadata['updated_at'] = datetime.now().isoformat()
            
            # Save updated metadata
            with open(metadata_path, 'w') as f:
                json.dump(metadata, f, indent=2)
            
            logger.info(f"Updated summary for document {document_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to update summary for {document_id}: {e}")
            return False
    
    def get_document_pages(self, document_id: str) -> List[str]:
        """Get list of page image paths (synchronous helper method)"""
        pages_dir = self._pages_dir(document_id)
        if not pages_dir.exists():
            return []
        
        # Get all page files sorted by name
        page_files = sorted([
            f for f in pages_dir.iterdir() 
            if f.is_file() and f.name.lower().startswith("page_")
        ])
        
        return [str(f) for f in page_files]
    
    async def get_all_documents(self) -> List[Document]:
        """Get all documents for agent processing"""
        try:
            documents = []
            
            if not self.base_path.exists():
                return documents
            
            # Get all document directories
            for doc_dir in self.base_path.iterdir():
                if doc_dir.is_dir():
                    try:
                        # Load the document
                        document = await self.get_document(doc_dir.name)
                        if document:
                            documents.append(document)
                    except Exception as e:
                        logger.warning(f"Failed to load document {doc_dir.name}: {e}")
                        continue
            
            return documents
            
        except Exception as e:
            logger.error(f"Failed to get all documents: {e}")
            raise StorageError(f"Failed to get all documents: {e}")
    
    async def get_all_pages(self) -> List[Page]:
        """Get all pages from all documents for agent processing"""
        try:
            all_pages = []
            
            if not self.base_path.exists():
                return all_pages
            
            # Get all document directories
            for doc_dir in self.base_path.iterdir():
                if doc_dir.is_dir():
                    try:
                        # Load the document
                        document = await self.get_document(doc_dir.name)
                        if document and document.pages:
                            all_pages.extend(document.pages)
                    except Exception as e:
                        logger.warning(f"Failed to load pages from document {doc_dir.name}: {e}")
                        continue
            
            return all_pages
            
        except Exception as e:
            logger.error(f"Failed to get all pages: {e}")
            raise StorageError(f"Failed to get all pages: {e}")
    
    def get_storage_stats(self) -> Dict[str, Any]:
        """Get storage statistics"""
        try:
            total_size = 0
            total_documents = 0
            total_pages = 0
            
            if self.base_path.exists():
                for doc_dir in self.base_path.iterdir():
                    if doc_dir.is_dir():
                        total_documents += 1
                        for file_path in doc_dir.rglob('*'):
                            if file_path.is_file():
                                total_size += file_path.stat().st_size
                                if file_path.name.startswith('page_'):
                                    total_pages += 1
            
            return {
                'backend': 'LocalStorage',
                'base_path': str(self.base_path),
                'total_documents': total_documents,
                'total_pages': total_pages,
                'total_size_bytes': total_size,
                'total_size_mb': round(total_size / (1024 * 1024), 2),
                'features': ['local_storage', 'metadata', 'page_images']
            }
            
        except Exception as e:
            logger.error(f"Failed to get storage stats: {e}")
            return {
                'backend': 'LocalStorage',
                'error': str(e)
            }