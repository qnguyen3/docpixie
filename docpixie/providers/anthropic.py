"""
Anthropic Claude provider for raw API operations
"""

import logging
from typing import List, Dict, Any

from .base import BaseProvider, ProviderError
from ..core.config import DocPixieConfig

logger = logging.getLogger(__name__)


class AnthropicProvider(BaseProvider):
    """Anthropic Claude provider for raw API operations"""
    
    def __init__(self, config: DocPixieConfig):
        super().__init__(config)
        
        if not config.anthropic_api_key:
            raise ValueError("Anthropic API key is required")
        
        # Import here to make it optional dependency
        try:
            import anthropic
            self.client = anthropic.AsyncAnthropic(api_key=config.anthropic_api_key)
        except ImportError:
            raise ImportError("Anthropic library not found. Install with: pip install anthropic")
        
        self.model = config.anthropic_model_pro  # Use Pro model for vision
    
    async def process_text_messages(
        self, 
        messages: List[Dict[str, Any]], 
        max_tokens: int = 300, 
        temperature: float = 0.3
    ) -> str:
        """Process text-only messages through Anthropic API"""
        try:
            # Convert system message format for Anthropic
            claude_messages = self._prepare_claude_text_messages(messages)
            
            response = await self.client.messages.create(
                model=self.model,
                max_tokens=max_tokens,
                temperature=temperature,
                messages=claude_messages
            )
            
            result = response.content[0].text.strip()
            logger.debug(f"Anthropic text response: {result[:50]}...")
            
            return result
            
        except Exception as e:
            logger.error(f"Anthropic text processing failed: {e}")
            raise ProviderError(f"Text processing failed: {e}", "anthropic")
    
    async def process_multimodal_messages(
        self, 
        messages: List[Dict[str, Any]], 
        max_tokens: int = 300, 
        temperature: float = 0.3
    ) -> str:
        """Process multimodal messages (text + images) through Anthropic Vision API"""
        try:
            # Process messages to convert image paths to base64
            claude_messages = self._prepare_claude_multimodal_messages(messages)
            
            response = await self.client.messages.create(
                model=self.model,
                max_tokens=max_tokens,
                temperature=temperature,
                messages=claude_messages
            )
            
            result = response.content[0].text.strip()
            logger.debug(f"Anthropic multimodal response: {result[:50]}...")
            
            return result
            
        except Exception as e:
            logger.error(f"Anthropic multimodal processing failed: {e}")
            raise ProviderError(f"Multimodal processing failed: {e}", "anthropic")
    
    def _prepare_claude_text_messages(self, messages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Prepare text-only messages for Claude API (handle system messages)"""
        claude_messages = []
        
        for message in messages:
            if message["role"] == "system":
                # Claude handles system messages differently - we'll prepend to first user message
                continue
            else:
                claude_messages.append(message)
        
        # Prepend system message content to first user message if present
        system_content = None
        for message in messages:
            if message["role"] == "system":
                system_content = message["content"]
                break
        
        if system_content and claude_messages and claude_messages[0]["role"] == "user":
            # Prepend system content to first user message
            original_content = claude_messages[0]["content"]
            claude_messages[0]["content"] = f"{system_content}\n\n{original_content}"
        
        return claude_messages
    
    def _prepare_claude_multimodal_messages(self, messages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Prepare multimodal messages for Claude API by converting image paths to base64"""
        claude_messages = []
        system_content = None
        
        # Extract system message
        for message in messages:
            if message["role"] == "system":
                system_content = message["content"]
                break
        
        for message in messages:
            if message["role"] == "system":
                continue  # Skip system message, will be prepended to user message
            elif message["role"] == "user" and isinstance(message["content"], list):
                # User message with multimodal content
                processed_content = []
                
                for content_item in message["content"]:
                    if content_item["type"] == "text":
                        processed_content.append(content_item)
                    elif content_item["type"] == "image_path":
                        # Convert image path to Claude format
                        image_path = content_item["image_path"]
                        if self._validate_image_path(image_path):
                            encoded_image = self._encode_image(image_path)
                            processed_content.append({
                                "type": "image",
                                "source": {
                                    "type": "base64",
                                    "media_type": "image/jpeg",
                                    "data": encoded_image
                                }
                            })
                        else:
                            logger.warning(f"Skipping invalid image path: {image_path}")
                    else:
                        # Pass through other content types
                        processed_content.append(content_item)
                
                # Prepend system content to first user message
                if system_content and len(claude_messages) == 0:
                    processed_content.insert(0, {
                        "type": "text",
                        "text": system_content
                    })
                
                claude_messages.append({
                    "role": message["role"],
                    "content": processed_content
                })
            else:
                # Regular text message
                claude_messages.append(message)
        
        return claude_messages