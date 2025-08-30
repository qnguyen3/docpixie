"""
Vision-based page selector for DocPixie RAG Agent
Selects relevant pages by analyzing page images directly with vision models
"""

import json
import logging
from typing import List, Dict, Any, Optional

from ..models.document import Page
from ..providers.base import BaseProvider
from ..core.config import DocPixieConfig
from ..exceptions import PageSelectionError
from .prompts import SYSTEM_PAGE_SELECTOR, USER_VISION_ANALYSIS, VISION_PAGE_SELECTION_PROMPT

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
        task_pages: List[Page]
    ) -> List[Page]:
        """
        Select most relevant pages by analyzing page IMAGES with vision model

        Args:
            query: The question/task to find pages for
            task_pages: Pages from the task's assigned document

        Returns:
            List of selected pages, ordered by relevance

        Raises:
            PageSelectionError: If page selection fails
        """
        if not task_pages:
            logger.warning("No pages provided for selection")
            return []

        try:
            logger.info(f"Selecting most relevant pages from {len(task_pages)} task pages")

            # Build vision-based selection message
            messages = self._build_vision_selection_messages(query, task_pages)

            # Use vision model to analyze page images and select best ones
            result = await self.provider.process_multimodal_messages(
                messages=messages,
                max_tokens=200,
                temperature=0.1  # Low temperature for consistent selection
            )

            # Parse selection result
            selected_pages = self._parse_page_selection(result, task_pages)

            logger.info(f"Successfully selected {len(selected_pages)} pages")
            return selected_pages

        except Exception as e:
            logger.error(f"Vision page selection failed: {e}")
            raise PageSelectionError(f"Failed to select pages for task: {e}")

    def _build_vision_selection_messages(
        self,
        query: str,
        all_pages: List[Page]
    ) -> List[Dict[str, Any]]:
        """
        Build multimodal message with all page images for vision analysis
        This is the key method that makes our system vision-first
        """
        messages = [
            {
                "role": "system",
                "content": SYSTEM_PAGE_SELECTOR
            }
        ]
        user_content = []
        # Add ALL page images to the message for vision analysis
        for i, page in enumerate(all_pages, 1):
            user_content.extend([
                {
                    "type": "image_path",
                    "image_path": page.image_path,
                    "detail": self.config.vision_detail
                },
                {
                    "type": "text",
                    "text": f"[Page {i}]"
                }
            ])

        user_content.append(
            {
                "type": "text",
                "text": VISION_PAGE_SELECTION_PROMPT.format(query=query)
            }
        )

        messages.append(
            {
                "role": "user",
                "content": user_content
            }
        )

        return messages

    def _parse_page_selection(
        self,
        result: str,
        all_pages: List[Page]
    ) -> List[Page]:
        """
        Parse the vision model's page selection response
        """
        try:
            # Parse JSON response
            selection_data = json.loads(result.strip())
            selected_indices = selection_data.get("selected_pages", [])
            # reasoning = selection_data.get("reasoning", "No reasoning provided")

            # logger.debug(f"Vision model reasoning: {reasoning}")

            # Convert 1-based indices to actual pages
            selected_pages = []
            for idx in selected_indices:
                if isinstance(idx, int) and 1 <= idx <= len(all_pages):
                    page = all_pages[idx - 1]  # Convert to 0-based index
                    selected_pages.append(page)
                    logger.debug(f"Selected page {idx}: {page.image_path}")

            # If no valid pages were selected, return empty list and raise error
            if not selected_pages:
                logger.error("No valid pages selected by vision model")
                raise PageSelectionError("Vision model failed to select any valid pages")

            return selected_pages

        except (json.JSONDecodeError, KeyError, TypeError) as e:
            logger.error(f"Failed to parse page selection JSON: {e}")
            logger.debug(f"Raw vision model response: {result}")

            # Raise error instead of fallback - no artificial limits
            raise PageSelectionError(f"Failed to parse vision model page selection response: {e}, raw response: \n{result}")

    async def select_pages_with_context(
        self,
        query: str,
        all_pages: List[Page],
        previous_selections: List[Page] = None
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
            return await self.select_pages_for_task(context_query, remaining_pages)
        else:
            # No previous context, use normal selection
            return await self.select_pages_for_task(query, all_pages)
