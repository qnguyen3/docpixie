"""
DocPixie Configuration
Simplified version of production config without embedding/vector DB settings
"""

import os
from dataclasses import dataclass, field
from typing import Tuple, Optional, Dict, Any
from pathlib import Path


@dataclass
class DocPixieConfig:
    """DocPixie configuration with sensible defaults"""
    
    # Document Processing with PyMuPDF
    pdf_render_scale: float = 2.0  # Higher scale = better quality, larger files
    pdf_max_image_size: Tuple[int, int] = (2048, 2048)
    jpeg_quality: int = 90
    thumbnail_size: Tuple[int, int] = (256, 256)  # For quick page selection
    
    # Mode-specific settings
    flash_max_pages: int = 5
    flash_vision_detail: str = "low"  # Use thumbnails for speed
    flash_timeout: int = 15  # seconds
    
    pro_max_pages: int = 15
    pro_vision_detail: str = "high"  # Use full resolution
    pro_timeout: int = 45  # seconds
    pro_synthesis_enabled: bool = True
    
    # Processing
    batch_size: int = 10  # Pages to process in parallel
    page_summary_enabled: bool = True
    document_summary_enabled: bool = True
    
    # Storage
    storage_type: str = "local"  # local, memory, s3
    local_storage_path: str = "./docpixie_data"
    
    # AI Provider Settings (Provider-agnostic)
    provider: str = "openai"  # openai, anthropic, local
    flash_model: str = "gpt-4o-mini"  # Faster, cheaper model for Flash mode
    pro_model: str = "gpt-4o"  # Better model for Pro mode  
    vision_model: str = "gpt-4o"  # Vision model for multimodal analysis
    
    # API keys loaded from environment variables only
    openai_api_key: Optional[str] = None
    anthropic_api_key: Optional[str] = None
    openrouter_api_key: Optional[str] = None
    
    # Request settings
    max_retries: int = 3
    request_timeout: int = 60
    
    # Caching
    enable_cache: bool = True
    cache_ttl: int = 3600  # 1 hour
    cache_max_size: int = 100
    
    # Agent Settings
    max_agent_iterations: int = 5  # Maximum adaptive planning iterations
    max_pages_per_task: int = 6    # Maximum pages to analyze per task
    max_tasks_per_plan: int = 4    # Maximum tasks in initial plan
    enable_conversation: bool = True  # Enable conversation support
    
    # Conversation Processing Settings
    max_conversation_turns: int = 8  # When to start summarizing conversation
    turns_to_summarize: int = 5      # How many turns to summarize
    turns_to_keep_full: int = 3      # How many recent turns to keep in full
    
    # Logging
    log_level: str = "INFO"
    log_requests: bool = False
    
    def __post_init__(self):
        """Initialize and validate configuration"""
        # Create storage directory if it doesn't exist
        if self.storage_type == "local":
            Path(self.local_storage_path).mkdir(parents=True, exist_ok=True)
        
        # Load API keys from environment if not provided
        if not self.openai_api_key:
            self.openai_api_key = os.getenv("OPENAI_API_KEY")
        
        if not self.anthropic_api_key:
            self.anthropic_api_key = os.getenv("ANTHROPIC_API_KEY")
        
        if not self.openrouter_api_key:
            self.openrouter_api_key = os.getenv("OPENROUTER_API_KEY")
        
        # Set provider-specific default models if using defaults
        self._set_provider_defaults()
        
        # Skip validation with test API keys (for testing)
        if self.openai_api_key != "test-key" and self.anthropic_api_key != "test-key" and self.openrouter_api_key != "test-key":
            # Validate required settings based on provider
            if self.provider == "openai" and not self.openai_api_key:
                raise ValueError("OpenAI API key is required when using OpenAI provider")
            
            if self.provider == "anthropic" and not self.anthropic_api_key:
                raise ValueError("Anthropic API key is required when using Anthropic provider")
            
            if self.provider == "openrouter" and not self.openrouter_api_key:
                raise ValueError("OpenRouter API key is required when using OpenRouter provider")
        
        # Validate image settings
        if self.pdf_render_scale <= 0:
            raise ValueError("PDF render scale must be positive")
        
        if self.jpeg_quality < 1 or self.jpeg_quality > 100:
            raise ValueError("JPEG quality must be between 1 and 100")
    
    def _set_provider_defaults(self):
        """Set appropriate default models based on provider"""
        provider_defaults = {
            "openai": {
                "flash_model": "gpt-4o-mini",
                "pro_model": "gpt-4o", 
                "vision_model": "gpt-4o"
            },
            "anthropic": {
                "flash_model": "claude-3-haiku-20240307",
                "pro_model": "claude-3-opus-20240229",
                "vision_model": "claude-3-opus-20240229"
            },
            "openrouter": {
                "flash_model": "openai/gpt-4o-mini",
                "pro_model": "openai/gpt-4o",
                "vision_model": "openai/gpt-4o"
            }
        }
        
        if self.provider in provider_defaults:
            defaults = provider_defaults[self.provider]
            # Only update if still using OpenAI defaults (means user didn't specify custom models)
            if self.flash_model == "gpt-4o-mini":
                self.flash_model = defaults["flash_model"]
            if self.pro_model == "gpt-4o":
                self.pro_model = defaults["pro_model"] 
            if self.vision_model == "gpt-4o":
                self.vision_model = defaults["vision_model"]
    
    @classmethod
    def from_dict(cls, config_dict: Dict[str, Any]) -> 'DocPixieConfig':
        """Create config from dictionary"""
        return cls(**config_dict)
    
    @classmethod
    def from_env(cls) -> 'DocPixieConfig':
        """Create config from environment variables"""
        config_dict = {}
        
        # Map environment variables to config fields
        env_mapping = {
            'DOCPIXIE_PROVIDER': 'provider',
            'DOCPIXIE_STORAGE_PATH': 'local_storage_path',
            'DOCPIXIE_FLASH_MAX_PAGES': 'flash_max_pages',
            'DOCPIXIE_PRO_MAX_PAGES': 'pro_max_pages',
            'DOCPIXIE_JPEG_QUALITY': 'jpeg_quality',
            'DOCPIXIE_ENABLE_CACHE': 'enable_cache',
            'DOCPIXIE_LOG_LEVEL': 'log_level',
        }
        
        for env_var, config_field in env_mapping.items():
            value = os.getenv(env_var)
            if value is not None:
                # Convert string values to appropriate types
                if config_field in ['flash_max_pages', 'pro_max_pages', 'jpeg_quality']:
                    config_dict[config_field] = int(value)
                elif config_field in ['enable_cache']:
                    config_dict[config_field] = value.lower() in ('true', '1', 'yes')
                else:
                    config_dict[config_field] = value
        
        return cls(**config_dict)
    
    def get_mode_config(self, mode: str) -> Dict[str, Any]:
        """Get configuration for a specific mode"""
        if mode == "flash":
            return {
                'max_pages': self.flash_max_pages,
                'vision_detail': self.flash_vision_detail,
                'timeout': self.flash_timeout,
                'model': self.flash_model
            }
        elif mode == "pro":
            return {
                'max_pages': self.pro_max_pages,
                'vision_detail': self.pro_vision_detail,
                'timeout': self.pro_timeout,
                'synthesis_enabled': self.pro_synthesis_enabled,
                'model': self.pro_model
            }
        else:
            raise ValueError(f"Unknown mode: {mode}")
    
    def validate_provider_config(self) -> None:
        """Validate provider-specific configuration"""
        if self.provider == "openai":
            if not self.openai_api_key:
                raise ValueError("OpenAI API key is required")
        elif self.provider == "anthropic":
            if not self.anthropic_api_key:
                raise ValueError("Anthropic API key is required")
        elif self.provider == "openrouter":
            if not self.openrouter_api_key:
                raise ValueError("OpenRouter API key is required")
        else:
            raise ValueError(f"Unsupported provider: {self.provider}")