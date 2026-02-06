"""Pydantic models for credential validation.

This module defines data structures for validation results and status tracking.
"""

from datetime import datetime, timezone
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class ValidationStatus(str, Enum):
    """Credential validation status."""
    
    SUCCESS = "success"
    INVALID_CREDENTIALS = "invalid_credentials"
    NETWORK_ERROR = "network_error"
    PROVIDER_ERROR = "provider_error"
    TIMEOUT = "timeout"


class ValidationResult(BaseModel):
    """Result of credential validation attempt.
    
    Attributes:
        status: Validation status outcome.
        email: Email address that was validated.
        provider: Email provider identifier.
        session_data: Session cookies/tokens if successful.
        error_message: Error details if validation failed.
        attempts: Number of validation attempts made.
        validated_at: Timestamp of validation.
    """
    
    status: ValidationStatus = Field(..., description="Validation status")
    email: str = Field(..., description="Email address")
    provider: str = Field(..., description="Provider identifier")
    session_data: Optional[dict] = Field(default=None, description="Session data")
    error_message: Optional[str] = Field(default=None, description="Error details")
    attempts: int = Field(default=1, ge=1, description="Attempt count")
    validated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), description="Validation timestamp")
    
    class Config:
        """Pydantic model configuration."""
        from_attributes = True
