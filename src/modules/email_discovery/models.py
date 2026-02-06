"""Data structures for email discovery and authentication workflows.

This module contains custom Pydantic models for managing email provider
configurations, authentication outcomes, and service endpoints.
"""

from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field, ConfigDict
from datetime import datetime


class IMAPConfig(BaseModel):
    """Configuration for IMAP server connection parameters.
    
    Args:
        host: IMAP server hostname
        port: IMAP server port number
        use_ssl: Enable SSL/TLS encryption
        use_tls: Enable STARTTLS upgrade
        timeout_seconds: Connection timeout
        
    Example:
        >>> config = IMAPConfig(
        ...     host="imap.example.com",
        ...     port=993,
        ...     use_ssl=True
        ... )
    """
    
    host: str = Field(..., description="IMAP server hostname")
    port: int = Field(..., ge=1, le=65535, description="IMAP port")
    use_ssl: bool = Field(default=True, description="SSL encryption flag")
    use_tls: bool = Field(default=False, description="STARTTLS flag")
    timeout_seconds: int = Field(default=30, ge=5, le=300, description="Connection timeout")
    
    model_config = ConfigDict(frozen=False, extra='forbid')


class LoginResult(BaseModel):
    """Outcome of email provider authentication attempt.
    
    Args:
        success: Whether authentication succeeded
        session_id: Unique session identifier if successful
        cookies: HTTP cookies from authentication
        error_message: Failure reason if unsuccessful
        provider: Email provider identifier
        timestamp: When authentication occurred
        metadata: Additional provider-specific data
        
    Example:
        >>> result = LoginResult(
        ...     success=True,
        ...     session_id="xyz123",
        ...     provider="wp.pl"
        ... )
    """
    
    success: bool = Field(..., description="Authentication success flag")
    session_id: Optional[str] = Field(default=None, description="Session identifier")
    cookies: Dict[str, str] = Field(default_factory=dict, description="Authentication cookies")
    error_message: Optional[str] = Field(default=None, description="Error details")
    provider: str = Field(..., description="Provider identifier")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Auth timestamp")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Extra data")
    
    model_config = ConfigDict(frozen=False)


class ProviderEndpoints(BaseModel):
    """Collection of service endpoints for an email provider.
    
    Args:
        login_url: Authentication endpoint
        logout_url: Session termination endpoint
        imap_host: IMAP server hostname
        imap_port: IMAP server port
        api_base: Base URL for API calls
        headers: Default HTTP headers
        
    Example:
        >>> endpoints = ProviderEndpoints(
        ...     login_url="https://login.provider.com/auth",
        ...     imap_host="imap.provider.com",
        ...     imap_port=993
        ... )
    """
    
    login_url: str = Field(..., description="Authentication URL")
    logout_url: Optional[str] = Field(default=None, description="Logout URL")
    imap_host: str = Field(..., description="IMAP hostname")
    imap_port: int = Field(..., ge=1, le=65535, description="IMAP port")
    api_base: Optional[str] = Field(default=None, description="API base URL")
    headers: Dict[str, str] = Field(default_factory=dict, description="Default headers")
    
    model_config = ConfigDict(frozen=False)


class EmailCredentials(BaseModel):
    """Email account credentials container.
    
    Args:
        email_address: Full email address
        password: Account password
        provider_hint: Optional provider identifier
        
    Example:
        >>> creds = EmailCredentials(
        ...     email_address="user@domain.com",
        ...     password="secret123"
        ... )
    """
    
    email_address: str = Field(..., min_length=5, description="Email address")
    password: str = Field(..., min_length=1, description="Account password")
    provider_hint: Optional[str] = Field(default=None, description="Provider identifier")
    
    model_config = ConfigDict(frozen=False)


class AuthenticationState(BaseModel):
    """Tracks authentication session state across requests.
    
    Args:
        session_id: Unique session identifier
        cookies_jar: Session cookies
        csrf_token: Cross-site request forgery token
        bearer_token: Bearer authentication token
        expires_at: Session expiration timestamp
        refresh_token: Token for session renewal
        
    Example:
        >>> state = AuthenticationState(
        ...     session_id="abc123",
        ...     cookies_jar={"session": "xyz"}
        ... )
    """
    
    session_id: str = Field(..., description="Session identifier")
    cookies_jar: Dict[str, str] = Field(default_factory=dict, description="Cookie storage")
    csrf_token: Optional[str] = Field(default=None, description="CSRF token")
    bearer_token: Optional[str] = Field(default=None, description="Bearer token")
    expires_at: Optional[datetime] = Field(default=None, description="Expiration time")
    refresh_token: Optional[str] = Field(default=None, description="Refresh token")
    provider_data: Dict[str, Any] = Field(default_factory=dict, description="Provider extras")
    
    model_config = ConfigDict(frozen=False)
