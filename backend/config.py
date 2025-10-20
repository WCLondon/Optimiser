"""
Configuration management for BNG Optimiser backend.
"""

import os
from typing import Optional
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    # API Settings
    app_name: str = "BNG Optimiser API"
    app_version: str = "1.0.0"
    debug: bool = False
    
    # Server
    host: str = "0.0.0.0"
    port: int = 8080
    
    # Attio API
    attio_api_key: str = ""
    attio_api_url: str = "https://api.attio.com/v2"
    
    # Database
    database_url: Optional[str] = None
    
    # Redis (for job queue in production)
    redis_url: Optional[str] = None
    
    # CORS
    cors_origins: list[str] = ["*"]
    
    # Job Settings
    job_timeout_seconds: int = 300  # 5 minutes
    job_cleanup_after_hours: int = 24
    
    # Backend Data
    backend_data_path: str = "./data"
    cache_backend_data: bool = True
    
    class Config:
        env_file = ".env"
        case_sensitive = False


# Global settings instance
settings = Settings()


def get_settings() -> Settings:
    """Get application settings."""
    return settings
