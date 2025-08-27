"""
Page summarizer for generating document summaries
"""

import asyncio
from typing import List, Optional, Dict, Any
import logging

from ..providers import BaseProvider, create_provider
from ..models.document import Document, Page
from ..core.config import DocPixieConfig

logger = logging.getLogger(__name__)


class PageSummarizer:
    """Generates summaries for document pages using vision models"""
    
    def __init__(self, config: DocPixieConfig, provider: Optional[BaseProvider] = None):
        self.config = config
        self.provider = provider or create_provider(config)
    
    async def summarize_pages(self, pages: List[Page]) -> List[Page]:
        """
        Generate summaries for multiple pages in parallel
        
        Args:
            pages: List of pages to summarize
            
        Returns:
            List of pages with summaries added
        """
        if not pages:
            return pages
        
        logger.info(f"Generating summaries for {len(pages)} pages")
        
        # Create batches to avoid overwhelming the API
        batch_size = self.config.batch_size
        summarized_pages = []
        
        for i in range(0, len(pages), batch_size):
            batch = pages[i:i + batch_size]
            logger.debug(f"Processing batch {i//batch_size + 1}: pages {i+1}-{min(i+batch_size, len(pages))}")
            
            # Process batch in parallel
            batch_tasks = [
                self._summarize_single_page(page)
                for page in batch
            ]
            
            batch_results = await asyncio.gather(*batch_tasks, return_exceptions=True)
            
            # Handle results and exceptions
            for page, result in zip(batch, batch_results):
                if isinstance(result, Exception):
                    logger.error(f"Failed to summarize page {page.page_number}: {result}")
                    # Keep original page without summary
                    summarized_pages.append(page)
                else:
                    summarized_pages.append(result)
        
        success_count = sum(1 for page in summarized_pages if page.content_summary)
        logger.info(f"Successfully generated {success_count}/{len(pages)} page summaries")
        
        return summarized_pages
    
    async def _summarize_single_page(self, page: Page) -> Page:
        """Summarize a single page"""
        try:
            # Build messages for page summary
            messages = [
                {
                    "role": "system",
                    "content": "You are a document analysis expert. Analyze the document page image and create a concise but comprehensive summary that captures the key information, topics, and content. Focus on what someone would need to know to determine if this page is relevant to their query."
                },
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": "Please analyze this document page and provide a concise summary of its content, including key topics, data, and information present."
                        },
                        {
                            "type": "image_path",
                            "image_path": page.image_path,
                            "detail": "high"
                        }
                    ]
                }
            ]
            
            # Generate summary using provider
            summary = await self.provider.process_multimodal_messages(
                messages=messages,
                max_tokens=200,
                temperature=0.3
            )
            
            # Create new page with summary
            summarized_page = Page(
                page_number=page.page_number,
                image_path=page.image_path,
                content_summary=summary,
                metadata={
                    **page.metadata,
                    'summary_generated': True,
                    'summary_model': self.config.provider
                }
            )
            
            return summarized_page
            
        except Exception as e:
            logger.error(f"Failed to summarize page {page.page_number}: {e}")
            # Return original page without summary
            return page
    
    async def summarize_document(self, document: Document) -> Document:
        """
        Generate summaries for all pages in a document and create document summary
        
        Args:
            document: Document to summarize
            
        Returns:
            Document with page summaries and document summary
        """
        logger.info(f"Summarizing document: {document.name}")
        
        # Summarize all pages
        summarized_pages = await self.summarize_pages(document.pages)
        
        # Generate document summary from all page images
        document_summary = None
        if self.config.document_summary_enabled:
            document_summary = await self._generate_document_summary(summarized_pages, document.name)
        
        # Create updated document
        updated_document = Document(
            id=document.id,
            name=document.name,
            pages=summarized_pages,
            summary=document_summary,
            status=document.status,
            metadata={
                **document.metadata,
                'page_summaries_generated': True,
                'document_summary_generated': document_summary is not None,
                'summary_model': self.config.provider
            },
            created_at=document.created_at
        )
        
        logger.info(f"Completed document summarization: {document.name}")
        return updated_document
    
    async def _generate_document_summary(self, pages: List[Page], document_name: str) -> Optional[str]:
        """Generate overall document summary using all page images in a single vision call"""
        try:
            # Get all page image paths
            image_paths = [page.image_path for page in pages if page.image_path]
            
            if not image_paths:
                logger.warning("No page images available for document summary")
                return None
            
            # Build messages for document summary
            messages = [
                {
                    "role": "system",
                    "content": "You are a document analysis expert. Analyze all pages of this document and create a comprehensive summary that captures the overall content, main themes, key information, and purpose of the entire document. Consider how all pages work together to form a complete document."
                },
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": f"Please analyze this complete document titled '{document_name}' and provide a comprehensive summary. Look at all pages together to understand the document's overall structure, main themes, key information, and purpose."
                        }
                    ]
                }
            ]
            
            # Add all page images to the user message
            for image_path in image_paths:
                messages[1]["content"].append({
                    "type": "image_path",
                    "image_path": image_path,
                    "detail": "high"
                })
            
            # Generate document summary using provider
            summary = await self.provider.process_multimodal_messages(
                messages=messages,
                max_tokens=400,
                temperature=0.3
            )
            
            logger.debug(f"Generated document summary: {summary[:50]}...")
            return summary
            
        except Exception as e:
            logger.error(f"Failed to generate document summary: {e}")
            return None
    
    
    async def update_page_summary(self, page: Page) -> Page:
        """Update summary for a single page"""
        return await self._summarize_single_page(page)
    
    def is_summary_enabled(self) -> bool:
        """Check if page summarization is enabled"""
        return self.config.page_summary_enabled
    
    def get_summary_stats(self) -> Dict[str, Any]:
        """Get summarizer statistics"""
        return {
            'provider': self.config.provider,
            'page_summary_enabled': self.config.page_summary_enabled,
            'document_summary_enabled': self.config.document_summary_enabled,
            'batch_size': self.config.batch_size,
            'model': getattr(self.config, f'{self.config.provider}_vision_model', 'unknown')
        }