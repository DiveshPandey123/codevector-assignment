"""Application configuration."""
from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    database_url: str
    api_key: str
    log_level: str = "INFO"
    environment: str = "development"
    
    # Connection pool settings
    db_pool_min_size: int = 5
    db_pool_max_size: int = 20
    db_pool_timeout: int = 30
    
    # API settings
    api_title: str = "Product Browsing Backend"
    api_version: str = "1.0.0"
    api_description: str = "Fast, consistent product browsing with cursor pagination"
    
    # Pagination defaults
    default_page_size: int = 50
    max_page_size: int = 100
    min_page_size: int = 1
    
    # Rate limiting
    rate_limit_requests: int = 100
    rate_limit_window: int = 60  # seconds
    
    class Config:
        env_file = ".env"
        case_sensitive = False


settings = Settings()
