"""Pydantic models for Facebook automation module.

This module defines data models for browser configuration, authentication results,
and security action outcomes.
"""

from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field


class BrowserConfig(BaseModel):
    """Configuration for browser automation.
    
    Attributes:
        headless: Whether to run browser in headless mode
        proxy: Proxy URL in format "http://user:pass@host:port"
        user_agent: Custom user agent string
        viewport_width: Browser viewport width in pixels
        viewport_height: Browser viewport height in pixels
    """
    
    headless: bool = Field(
        default=True,
        description="Run browser in headless mode"
    )
    proxy: Optional[str] = Field(
        default=None,
        description="Proxy URL (e.g., 'http://user:pass@host:port')"
    )
    user_agent: Optional[str] = Field(
        default=None,
        description="Custom user agent string"
    )
    viewport_width: int = Field(
        default=1920,
        ge=800,
        le=3840,
        description="Viewport width in pixels"
    )
    viewport_height: int = Field(
        default=1080,
        ge=600,
        le=2160,
        description="Viewport height in pixels"
    )


class ResetPasswordResult(BaseModel):
    """Result of password reset operation.
    
    Attributes:
        success: Whether password reset was successful
        new_password: The new password that was set (if successful)
        error_message: Error description if failed
        checkpoint_required: Whether Facebook checkpoint is blocking action
    """
    
    success: bool = Field(
        description="Whether password reset succeeded"
    )
    new_password: Optional[str] = Field(
        default=None,
        description="New password if reset was successful"
    )
    error_message: Optional[str] = Field(
        default=None,
        description="Error message if reset failed"
    )
    checkpoint_required: bool = Field(
        default=False,
        description="Facebook checkpoint is blocking action"
    )


class LoginResult(BaseModel):
    """Result of login attempt.
    
    Attributes:
        success: Whether login was successful
        session_data: Session information if successful
        cookies: Browser cookies from session
        two_fa_required: Whether 2FA is required but not completed
        checkpoint_required: Whether Facebook checkpoint is blocking login
        error_message: Error description if failed
    """
    
    success: bool = Field(
        description="Whether login succeeded"
    )
    session_data: Optional[dict[str, Any]] = Field(
        default=None,
        description="Session data if login successful"
    )
    cookies: Optional[list[dict[str, Any]]] = Field(
        default=None,
        description="Browser cookies from session"
    )
    two_fa_required: bool = Field(
        default=False,
        description="2FA verification is required"
    )
    checkpoint_required: bool = Field(
        default=False,
        description="Facebook checkpoint is blocking login"
    )
    error_message: Optional[str] = Field(
        default=None,
        description="Error message if login failed"
    )


class SecurityAction(str, Enum):
    """Available security actions.
    
    Actions that can be performed on a Facebook account for security.
    """
    
    LOGOUT_OTHER_SESSIONS = "logout_other_sessions"
    DISABLE_NOTIFICATIONS = "disable_notifications"
    UPDATE_PRIVACY = "update_privacy"


class SecurityActionResult(BaseModel):
    """Result of security action.
    
    Attributes:
        action: The security action that was performed
        success: Whether action was successful
        error_message: Error description if failed
    """
    
    action: SecurityAction = Field(
        description="Security action performed"
    )
    success: bool = Field(
        description="Whether action succeeded"
    )
    error_message: Optional[str] = Field(
        default=None,
        description="Error message if action failed"
    )
