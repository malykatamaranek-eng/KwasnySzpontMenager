"""Configuration management for the Facebook automation system.

This module provides centralized configuration using Pydantic Settings,
loading values from environment variables with sensible defaults.
"""

from typing import Optional
from pydantic import Field, PostgresDsn, RedisDsn, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables.
    
    All settings can be overridden via environment variables.
    Sensitive values should always be provided via environment.
    """
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )
    
    # Application
    app_name: str = Field(default="Facebook Automation System", alias="APP_NAME")
    debug: bool = Field(default=False, alias="DEBUG")
    environment: str = Field(default="production", alias="ENVIRONMENT")
    
    # Database - PostgreSQL
    database_url: PostgresDsn = Field(
        default="postgresql+asyncpg://user:pass@localhost:5432/facebook_automation",
        alias="DATABASE_URL",
        description="Database URL - must be overridden in production"
    )
    database_pool_size: int = Field(default=20, alias="DATABASE_POOL_SIZE")
    database_max_overflow: int = Field(default=10, alias="DATABASE_MAX_OVERFLOW")
    database_pool_timeout: int = Field(default=30, alias="DATABASE_POOL_TIMEOUT")
    database_echo: bool = Field(default=False, alias="DATABASE_ECHO")
    
    # Redis
    redis_url: RedisDsn = Field(
        default="redis://localhost:6379/0",
        alias="REDIS_URL"
    )
    redis_max_connections: int = Field(default=50, alias="REDIS_MAX_CONNECTIONS")
    redis_socket_timeout: int = Field(default=5, alias="REDIS_SOCKET_TIMEOUT")
    redis_socket_connect_timeout: int = Field(default=5, alias="REDIS_SOCKET_CONNECT_TIMEOUT")
    
    # Security
    secret_key: str = Field(
        default="changeme-insecure-secret-key-for-development-only",
        alias="SECRET_KEY"
    )
    encryption_key: str = Field(
        default="changeme-insecure-encryption-key-for-development-only",
        alias="ENCRYPTION_KEY"
    )
    jwt_secret_key: str = Field(
        default="changeme-insecure-jwt-secret-key-for-development-only",
        alias="JWT_SECRET_KEY"
    )
    jwt_algorithm: str = Field(default="HS256", alias="JWT_ALGORITHM")
    jwt_access_token_expire_minutes: int = Field(default=30, alias="JWT_ACCESS_TOKEN_EXPIRE_MINUTES")
    jwt_refresh_token_expire_days: int = Field(default=7, alias="JWT_REFRESH_TOKEN_EXPIRE_DAYS")
    
    # Celery
    celery_broker_url: str = Field(
        default="redis://localhost:6379/1",
        alias="CELERY_BROKER_URL"
    )
    celery_result_backend: str = Field(
        default="redis://localhost:6379/2",
        alias="CELERY_RESULT_BACKEND"
    )
    celery_task_time_limit: int = Field(default=3600, alias="CELERY_TASK_TIME_LIMIT")
    celery_task_soft_time_limit: int = Field(default=3000, alias="CELERY_TASK_SOFT_TIME_LIMIT")
    celery_worker_prefetch_multiplier: int = Field(default=4, alias="CELERY_WORKER_PREFETCH_MULTIPLIER")
    celery_worker_max_tasks_per_child: int = Field(default=1000, alias="CELERY_WORKER_MAX_TASKS_PER_CHILD")
    
    # Logging
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")
    log_format: str = Field(default="json", alias="LOG_FORMAT")
    log_file: Optional[str] = Field(default=None, alias="LOG_FILE")
    
    # Proxy Settings
    proxy_max_concurrent_tasks: int = Field(default=10, alias="PROXY_MAX_CONCURRENT_TASKS")
    proxy_connection_timeout: int = Field(default=30, alias="PROXY_CONNECTION_TIMEOUT")
    proxy_request_timeout: int = Field(default=60, alias="PROXY_REQUEST_TIMEOUT")
    proxy_health_check_interval: int = Field(default=300, alias="PROXY_HEALTH_CHECK_INTERVAL")
    proxy_max_retries: int = Field(default=3, alias="PROXY_MAX_RETRIES")
    
    # Email Settings
    email_imap_timeout: int = Field(default=30, alias="EMAIL_IMAP_TIMEOUT")
    email_check_interval: int = Field(default=10, alias="EMAIL_CHECK_INTERVAL")
    email_max_wait_time: int = Field(default=300, alias="EMAIL_MAX_WAIT_TIME")
    email_code_pattern: str = Field(
        default=r"\b\d{6}\b",
        alias="EMAIL_CODE_PATTERN"
    )
    email_max_retries: int = Field(default=3, alias="EMAIL_MAX_RETRIES")
    
    # Facebook Settings
    facebook_base_url: str = Field(default="https://www.facebook.com", alias="FACEBOOK_BASE_URL")
    facebook_mobile_url: str = Field(default="https://m.facebook.com", alias="FACEBOOK_MOBILE_URL")
    facebook_login_timeout: int = Field(default=60, alias="FACEBOOK_LOGIN_TIMEOUT")
    facebook_page_load_timeout: int = Field(default=30, alias="FACEBOOK_PAGE_LOAD_TIMEOUT")
    facebook_action_timeout: int = Field(default=10, alias="FACEBOOK_ACTION_TIMEOUT")
    facebook_max_login_retries: int = Field(default=3, alias="FACEBOOK_MAX_LOGIN_RETRIES")
    facebook_session_lifetime_hours: int = Field(default=24, alias="FACEBOOK_SESSION_LIFETIME_HOURS")
    
    # Browser Settings
    browser_headless: bool = Field(default=True, alias="BROWSER_HEADLESS")
    browser_viewport_width: int = Field(default=1920, alias="BROWSER_VIEWPORT_WIDTH")
    browser_viewport_height: int = Field(default=1080, alias="BROWSER_VIEWPORT_HEIGHT")
    browser_user_agent: Optional[str] = Field(default=None, alias="BROWSER_USER_AGENT")
    
    # API Settings
    api_host: str = Field(default="0.0.0.0", alias="API_HOST")
    api_port: int = Field(default=8000, alias="API_PORT")
    api_workers: int = Field(default=4, alias="API_WORKERS")
    api_reload: bool = Field(default=False, alias="API_RELOAD")
    api_cors_origins: list[str] = Field(
        default=["http://localhost:3000", "http://localhost:8000"],
        alias="API_CORS_ORIGINS"
    )
    
    # Rate Limiting
    rate_limit_per_minute: int = Field(default=60, alias="RATE_LIMIT_PER_MINUTE")
    rate_limit_per_hour: int = Field(default=1000, alias="RATE_LIMIT_PER_HOUR")
    
    @field_validator("log_level")
    @classmethod
    def validate_log_level(cls, v: str) -> str:
        """Validate log level is a valid option."""
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        v_upper = v.upper()
        if v_upper not in valid_levels:
            raise ValueError(f"Log level must be one of {valid_levels}")
        return v_upper
    
    @field_validator("environment")
    @classmethod
    def validate_environment(cls, v: str) -> str:
        """Validate environment is a valid option."""
        valid_envs = ["development", "staging", "production"]
        v_lower = v.lower()
        if v_lower not in valid_envs:
            raise ValueError(f"Environment must be one of {valid_envs}")
        return v_lower
    
    def get_database_url_sync(self) -> str:
        """Get synchronous database URL for Alembic.
        
        Returns:
            str: PostgreSQL connection string with psycopg2 driver.
        """
        return str(self.database_url).replace(
            "postgresql+asyncpg://",
            "postgresql+psycopg2://"
        )
    
    def is_production(self) -> bool:
        """Check if running in production environment.
        
        Returns:
            bool: True if environment is production.
        """
        return self.environment == "production"
    
    def is_development(self) -> bool:
        """Check if running in development environment.
        
        Returns:
            bool: True if environment is development.
        """
        return self.environment == "development"
    
    def validate_production_config(self) -> list[str]:
        """Validate configuration for production use.
        
        Checks for insecure default values that should be overridden
        in production environments.
        
        Returns:
            list[str]: List of configuration warnings/errors.
        """
        warnings = []
        
        if self.is_production():
            # Check for default secrets
            if "changeme" in self.secret_key.lower():
                warnings.append("SECRET_KEY is using default value - must be changed in production")
            if "changeme" in self.encryption_key.lower():
                warnings.append("ENCRYPTION_KEY is using default value - must be changed in production")
            if "changeme" in self.jwt_secret_key.lower():
                warnings.append("JWT_SECRET_KEY is using default value - must be changed in production")
            
            # Check for default database credentials
            db_str = str(self.database_url)
            if "user:pass" in db_str or "postgres:postgres" in db_str:
                warnings.append("DATABASE_URL is using default credentials - must be changed in production")
        
        return warnings


# Global settings instance
settings = Settings()
