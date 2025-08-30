"""
Vision-based page selector for DocPixie RAG Agent
Selects relevant pages by analyzing page images directly with vision models
"""

import json
import logging
from typing import List, Dict, Any

from ..models.document import Page
from ..providers.base import BaseProvider
from ..core.config import DocPixieConfig
from .prompts import SYSTEM_PAGE_SELECTOR

logger = logging.getLogger(__name__)


class VisionPageSelector:
    """
    Selects relevant document pages using vision model analysis
    Key feature: Analyzes actual page IMAGES, not text summaries
    """
    
    def __init__(self, provider: BaseProvider, config: DocPixieConfig):
        self.provider = provider
        self.config = config
    
    async def select_pages_for_task(
        self, 
        query: str, 
        all_pages: List[Page], 
        max_pages: int = 6
    ) -> List[Page]:
        """
        Select most relevant pages by analyzing page IMAGES with vision model
        
        Args:
            query: The question/task to find pages for
            all_pages: All available pages from all documents
            max_pages: Maximum number of pages to select
            
        Returns:
            List of selected pages, ordered by relevance
        """
        if not all_pages:
            logger.warning("No pages provided for selection")
            return []
        
        if len(all_pages) <= max_pages:
            logger.info(f"Only {len(all_pages)} pages available, returning all")
            return all_pages
        
        try:
            logger.info(f"Selecting {max_pages} most relevant pages from {len(all_pages)} total pages")
            
            # Build vision-based selection message
            messages = self._build_vision_selection_messages(query, all_pages, max_pages)
            
            # Use vision model to analyze page images and select best ones
            result = await self.provider.process_multimodal_messages(
                messages=messages,
                max_tokens=200,
                temperature=0.1  # Low temperature for consistent selection
            )
            
            # Parse selection result
            selected_pages = self._parse_page_selection(result, all_pages, max_pages)
            
            logger.info(f"Successfully selected {len(selected_pages)} pages")
            return selected_pages
            
        except Exception as e:
            logger.error(f"Vision page selection failed: {e}")
            # Fallback: return first N pages
            logger.warning(f"Falling back to first {max_pages} pages")
            return all_pages[:max_pages]
    
    def _build_vision_selection_messages(
        self, 
        query: str, 
        all_pages: List[Page], 
        max_pages: int
    ) -> List[Dict[str, Any]]:
        """
        Build multimodal message with all page images for vision analysis
        This is the key method that makes our system vision-first
        """
        messages = [
            {
                "role": "system", 
                "content": SYSTEM_PAGE_SELECTOR
            },
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": f"""Analyze these document page images and select the {max_pages} most relevant pages for this query:

QUERY: {query}

Look at each page image carefully and determine which pages are most likely to contain information that would help answer the query. Consider:
1. Text content visible in the page
2. Charts, graphs, tables, or diagrams that might be relevant
3. Headers, titles, or section names that relate to the query
4. Overall page structure and content type

Return a JSON object with the page numbers that are most relevant:
{{"selected_pages": [1, 3, 7], "reasoning": "Brief explanation of why these pages were selected"}}

Here are the page images to analyze:"""
                    }
                ]
            }
        ]
        
        # Add ALL page images to the message for vision analysis
        for i, page in enumerate(all_pages, 1):
            messages[1]["content"].extend([
                {
                    "type": "image_path",
                    "image_path": page.image_path,
                    "detail": "low"  # Use low detail for page selection to be faster
                },
                {
                    "type": "text",
                    "text": f"[Page {i}]"
                }
            ])
        
        return messages
    
    def _parse_page_selection(
        self, 
        result: str, 
        all_pages: List[Page], 
        max_pages: int
    ) -> List[Page]:
        """
        Parse the vision model's page selection response
        """
        try:
            # Parse JSON response
            selection_data = json.loads(result.strip())
            selected_indices = selection_data.get("selected_pages", [])
            reasoning = selection_data.get("reasoning", "No reasoning provided")
            
            logger.debug(f"Vision model reasoning: {reasoning}")
            
            # Convert 1-based indices to actual pages
            selected_pages = []
            for idx in selected_indices:
                if isinstance(idx, int) and 1 <= idx <= len(all_pages):
                    page = all_pages[idx - 1]  # Convert to 0-based index
                    selected_pages.append(page)
                    logger.debug(f"Selected page {idx}: {page.image_path}")
            
            # Ensure we don't exceed max_pages
            if len(selected_pages) > max_pages:
                selected_pages = selected_pages[:max_pages]
                logger.debug(f"Trimmed selection to {max_pages} pages")
            
            # If no valid pages were selected, fallback to first pages
            if not selected_pages:
                logger.warning("No valid pages selected by vision model, using fallback")
                selected_pages = all_pages[:max_pages]
            
            return selected_pages
            
        except (json.JSONDecodeError, KeyError, TypeError) as e:
            logger.error(f"Failed to parse page selection JSON: {e}")
            logger.debug(f"Raw vision model response: {result}")
            
            # Fallback: return first N pages
            return all_pages[:max_pages]
    
    async def select_pages_with_context(
        self,
        query: str,
        all_pages: List[Page],
        previous_selections: List[Page] = None,
        max_pages: int = 6
    ) -> List[Page]:
        """
        Select pages with context from previous selections (for iterative selection)
        """
        if previous_selections:
            # Filter out already selected pages
            remaining_pages = [
                page for page in all_pages 
                if page.image_path not in {p.image_path for p in previous_selections}
            ]
            
            if not remaining_pages:
                logger.info("All pages have been previously selected")
                return []
            
            # Select from remaining pages with context about what was already selected
            context_query = f"{query} (Note: Previous pages already analyzed related topics, focus on different aspects)"
            return await self.select_pages_for_task(context_query, remaining_pages, max_pages)
        else:
            # No previous context, use normal selection
            return await self.select_pages_for_task(query, all_pages, max_pages)