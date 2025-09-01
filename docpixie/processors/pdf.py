"""
PyMuPDF-based PDF processor
Replacement for pdf2image with better performance and quality
"""

import asyncio
import logging
from typing import List, Optional, Tuple
from pathlib import Path
import tempfile
import os

from PIL import Image
import fitz  # PyMuPDF

from .base import BaseProcessor, ProcessingError
from ..models.document import Document, Page, DocumentStatus
from ..core.config import DocPixieConfig

logger = logging.getLogger(__name__)


class PDFProcessor(BaseProcessor):
    """PDF processor using PyMuPDF for better performance"""
    
    SUPPORTED_EXTENSIONS = ['.pdf']
    
    def __init__(self, config: DocPixieConfig):
        super().__init__(config)
        self.temp_dir = None
    
    def supports(self, file_path: str) -> bool:
        """Check if file is a PDF"""
        return Path(file_path).suffix.lower() in self.SUPPORTED_EXTENSIONS
    
    def get_supported_extensions(self) -> List[str]:
        """Get supported file extensions"""
        return self.SUPPORTED_EXTENSIONS.copy()
    
    async def process(self, file_path: str, document_id: Optional[str] = None) -> Document:
        """
        Process PDF into document pages using PyMuPDF
        
        Args:
            file_path: Path to PDF file
            document_id: Optional custom document ID
            
        Returns:
            Document with processed pages
        """
        self._validate_file(file_path)
        logger.info(f"Processing PDF: {file_path}")
        
        try:
            # Create temporary directory for page images
            self.temp_dir = tempfile.mkdtemp(prefix="docpixie_pdf_")
            
            # Process PDF in thread pool (PyMuPDF is not async)
            pages = await asyncio.get_event_loop().run_in_executor(
                None, 
                self._process_pdf_sync,
                file_path
            )
            
            # Create document
            document = self._create_document(file_path, pages, document_id)
            document.status = DocumentStatus.COMPLETED
            
            # Update pages with document info
            for page in document.pages:
                page.document_name = document.name
                page.document_id = document.id
            
            logger.info(f"Successfully processed PDF: {len(pages)} pages")
            return document
            
        except Exception as e:
            logger.error(f"Failed to process PDF {file_path}: {e}")
            # Clean up temp directory on error
            if self.temp_dir and os.path.exists(self.temp_dir):
                import shutil
                shutil.rmtree(self.temp_dir, ignore_errors=True)
            raise ProcessingError(f"PDF processing failed: {e}", file_path)
    
    def _process_pdf_sync(self, file_path: str) -> List[Page]:
        """Synchronous PDF processing with PyMuPDF"""
        pages = []
        
        try:
            # Open PDF document
            pdf_doc = fitz.open(file_path)
            total_pages = pdf_doc.page_count
            
            logger.info(f"Processing {total_pages} pages from PDF")
            
            for page_num in range(total_pages):
                try:
                    # Get page
                    page = pdf_doc[page_num]
                    
                    # Create transformation matrix for scaling
                    matrix = fitz.Matrix(
                        self.config.pdf_render_scale, 
                        self.config.pdf_render_scale
                    )
                    
                    # Render page to pixmap
                    pix = page.get_pixmap(
                        matrix=matrix,
                        alpha=False  # No transparency for JPEG
                    )
                    
                    # Convert to PIL Image
                    img_data = pix.tobytes("ppm")
                    img = Image.open(io.BytesIO(img_data))
                    
                    # Optimize image
                    optimized_img = self._optimize_image(img)
                    
                    # Save page image
                    page_filename = f"page_{page_num + 1:03d}.jpg"
                    page_image_path = os.path.join(self.temp_dir, page_filename)
                    
                    optimized_img.save(
                        page_image_path, 
                        'JPEG', 
                        quality=self.config.jpeg_quality,
                        optimize=True
                    )
                    
                    # Create page object
                    page_obj = Page(
                        page_number=page_num + 1,
                        image_path=page_image_path,
                        metadata={
                            'width': pix.width,
                            'height': pix.height,
                            'file_size': os.path.getsize(page_image_path)
                        }
                    )
                    
                    pages.append(page_obj)
                    
                except Exception as e:
                    logger.error(f"Failed to process page {page_num + 1}: {e}")
                    raise ProcessingError(
                        f"Failed to process page {page_num + 1}: {e}",
                        file_path,
                        page_num + 1
                    )
            
            pdf_doc.close()
            return pages
            
        except fitz.FileDataError as e:
            raise ProcessingError(f"Invalid PDF file: {e}", file_path)
        except fitz.FileNotFoundError as e:
            raise ProcessingError(f"PDF file not found: {e}", file_path)
        except Exception as e:
            raise ProcessingError(f"Unexpected error processing PDF: {e}", file_path)
    
    def _optimize_image(self, img: Image.Image) -> Image.Image:
        """
        Optimize image for storage and processing
        Adapted from existing resize_image_for_upload logic
        """
        # Convert to RGB if necessary
        if img.mode in ('RGBA', 'LA', 'P'):
            # Create white background
            rgb_img = Image.new('RGB', img.size, (255, 255, 255))
            if img.mode == 'RGBA':
                rgb_img.paste(img, mask=img.split()[-1])  # Use alpha channel as mask
            else:
                rgb_img.paste(img)
            img = rgb_img
        elif img.mode != 'RGB':
            img = img.convert('RGB')
        
        # Resize if image is too large
        max_width, max_height = self.config.pdf_max_image_size
        if img.width > max_width or img.height > max_height:
            # Calculate new size maintaining aspect ratio
            ratio = min(max_width / img.width, max_height / img.height)
            new_width = int(img.width * ratio)
            new_height = int(img.height * ratio)
            
            img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
            logger.debug(f"Resized image to {new_width}x{new_height}")
        
        return img
    
    def create_thumbnail(self, image_path: str) -> str:
        """Create thumbnail for quick page selection"""
        try:
            with Image.open(image_path) as img:
                # Create thumbnail
                thumbnail = img.copy()
                thumbnail.thumbnail(self.config.thumbnail_size, Image.Resampling.LANCZOS)
                
                # Save thumbnail
                thumb_path = image_path.replace('.jpg', '_thumb.jpg')
                thumbnail.save(thumb_path, 'JPEG', quality=85, optimize=True)
                
                return thumb_path
                
        except Exception as e:
            logger.error(f"Failed to create thumbnail for {image_path}: {e}")
            return image_path  # Return original if thumbnail creation fails
    
    def get_pdf_metadata(self, file_path: str) -> dict:
        """Extract PDF metadata"""
        try:
            pdf_doc = fitz.open(file_path)
            metadata = pdf_doc.metadata
            page_count = pdf_doc.page_count
            pdf_doc.close()
            
            return {
                'title': metadata.get('title', ''),
                'author': metadata.get('author', ''),
                'subject': metadata.get('subject', ''),
                'creator': metadata.get('creator', ''),
                'producer': metadata.get('producer', ''),
                'creation_date': metadata.get('creationDate', ''),
                'modification_date': metadata.get('modDate', ''),
                'page_count': page_count
            }
        except Exception as e:
            logger.error(f"Failed to extract PDF metadata: {e}")
            return {}


# Import io for BytesIO
import io