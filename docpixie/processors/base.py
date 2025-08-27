"""
Base processor interface for document processing
"""

from abc import ABC, abstractmethod
from typing import List, Optional
from pathlib import Path
import logging

from ..models.document import Document, Page
from ..core.config import DocPixieConfig

logger = logging.getLogger(__name__)


class BaseProcessor(ABC):
    """Base class for document processors"""
    
    def __init__(self, config: DocPixieConfig):
        self.config = config
    
    @abstractmethod
    def supports(self, file_path: str) -> bool:
        """Check if this processor supports the given file type"""
        pass
    
    @abstractmethod
    async def process(self, file_path: str, document_id: Optional[str] = None) -> Document:
        """
        Process a document file into pages
        
        Args:
            file_path: Path to the document file
            document_id: Optional custom document ID
            
        Returns:
            Document with processed pages
        """
        pass
    
    def get_supported_extensions(self) -> List[str]:
        """Get list of supported file extensions"""
        return []
    
    def _create_document(
        self, 
        file_path: str, 
        pages: List[Page], 
        document_id: Optional[str] = None
    ) -> Document:
        """Create a Document object from processed pages"""
        document_name = Path(file_path).stem
        
        return Document(
            id=document_id or self._generate_document_id(file_path),
            name=document_name,
            pages=pages,
            metadata={
                'original_file': file_path,
                'processor': self.__class__.__name__,
                'file_size': Path(file_path).stat().st_size if Path(file_path).exists() else 0
            }
        )
    
    def _generate_document_id(self, file_path: str) -> str:
        """Generate a document ID from file path"""
        import hashlib
        return hashlib.md5(file_path.encode()).hexdigest()
    
    def _validate_file(self, file_path: str) -> None:
        """Validate that file exists and is readable"""
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")
        if not path.is_file():
            raise ValueError(f"Path is not a file: {file_path}")
        if path.stat().st_size == 0:
            raise ValueError(f"File is empty: {file_path}")


class ProcessingError(Exception):
    """Exception raised during document processing"""
    
    def __init__(self, message: str, file_path: str, page_number: Optional[int] = None):
        self.file_path = file_path
        self.page_number = page_number
        super().__init__(message)