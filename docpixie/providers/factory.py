"""
Provider factory for creating AI vision providers
"""

from typing import Union

from .base import BaseProvider
from .openai import OpenAIProvider
from .anthropic import AnthropicProvider
from .openrouter import OpenRouterProvider
from ..core.config import DocPixieConfig


def create_provider(config: DocPixieConfig) -> BaseProvider:
    """
    Create AI provider based on configuration
    
    Args:
        config: DocPixie configuration
        
    Returns:
        Configured provider instance
        
    Raises:
        ValueError: If provider is not supported
    """
    if config.provider == "openai":
        return OpenAIProvider(config)
    elif config.provider == "anthropic":
        return AnthropicProvider(config)
    elif config.provider == "openrouter":
        return OpenRouterProvider(config)
    else:
        raise ValueError(f"Unsupported provider: {config.provider}")


def get_available_providers() -> list[str]:
    """Get list of available provider names"""
    return ["openai", "anthropic", "openrouter"]


def validate_provider_config(provider: str, config: DocPixieConfig) -> bool:
    """
    Validate provider configuration
    
    Args:
        provider: Provider name
        config: Configuration to validate
        
    Returns:
        True if configuration is valid
        
    Raises:
        ValueError: If configuration is invalid
    """
    if provider not in get_available_providers():
        raise ValueError(f"Unknown provider: {provider}")
    
    if provider == "openai":
        if not config.openai_api_key:
            raise ValueError("OpenAI API key is required")
        if not config.vision_model:
            raise ValueError("Vision model is required")
        return True
    
    elif provider == "anthropic":
        if not config.anthropic_api_key:
            raise ValueError("Anthropic API key is required")
        if not config.vision_model:
            raise ValueError("Vision model is required")
        return True
    
    elif provider == "openrouter":
        if not config.openrouter_api_key:
            raise ValueError("OpenRouter API key is required")
        if not config.vision_model:
            raise ValueError("Vision model is required")
        return True
    
    return False