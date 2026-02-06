"""Pydantic models for email processing and code extraction.

This module defines data structures for email messages, verification code
extraction, and email search criteria.
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field, field_validator


class EmailMessage(BaseModel):
    """Represents a parsed email message.
    
    Attributes:
        id: Unique message identifier from email server.
        from_addr: Sender email address.
        to_addr: Recipient email address.
        subject: Email subject line.
        body_text: Plain text email body.
        body_html: HTML email body (optional).
        date: Email sent/received timestamp.
        headers: Raw email headers as dict.
    """
    
    id: str = Field(..., description="Message ID from email server")
    from_addr: str = Field(..., description="Sender email address")
    to_addr: str = Field(..., description="Recipient email address")
    subject: str = Field(..., description="Email subject")
    body_text: str = Field(default="", description="Plain text body")
    body_html: Optional[str] = Field(default=None, description="HTML body")
    date: datetime = Field(..., description="Email timestamp")
    headers: dict[str, str] = Field(default_factory=dict, description="Email headers")
    
    class Config:
        """Pydantic model configuration."""
        from_attributes = True


class CodeMatch(BaseModel):
    """Represents a verification code found in an email.
    
    Attributes:
        code: The extracted verification code.
        confidence: Confidence score (0.0-1.0) based on pattern match.
        location: Where code was found (subject/body).
        pattern_used: Regex pattern that matched the code.
    """
    
    code: str = Field(..., description="Extracted verification code")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Match confidence")
    location: str = Field(..., description="Code location (subject/body)")
    pattern_used: str = Field(..., description="Regex pattern used")
    
    @field_validator("location")
    @classmethod
    def validate_location(cls, v: str) -> str:
        """Validate location is valid option.
        
        Args:
            v: Location string to validate.
        
        Returns:
            str: Validated location.
        
        Raises:
            ValueError: If location is invalid.
        """
        valid_locations = {"subject", "body"}
        if v not in valid_locations:
            raise ValueError(f"Location must be one of {valid_locations}")
        return v
    
    class Config:
        """Pydantic model configuration."""
        from_attributes = True


class SearchCriteria(BaseModel):
    """Email search criteria for filtering messages.
    
    Attributes:
        from_address: Filter by sender email address.
        since_date: Filter messages since this date.
        subject_contains: Filter by subject substring.
        unread_only: Only fetch unread messages.
    """
    
    from_address: Optional[str] = Field(default=None, description="Sender filter")
    since_date: Optional[datetime] = Field(default=None, description="Date filter")
    subject_contains: Optional[str] = Field(default=None, description="Subject filter")
    unread_only: bool = Field(default=False, description="Unread only flag")
    
    class Config:
        """Pydantic model configuration."""
        from_attributes = True
