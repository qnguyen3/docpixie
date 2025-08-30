"""
OpenRouter provider for raw API operations
Uses OpenAI client with OpenRouter's API endpoint
"""

import logging
from typing import List, Dict, Any

from .base import BaseProvider, ProviderError
from ..core.config import DocPixieConfig

logger = logging.getLogger(__name__)


class OpenRouterProvider(BaseProvider):
    """OpenRouter provider for raw API operations"""
    
    def __init__(self, config: DocPixieConfig):
        super().__init__(config)
        
        if not config.openrouter_api_key:
            raise ValueError("OpenRouter API key is required")
        
        # Import here to make it optional dependency
        try:
            from openai import AsyncOpenAI
            self.client = AsyncOpenAI(
                api_key=config.openrouter_api_key,
                base_url="https://openrouter.ai/api/v1"
            )
        except ImportError:
            raise ImportError("OpenAI library not found. Install with: pip install openai")
        
        self.model = config.vision_model
    
    async def process_text_messages(
        self, 
        messages: List[Dict[str, Any]], 
        max_tokens: int = 300, 
        temperature: float = 0.3
    ) -> str:
        """Process text-only messages through OpenRouter API"""
        try:
            response = await self.client.chat.completions.create(
                model=self.config.model,
                messages=messages,
                max_tokens=max_tokens,
                temperature=temperature
            )
            
            result = response.choices[0].message.content.strip()
            logger.debug(f"OpenRouter text response: {result[:50]}...")
            
            return result
            
        except Exception as e:
            logger.error(f"OpenRouter text processing failed: {e}")
            raise ProviderError(f"Text processing failed: {e}", "openrouter")
    
    async def process_multimodal_messages(
        self, 
        messages: List[Dict[str, Any]], 
        max_tokens: int = 300, 
        temperature: float = 0.3
    ) -> str:
        """Process multimodal messages (text + images) through OpenRouter API"""
        try:
            # Process messages to convert image paths to data URLs
            processed_messages = self._prepare_openai_messages(messages)
            
            response = await self.client.chat.completions.create(
                model=self.model,  # Use vision model
                messages=processed_messages,
                max_tokens=max_tokens,
                temperature=temperature
            )
            
            result = response.choices[0].message.content.strip()
            logger.debug(f"OpenRouter multimodal response: {result[:50]}...")
            
            return result
            
        except Exception as e:
            logger.error(f"OpenRouter multimodal processing failed: {e}")
            raise ProviderError(f"Multimodal processing failed: {e}", "openrouter")
    
    def _prepare_openai_messages(self, messages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Prepare messages for OpenRouter API by converting image paths to data URLs"""
        processed_messages = []
        
        for message in messages:
            if message["role"] == "system":
                # System messages are text-only
                processed_messages.append(message)
            elif message["role"] == "user" and isinstance(message["content"], list):
                # User message with multimodal content
                processed_content = []
                
                for content_item in message["content"]:
                    if content_item["type"] == "text":
                        processed_content.append(content_item)
                    elif content_item["type"] == "image_path":
                        # Convert image path to OpenRouter format (same as OpenAI)
                        image_path = content_item["image_path"]
                        if self._validate_image_path(image_path):
                            image_data_url = self._create_image_data_url(image_path)
                            processed_content.append({
                                "type": "image_url",
                                "image_url": {
                                    "url": image_data_url,
                                    "detail": content_item.get("detail", "high")
                                }
                            })
                        else:
                            logger.warning(f"Skipping invalid image path: {image_path}")
                    else:
                        # Pass through other content types
                        processed_content.append(content_item)
                
                processed_messages.append({
                    "role": message["role"],
                    "content": processed_content
                })
            else:
                # Regular text message
                processed_messages.append(message)
        
        return processed_messages