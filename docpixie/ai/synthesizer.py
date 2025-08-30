"""
Response synthesizer for DocPixie RAG Agent
Combines multiple task results into coherent final answers
"""

import logging
from typing import List

from ..models.agent import TaskResult
from ..providers.base import BaseProvider
from .prompts import SYNTHESIS_PROMPT, SYSTEM_SYNTHESIS

logger = logging.getLogger(__name__)


class ResponseSynthesizer:
    """
    Synthesizes multiple task results into a comprehensive final response
    Key feature: Combines findings from different tasks into coherent narrative
    """

    def __init__(self, provider: BaseProvider):
        self.provider = provider

    async def synthesize_response(
        self,
        original_query: str,
        task_results: List[TaskResult]
    ) -> str:
        """
        Synthesize multiple task results into a final comprehensive response

        Args:
            original_query: The user's original question
            task_results: List of completed task results to combine

        Returns:
            Synthesized response that addresses the original query
        """
        if not task_results:
            logger.warning("No task results provided for synthesis")
            return "I couldn't find any relevant information to answer your query."

        try:
            logger.info(f"Synthesizing response from {len(task_results)} task results")

            # Build results text from all task findings
            results_text = self._build_results_text(task_results)

            # Generate synthesis prompt
            prompt = SYNTHESIS_PROMPT.format(
                original_query=original_query,
                results_text=results_text
            )

            messages = [
                {"role": "system", "content": SYSTEM_SYNTHESIS},
                {"role": "user", "content": prompt}
            ]

            # Get synthesized response
            result = await self.provider.process_text_messages(
                messages=messages,
                max_tokens=2048,  # Longer response for synthesis
                temperature=0.2  # Low temperature for consistent synthesis
            )

            logger.info("Successfully synthesized final response")
            return result.strip()

        except Exception as e:
            logger.error(f"Failed to synthesize response: {e}")
            # Fallback: return basic combination of results
            return self._create_fallback_response(original_query, task_results)

    def _build_results_text(self, task_results: List[TaskResult]) -> str:
        """Build formatted text from all task results"""
        results_sections = []

        for i, result in enumerate(task_results, 1):
            section = f"""TASK {i}: {result.task.name}
Description: {result.task.description}
Analysis: {result.analysis}

---"""
            results_sections.append(section)

        return "\n".join(results_sections)

    def _create_fallback_response(
        self,
        original_query: str,
        task_results: List[TaskResult]
    ) -> str:
        """Create a simple fallback response if synthesis fails"""
        logger.warning("Using fallback response synthesis")

        response_parts = [
            f"Based on my analysis of the documents, here's what I found regarding your query: {original_query}\n"
        ]

        for i, result in enumerate(task_results, 1):
            response_parts.append(f"**{result.task.name}:**")
            response_parts.append(result.analysis)

            if i < len(task_results):
                response_parts.append("")  # Add blank line between results

        return "\n".join(response_parts)

    async def synthesize_single_result(
        self,
        original_query: str,
        task_result: TaskResult
    ) -> str:
        """
        Handle synthesis for single task result (simpler case)

        Args:
            original_query: The user's original question
            task_result: Single task result to present

        Returns:
            Formatted response for single task
        """
        try:
            # For single results, we can often just clean up the analysis
            # But still use synthesis prompt for consistency
            return await self.synthesize_response(original_query, [task_result])

        except Exception as e:
            logger.error(f"Failed to synthesize single result: {e}")

            # Simple fallback for single result
            response = f"Based on my analysis, here's what I found regarding your query:\n\n"
            response += f"**{task_result.task.name}**\n{task_result.analysis}"

            return response

    def validate_synthesis_quality(self, synthesized_response: str) -> bool:
        """
        Basic validation of synthesis quality

        Args:
            synthesized_response: The synthesized response to validate

        Returns:
            True if response meets basic quality criteria
        """
        if not synthesized_response or not synthesized_response.strip():
            return False

        # Check minimum length (synthesis should be substantial)
        if len(synthesized_response.strip()) < 50:
            return False

        # Check it doesn't just repeat the prompt
        if "SYNTHESIS_PROMPT" in synthesized_response:
            return False

        # Check for basic structure indicators
        if "I couldn't find" in synthesized_response and len(synthesized_response) < 100:
            return False

        return True
