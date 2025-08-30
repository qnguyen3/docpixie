"""
Page summarizer for generating document summaries
"""

import asyncio
from typing import List, Optional, Dict, Any
import logging

from ..providers.base import BaseProvider
from ..models.document import Document, Page
from ..core.config import DocPixieConfig
from .prompts import SYSTEM_VISION_EXPERT

logger = logging.getLogger(__name__)


class PageSummarizer:
    """Generates summaries for document pages using vision models"""

    def __init__(self, config: DocPixieConfig, provider: Optional[BaseProvider] = None):
        self.config = config
        if provider:
            self.provider = provider
        else:
            from ..providers.factory import create_provider
            self.provider = create_provider(config)



    async def summarize_document(self, document: Document) -> Document:
        """
        Generate document summary from all page images

        Args:
            document: Document to summarize

        Returns:
            Document with document summary
        """
        logger.info(f"Summarizing document: {document.name}")

        # Always generate document summary from all page images
        document_summary = await self._generate_document_summary(document.pages, document.name)

        # Create updated document
        updated_document = Document(
            id=document.id,
            name=document.name,
            pages=document.pages,
            summary=document_summary,
            status=document.status,
            metadata={
                **document.metadata,
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
                    "detail": self.config.vision_detail
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



    def get_summary_stats(self) -> Dict[str, Any]:
        """Get summarizer statistics"""
        return {
            'provider': self.config.provider,
            'model': self.config.vision_model
        }
