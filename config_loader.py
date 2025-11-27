"""
Configuration Loader

Loads and validates configuration from config.json
"""

import json
import os
from pathlib import Path
from typing import Dict, Any


class Config:
    """Configuration manager"""

    def __init__(self, config_path: str = "config.json"):
        """Load configuration from file"""
        self.config_path = config_path
        self._config = self._load_config()

    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from JSON file"""
        if not os.path.exists(self.config_path):
            raise FileNotFoundError(f"Configuration file not found: {self.config_path}")

        with open(self.config_path, 'r', encoding='utf-8') as f:
            return json.load(f)

    def get(self, key_path: str, default=None):
        """
        Get configuration value using dot notation

        Args:
            key_path: Path to config key (e.g., 'api.model')
            default: Default value if key not found

        Returns:
            Configuration value
        """
        keys = key_path.split('.')
        value = self._config

        for key in keys:
            if isinstance(value, dict) and key in value:
                value = value[key]
            else:
                return default

        return value

    def get_all(self) -> Dict[str, Any]:
        """Get entire configuration"""
        return self._config.copy()

    # Convenience properties
    @property
    def api_model(self) -> str:
        return self.get('api.model', 'gemini-2.5-flash')

    @property
    def api_temperature(self) -> float:
        return self.get('api.temperature', 0.7)

    @property
    def api_max_tokens(self) -> int:
        return self.get('api.max_output_tokens', 64000)

    @property
    def api_max_retries(self) -> int:
        return self.get('api.max_retries', 3)

    @property
    def api_retry_delay(self) -> int:
        return self.get('api.retry_delay', 2)

    @property
    def max_refinement_iterations(self) -> int:
        return self.get('workflow.max_refinement_iterations', 2)

    @property
    def source_dir(self) -> str:
        return self.get('workflow.source_dir', 'source')

    @property
    def output_dir(self) -> str:
        return self.get('workflow.output_dir', 'output')

    @property
    def process_all_topics(self) -> bool:
        return self.get('workflow.process_all_topics', False)

    @property
    def generate_all_channels(self) -> bool:
        return self.get('workflow.generate_all_channels', False)

    @property
    def enabled_channels(self) -> list:
        return self.get('channels.enabled', ['linkedin', 'newsletter', 'blog'])

    @property
    def default_channel(self) -> str:
        return self.get('channels.default', 'linkedin')

    @property
    def log_level(self) -> str:
        return self.get('logging.level', 'INFO')

    @property
    def log_format(self) -> str:
        return self.get('logging.format', '%(asctime)s - %(name)s - %(levelname)s - %(message)s')

    @property
    def log_file(self) -> str:
        return self.get('logging.file', 'logs/workflow.log')

    @property
    def log_console(self) -> bool:
        return self.get('logging.console', True)


# Global config instance
_config_instance = None


def load_config(config_path: str = "config.json") -> Config:
    """Load configuration (singleton pattern)"""
    global _config_instance
    if _config_instance is None:
        _config_instance = Config(config_path)
    return _config_instance


def get_config() -> Config:
    """Get current configuration instance"""
    global _config_instance
    if _config_instance is None:
        _config_instance = Config()
    return _config_instance
