"""
Context Processor - Handles conversation history summarization and context building
"""

import logging
from typing import List, Tuple, Optional

from ..models.agent import ConversationMessage
from ..providers.base import BaseProvider
from ..core.config import DocPixieConfig
from ..exceptions import ContextProcessingError
from .prompts import CONVERSATION_SUMMARIZATION_PROMPT

logger = logging.getLogger(__name__)


class ContextProcessor:
    """
    Processes conversation history to create optimized context for RAG
    
    When conversation exceeds max_turns:
    - Summarizes first turns_to_summarize turns 
    - Includes last turns_to_keep_full turns in full
    - Creates condensed context for query reformulation
    """
    
    def __init__(self, provider: BaseProvider, config: DocPixieConfig):
        self.provider = provider
        self.max_turns_before_summary = config.max_conversation_turns
        self.turns_to_summarize = config.turns_to_summarize
        self.turns_to_keep_full = config.turns_to_keep_full
    
    async def process_conversation_context(
        self,
        messages: List[ConversationMessage],
        current_query: str
    ) -> Tuple[str, List[ConversationMessage]]:
        """
        Process conversation history and return optimized context
        
        Args:
            messages: List of conversation messages
            current_query: The current user query
            
        Returns:
            Tuple of (processed_context_string, messages_for_display)
            
        Raises:
            ContextProcessingError: If context processing fails
        """
        try:
            # Calculate number of turns (1 turn = 1 user message + 1 assistant message)
            turns = self._count_turns(messages)
            
            if turns <= self.max_turns_before_summary:
                # No summarization needed
                context = self._format_messages_as_context(messages)
                return context, messages
            
            logger.info(f"Conversation has {turns} turns, applying context summarization")
            
            # Split messages for summarization
            messages_to_summarize, messages_to_keep = self._split_messages_for_summary(messages)
            
            # Summarize the first part
            summary = await self._summarize_conversation_chunk(messages_to_summarize)
            
            # Build final context
            context_parts = []
            
            # Add summary
            context_parts.append(f"Previous Conversation Summary:\n{summary}\n")
            
            # Add recent messages in full
            if messages_to_keep:
                context_parts.append("Recent Conversation:")
                context_parts.append(self._format_messages_as_context(messages_to_keep))
            
            # Add current query
            context_parts.append(f"\nCurrent Query: {current_query}")
            
            final_context = "\n".join(context_parts)
            
            # Create display messages (summary + recent)
            summary_message = ConversationMessage(
                role="system",
                content=f"[Conversation Summary of First {self.turns_to_summarize} Turns]\n{summary}"
            )
            display_messages = [summary_message] + messages_to_keep
            
            return final_context, display_messages
            
        except Exception as e:
            logger.error(f"Context processing failed: {e}")
            raise ContextProcessingError(f"Failed to process conversation context: {e}")
    
    def _count_turns(self, messages: List[ConversationMessage]) -> int:
        """Count conversation turns (user messages only)"""
        user_messages = sum(1 for msg in messages if msg.role == "user")
        return user_messages
    
    def _split_messages_for_summary(
        self, 
        messages: List[ConversationMessage]
    ) -> Tuple[List[ConversationMessage], List[ConversationMessage]]:
        """Split messages into parts to summarize and keep"""
        # Find the split point based on turns
        turn_count = 0
        split_index = 0
        
        for i in range(0, len(messages), 2):  # Process in pairs
            if i + 1 < len(messages) and messages[i].role == "user":
                turn_count += 1
                if turn_count == self.turns_to_summarize:
                    split_index = i + 2  # Include the assistant response
                    break
        
        messages_to_summarize = messages[:split_index]
        messages_to_keep = messages[split_index:]
        
        # Ensure we keep at most the last N turns
        if self.turns_to_keep_full > 0:
            max_messages_to_keep = self.turns_to_keep_full * 2  # Each turn has 2 messages
            if len(messages_to_keep) > max_messages_to_keep:
                messages_to_keep = messages_to_keep[-max_messages_to_keep:]
        
        return messages_to_summarize, messages_to_keep
    
    def _format_messages_as_context(self, messages: List[ConversationMessage]) -> str:
        """Format messages as readable context"""
        formatted_parts = []
        
        for msg in messages:
            role = "User" if msg.role == "user" else "Assistant"
            formatted_parts.append(f"{role}: {msg.content}")
        
        return "\n\n".join(formatted_parts)
    
    async def _summarize_conversation_chunk(self, messages: List[ConversationMessage]) -> str:
        """Summarize a chunk of conversation"""
        try:
            conversation_text = self._format_messages_as_context(messages)
            
            prompt = CONVERSATION_SUMMARIZATION_PROMPT.format(
                conversation_text=conversation_text
            )

            messages_for_api = [
                {"role": "system", "content": "You are a helpful assistant that creates concise conversation summaries."},
                {"role": "user", "content": prompt}
            ]

            summary = await self.provider.process_text_messages(
                messages=messages_for_api,
                max_tokens=500,
                temperature=0.3
            )
            
            return summary.strip()
            
        except Exception as e:
            logger.error(f"Conversation summarization failed: {e}")
            raise ContextProcessingError(f"Failed to summarize conversation: {e}")