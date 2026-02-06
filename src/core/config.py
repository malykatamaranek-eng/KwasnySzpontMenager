"""Application configuration using Pydantic Settings."""
from typing import Optional
from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    """Application settings."""
    
    # Database
    DATABASE_URL: str = Field(
        default="postgresql://admin:secret@localhost:5432/automation",
        description="PostgreSQL database URL"
    )
    
    # Redis
    REDIS_URL: str = Field(
        default="redis://localhost:6379/0",
        description="Redis connection URL"
    )
    
    # Security
    ENCRYPTION_KEY: str = Field(
        default="bXlzZWNyZXRrZXkxMjM0NTY3ODkwMTIzNDU2Nzg5MDEyMzQ1Njc4OTAxMjM0NTY3ODkwMTIzNDU2Nzg5MDEyMzQ1Njc4OTAxMjM0NTY3ODkw",
        description="AES-256-GCM encryption key (base64 encoded)"
    )
    JWT_SECRET: str = Field(
        default="mysecretjwtsecretkey1234567890",
        description="JWT secret key"
    )
    
    # Celery
    CELERY_BROKER_URL: str = Field(
        default="redis://localhost:6379/0",
        description="Celery broker URL"
    )
    CELERY_RESULT_BACKEND: str = Field(
        default="redis://localhost:6379/0",
        description="Celery result backend URL"
    )
    
    # Playwright
    PLAYWRIGHT_HEADLESS: bool = Field(
        default=True,
        description="Run Playwright in headless mode"
    )
    PLAYWRIGHT_TIMEOUT: int = Field(
        default=30000,
        description="Playwright timeout in milliseconds"
    )
    
    # Rate Limiting
    RATE_LIMIT_PER_MINUTE: int = Field(
        default=10,
        description="API rate limit per minute"
    )
    
    # Application
    APP_NAME: str = "Account Automation System"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False
    
    class Config:
        """Pydantic config."""
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


# Global settings instance
settings = Settings()
