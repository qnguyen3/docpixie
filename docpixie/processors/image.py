"""
Image processor for direct image files
Handles JPG, PNG, WebP, and other image formats
"""

import asyncio
import logging
import tempfile
import os
from typing import List, Optional
from pathlib import Path

from PIL import Image

from .base import BaseProcessor, ProcessingError
from ..models.document import Document, Page, DocumentStatus
from ..core.config import DocPixieConfig

logger = logging.getLogger(__name__)


class ImageProcessor(BaseProcessor):
    """Processor for image files"""
    
    SUPPORTED_EXTENSIONS = ['.jpg', '.jpeg', '.png', '.webp', '.bmp', '.tiff', '.tif']
    
    def __init__(self, config: DocPixieConfig):
        super().__init__(config)
        self.temp_dir = None
    
    def supports(self, file_path: str) -> bool:
        """Check if file is a supported image format"""
        return Path(file_path).suffix.lower() in self.SUPPORTED_EXTENSIONS
    
    def get_supported_extensions(self) -> List[str]:
        """Get supported file extensions"""
        return self.SUPPORTED_EXTENSIONS.copy()
    
    async def process(self, file_path: str, document_id: Optional[str] = None) -> Document:
        """
        Process image file into a single-page document
        
        Args:
            file_path: Path to image file
            document_id: Optional custom document ID
            
        Returns:
            Document with single page
        """
        self._validate_file(file_path)
        logger.info(f"Processing image: {file_path}")
        
        try:
            # Create temporary directory for processed image
            self.temp_dir = tempfile.mkdtemp(prefix="docpixie_img_")
            
            # Process image in thread pool
            page = await asyncio.get_event_loop().run_in_executor(
                None,
                self._process_image_sync,
                file_path
            )
            
            # Create document with single page
            document = self._create_document(file_path, [page], document_id)
            document.status = DocumentStatus.COMPLETED
            
            # Update page with document info
            for page in document.pages:
                page.document_name = document.name
                page.document_id = document.id
            
            logger.info(f"Successfully processed image: {file_path}")
            return document
            
        except Exception as e:
            logger.error(f"Failed to process image {file_path}: {e}")
            # Clean up temp directory on error
            if self.temp_dir and os.path.exists(self.temp_dir):
                import shutil
                shutil.rmtree(self.temp_dir, ignore_errors=True)
            raise ProcessingError(f"Image processing failed: {e}", file_path)
    
    def _process_image_sync(self, file_path: str) -> Page:
        """Synchronous image processing"""
        try:
            # Open and process image
            with Image.open(file_path) as img:
                # Get original dimensions
                original_width, original_height = img.size
                
                # Optimize image
                optimized_img = self._optimize_image(img)
                
                # Save optimized image
                output_filename = "page_001.jpg"
                output_path = os.path.join(self.temp_dir, output_filename)
                
                optimized_img.save(
                    output_path,
                    'JPEG',
                    quality=self.config.jpeg_quality,
                    optimize=True
                )
                
                # Get final image dimensions and file size
                final_width, final_height = optimized_img.size
                file_size = os.path.getsize(output_path)
                
                # Create page object
                page = Page(
                    page_number=1,
                    image_path=output_path,
                    metadata={
                        'original_width': original_width,
                        'original_height': original_height,
                        'final_width': final_width,
                        'final_height': final_height,
                        'file_size': file_size,
                        'original_format': img.format
                    }
                )
                
                return page
                
        except Image.UnidentifiedImageError as e:
            raise ProcessingError(f"Unrecognized image format: {e}", file_path)
        except Exception as e:
            raise ProcessingError(f"Failed to process image: {e}", file_path)
    
    def _optimize_image(self, img: Image.Image) -> Image.Image:
        """
        Optimize image for storage and processing
        Same logic as PDF processor
        """
        # Convert to RGB if necessary
        if img.mode in ('RGBA', 'LA', 'P'):
            # Create white background for transparency
            rgb_img = Image.new('RGB', img.size, (255, 255, 255))
            if img.mode == 'RGBA':
                rgb_img.paste(img, mask=img.split()[-1])  # Use alpha channel as mask
            elif img.mode == 'P' and 'transparency' in img.info:
                # Handle palette mode with transparency
                img = img.convert('RGBA')
                rgb_img.paste(img, mask=img.split()[-1])
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
    
    def get_image_metadata(self, file_path: str) -> dict:
        """Extract image metadata"""
        try:
            with Image.open(file_path) as img:
                metadata = {
                    'format': img.format,
                    'mode': img.mode,
                    'width': img.width,
                    'height': img.height,
                    'has_transparency': img.mode in ('RGBA', 'LA') or 'transparency' in img.info
                }
                
                # Add EXIF data if available
                if hasattr(img, '_getexif') and img._getexif() is not None:
                    exif = img._getexif()
                    metadata['exif'] = exif
                
                return metadata
                
        except Exception as e:
            logger.error(f"Failed to extract image metadata: {e}")
            return {}