"""
Processor factory for selecting appropriate document processor
"""

from typing import Optional, Dict, Type
from pathlib import Path
import logging

from .base import BaseProcessor
from .pdf import PDFProcessor
from .image import ImageProcessor
from ..core.config import DocPixieConfig

logger = logging.getLogger(__name__)


class ProcessorFactory:
    """Factory for creating document processors"""
    
    def __init__(self, config: DocPixieConfig):
        self.config = config
        self._processors: Dict[str, Type[BaseProcessor]] = {
            'pdf': PDFProcessor,
            'image': ImageProcessor
        }
        
        # Map file extensions to processor types
        self._extension_map: Dict[str, str] = {}
        self._build_extension_map()
    
    def _build_extension_map(self):
        """Build mapping from file extensions to processor types"""
        # Create processor instances to get supported extensions
        for processor_type, processor_class in self._processors.items():
            processor = processor_class(self.config)
            for ext in processor.get_supported_extensions():
                self._extension_map[ext.lower()] = processor_type
        
        logger.debug(f"Built extension map: {self._extension_map}")
    
    def get_processor(self, file_path: str) -> BaseProcessor:
        """
        Get appropriate processor for file
        
        Args:
            file_path: Path to file
            
        Returns:
            Processor instance
            
        Raises:
            ValueError: If file type is not supported
        """
        file_extension = Path(file_path).suffix.lower()
        
        if not file_extension:
            raise ValueError(f"File has no extension: {file_path}")
        
        processor_type = self._extension_map.get(file_extension)
        
        if not processor_type:
            supported_exts = list(self._extension_map.keys())
            raise ValueError(
                f"Unsupported file type '{file_extension}'. "
                f"Supported extensions: {supported_exts}"
            )
        
        processor_class = self._processors[processor_type]
        processor = processor_class(self.config)
        
        logger.debug(f"Selected {processor_class.__name__} for {file_path}")
        return processor
    
    def supports_file(self, file_path: str) -> bool:
        """Check if file type is supported"""
        file_extension = Path(file_path).suffix.lower()
        return file_extension in self._extension_map
    
    def get_supported_extensions(self) -> Dict[str, str]:
        """Get all supported extensions and their processor types"""
        return self._extension_map.copy()
    
    def register_processor(self, processor_type: str, processor_class: Type[BaseProcessor]):
        """
        Register a custom processor
        
        Args:
            processor_type: Unique identifier for processor
            processor_class: Processor class
        """
        self._processors[processor_type] = processor_class
        
        # Update extension mapping
        processor = processor_class(self.config)
        for ext in processor.get_supported_extensions():
            self._extension_map[ext.lower()] = processor_type
        
        logger.info(f"Registered custom processor: {processor_type}")
    
    def list_processors(self) -> Dict[str, Type[BaseProcessor]]:
        """Get all registered processors"""
        return self._processors.copy()
    
    def create_processor(self, processor_type: str) -> Optional[BaseProcessor]:
        """
        Create processor by type
        
        Args:
            processor_type: Type of processor to create
            
        Returns:
            Processor instance or None if type not found
        """
        processor_class = self._processors.get(processor_type)
        if processor_class:
            return processor_class(self.config)
        return None