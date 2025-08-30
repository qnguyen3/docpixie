"""
Query Reformulator - Creates optimized search queries from conversation context
"""

import json
import logging

from ..providers.base import BaseProvider
from ..exceptions import QueryReformulationError
from .prompts import QUERY_REFORMULATION_PROMPT, SYSTEM_QUERY_REFORMULATOR

logger = logging.getLogger(__name__)


class QueryReformulator:
    """
    Reformulates queries by resolving references for better search

    Focuses on:
    - Resolving pronouns and references (e.g., "it", "this", "that")
    - Keeping queries concise and focused on current intent
    - NOT combining multiple questions or intents
    - Maintaining optimal length for search
    """

    def __init__(self, provider: BaseProvider):
        self.provider = provider

    async def reformulate_with_context(
        self,
        current_query: str,
        conversation_context: str
    ) -> str:
        """
        Reformulate query by resolving references while keeping it concise

        Args:
            current_query: The current user query
            conversation_context: Processed context from ContextProcessor

        Returns:
            Reformulated query with resolved references

        Raises:
            QueryReformulationError: If reformulation fails
        """
        try:
            # Build prompt using existing template
            prompt = QUERY_REFORMULATION_PROMPT.format(
                conversation_context=conversation_context,
                recent_topics="", # Let AI extract topics from context
                current_query=current_query
            )

            messages_for_api = [
                {"role": "system", "content": SYSTEM_QUERY_REFORMULATOR},
                {"role": "user", "content": prompt}
            ]

            response = await self.provider.process_text_messages(
                messages=messages_for_api,
                max_tokens=1024,
                temperature=0.2
            )

            # Parse JSON response
            result = None
            try:
                result = json.loads(response.strip())
                reformulated = result.get("reformulated_query", current_query)

                logger.info(f"Query reformulation: '{current_query}' → '{reformulated}'")
                return reformulated

            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse reformulation JSON: {response}")
                raise QueryReformulationError(f"Invalid JSON response from reformulation: {e}")

        except Exception as e:
            logger.error(f"Query reformulation failed: {e}")
            raise QueryReformulationError(f"Failed to reformulate query: {e}")
