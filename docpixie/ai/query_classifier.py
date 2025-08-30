"""
Query Classifier - Determines if queries need document retrieval
"""

import json
import logging

from ..providers.base import BaseProvider
from ..exceptions import QueryClassificationError
from .prompts import QUERY_CLASSIFICATION_PROMPT, SYSTEM_QUERY_CLASSIFIER

logger = logging.getLogger(__name__)


class QueryClassifier:
    """
    Classifies queries to determine processing strategy

    Key classification:
    - needs_documents: Whether query requires document retrieval
    """

    def __init__(self, provider: BaseProvider):
        self.provider = provider

    async def classify_query(self, query: str) -> dict:
        """
        Classify a query to determine processing approach

        Args:
            query: The user's query (potentially reformulated)

        Returns:
            Dict with classification results:
            {
                "reasoning": "explanation",
                "needs_documents": bool
            }

        Raises:
            QueryClassificationError: If classification fails
        """
        result = None

        try:
            # Build classification prompt
            prompt = QUERY_CLASSIFICATION_PROMPT.format(query=query)

            messages_for_api = [
                {"role": "system", "content": SYSTEM_QUERY_CLASSIFIER},
                {"role": "user", "content": prompt}
            ]

            response = await self.provider.process_text_messages(
                messages=messages_for_api,
                max_tokens=450,
                temperature=0.1
            )

            # Parse JSON response
            try:
                result = json.loads(response.strip())

                # Validate required fields
                if "reasoning" not in result or "needs_documents" not in result:
                    raise QueryClassificationError(
                        f"Missing required fields in classification response: {result}"
                    )

                logger.info(f"Query classified: needs_documents={result['needs_documents']}, "
                           f"reasoning='{result['reasoning']}'")

                return result

            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse classification JSON: {response}")
                raise QueryClassificationError(f"Invalid JSON response from classification: {e}. Raw response: {result}")

        except Exception as e:
            logger.error(f"Query classification failed: {e}")
            raise QueryClassificationError(f"Failed to classify query: {e}")
