"""
Document models and data structures for DocPixie
Simplified version of schemas from production DocPixie
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from enum import Enum
from pathlib import Path
import uuid
from datetime import datetime


class QueryMode(str, Enum):
    """Query processing modes"""
    AUTO = "auto"    # Standard adaptive processing


class DocumentStatus(str, Enum):
    """Document processing status"""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class Page:
    """Represents a single document page"""
    page_number: int
    image_path: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        """Validate page data"""
        if self.page_number <= 0:
            raise ValueError("Page number must be positive")
        if not self.image_path:
            raise ValueError("Image path is required")


@dataclass 
class Document:
    """Represents a processed document with pages"""
    id: str
    name: str
    pages: List[Page]
    summary: Optional[str] = None
    status: DocumentStatus = DocumentStatus.PENDING
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)
    
    def __post_init__(self):
        """Generate ID if not provided and validate data"""
        if not self.id:
            self.id = str(uuid.uuid4())
        if not self.name:
            raise ValueError("Document name is required")
        if not isinstance(self.pages, list):
            raise ValueError("Pages must be a list")
    
    @property
    def page_count(self) -> int:
        """Get total number of pages"""
        return len(self.pages)
    
    
    def get_page(self, page_number: int) -> Optional[Page]:
        """Get specific page by number"""
        for page in self.pages:
            if page.page_number == page_number:
                return page
        return None
    
    def get_pages_range(self, start: int, end: int) -> List[Page]:
        """Get pages in a range"""
        return [p for p in self.pages if start <= p.page_number <= end]


@dataclass
class QueryResult:
    """Result of a RAG query"""
    query: str
    answer: str
    selected_pages: List[Page]
    mode: QueryMode
    confidence: float = 0.0
    processing_time: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        """Validate result data"""
        if not self.query:
            raise ValueError("Query is required")
        if not self.answer:
            raise ValueError("Answer is required")
        if self.confidence < 0 or self.confidence > 1:
            raise ValueError("Confidence must be between 0 and 1")
    
    @property
    def page_count(self) -> int:
        """Number of pages used for the answer"""
        return len(self.selected_pages)
    
    @property
    def page_numbers(self) -> List[int]:
        """Page numbers used for the answer"""
        return [p.page_number for p in self.selected_pages]


@dataclass
class DocumentProcessRequest:
    """Request to process a document"""
    file_path: str
    document_id: Optional[str] = None
    document_name: Optional[str] = None
    
    def __post_init__(self):
        """Validate and set defaults"""
        if not self.file_path or not Path(self.file_path).exists():
            raise FileNotFoundError(f"File not found: {self.file_path}")
        
        if not self.document_name:
            self.document_name = Path(self.file_path).stem
        
        if not self.document_id:
            self.document_id = str(uuid.uuid4())


@dataclass
class QueryRequest:
    """Request to query documents"""
    query: str
    mode: QueryMode = QueryMode.AUTO
    document_ids: Optional[List[str]] = None
    max_pages: Optional[int] = None
    stream: bool = False
    
    def __post_init__(self):
        """Validate query request"""
        if not self.query.strip():
            raise ValueError("Query cannot be empty")
        
        # Set default max_pages
        if self.max_pages is None:
            self.max_pages = 15  # Use standard page limit