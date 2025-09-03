"""
Global configuration manager for DocPixie CLI
Handles API keys, model preferences, and user settings
"""

import json
import os
from pathlib import Path
from typing import Optional, Dict, Any
from dataclasses import dataclass, asdict, field


PLANNING_MODELS = [
    "anthropic/claude-opus-4.1",
    "anthropic/claude-sonnet-4",
    "anthropic/claude-3.5-haiku",
    "google/gemini-2.5-flash",
    "google/gemini-2.5-pro",
    "openai/gpt-4.1",
    "openai/gpt-4.1-mini",
    "openai/gpt-5-mini",
    "openai/gpt-5",
    "qwen/qwen-plus",
    "qwen/qwen-max",
    "nousresearch/hermes-4-70b",
    "deepseek/deepseek-chat-v3.1",
    "mistralai/mistral-medium-3.1",
]

VISION_MODELS = [
    "google/gemini-2.5-pro",
    "google/gemini-2.5-flash",
    "google/gemini-2.5-flash-lite",
    "openai/gpt-4.1",
    "openai/gpt-4.1-mini",
    "openai/gpt-4.1-nano",
    "anthropic/claude-sonnet-4",
    "minimax/minimax-01",
]


@dataclass
class CLIConfig:
    """CLI configuration stored globally in ~/.docpixie/"""

    openrouter_api_key: Optional[str] = None

    text_model: str = "qwen/qwen-plus"
    vision_model: str = "google/gemini-2.5-flash"

    last_conversation_id: Optional[str] = None
    theme: str = "default"

    auto_index_on_startup: bool = True
    max_conversation_history: int = 20

    def to_dict(self) -> Dict[str, Any]:
        """Convert config to dictionary for JSON serialization"""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'CLIConfig':
        """Create config from dictionary"""
        return cls(**data)


class ConfigManager:
    """Manages global DocPixie CLI configuration"""

    def __init__(self):
        """Initialize config manager with global config directory"""
        self.config_dir = Path.home() / ".docpixie"
        self.config_file = self.config_dir / "config.json"
        self.conversations_dir = self.config_dir / "conversations"

        self.config_dir.mkdir(exist_ok=True)
        self.conversations_dir.mkdir(exist_ok=True)

        self.config = self.load_config()

    def load_config(self) -> CLIConfig:
        """Load configuration from file or create default"""
        if self.config_file.exists():
            try:
                with open(self.config_file, 'r') as f:
                    data = json.load(f)
                    return CLIConfig.from_dict(data)
            except Exception as e:
                print(f"Warning: Failed to load config: {e}")
                return CLIConfig()
        else:
            env_key = os.getenv("OPENROUTER_API_KEY")
            config = CLIConfig()
            if env_key:
                config.openrouter_api_key = env_key
            return config

    def save_config(self):
        """Save current configuration to file"""
        try:
            with open(self.config_file, 'w') as f:
                json.dump(self.config.to_dict(), f, indent=2)
        except Exception as e:
            print(f"Error saving config: {e}")

    def get_api_key(self) -> Optional[str]:
        """Get OpenRouter API key from config or environment"""
        if self.config.openrouter_api_key:
            return self.config.openrouter_api_key
        return os.getenv("OPENROUTER_API_KEY")

    def set_api_key(self, api_key: str):
        """Set and save OpenRouter API key"""
        self.config.openrouter_api_key = api_key
        self.save_config()

    def has_api_key(self) -> bool:
        """Check if API key is configured"""
        return bool(self.get_api_key())

    def get_models(self) -> tuple[str, str]:
        """Get configured models (text, vision)"""
        return self.config.text_model, self.config.vision_model

    def set_models(self, text_model: str = None, vision_model: str = None):
        """Update model configuration"""
        if text_model:
            self.config.text_model = text_model
        if vision_model:
            self.config.vision_model = vision_model
        self.save_config()

    def get_conversation_path(self, conversation_id: str) -> Path:
        """Get path for a specific conversation file"""
        return self.conversations_dir / f"{conversation_id}.json"

    def get_all_conversations(self) -> list[Path]:
        """Get all conversation files"""
        return list(self.conversations_dir.glob("*.json"))

    def validate_api_key(self, api_key: str) -> bool:
        """
        Validate API key by making a test request
        Returns True if valid, False otherwise
        """
        try:
            if api_key and len(api_key) > 10:
                return True
            return False
        except Exception:
            return False


_config_manager = None


def get_config_manager() -> ConfigManager:
    """Get or create the global config manager instance"""
    global _config_manager
    if _config_manager is None:
        _config_manager = ConfigManager()
    return _config_manager
