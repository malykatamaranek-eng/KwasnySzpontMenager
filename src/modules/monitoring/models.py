"""Pydantic models for security monitoring and alerting.

This module defines data structures for security alerts, monitoring
configuration, and alert handling.
"""

from datetime import datetime, timezone
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class AlertType(str, Enum):
    """Type of security alert."""
    
    NEW_LOGIN = "new_login"
    SUSPICIOUS_ACTIVITY = "suspicious_activity"
    PASSWORD_CHANGED = "password_changed"
    CHECKPOINT = "checkpoint"
    OTHER = "other"


class SecurityAlertData(BaseModel):
    """Security alert details from Facebook.
    
    Attributes:
        alert_type: Type of security alert.
        location: Geographic location if available.
        device: Device information if available.
        timestamp: When alert occurred.
        ip_address: IP address if available.
        details: Additional alert-specific details.
    """
    
    alert_type: AlertType = Field(..., description="Alert type")
    location: Optional[str] = Field(default=None, description="Geographic location")
    device: Optional[str] = Field(default=None, description="Device info")
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), description="Alert timestamp")
    ip_address: Optional[str] = Field(default=None, description="IP address")
    details: dict = Field(default_factory=dict, description="Additional details")
    
    class Config:
        """Pydantic model configuration."""
        from_attributes = True


class MonitoringConfig(BaseModel):
    """Configuration for security monitoring.
    
    Attributes:
        check_interval_minutes: Minutes between security checks.
        alert_threshold: Number of alerts before triggering notification.
        webhook_url: Optional webhook URL for notifications.
    """
    
    check_interval_minutes: int = Field(
        default=60,
        ge=1,
        le=1440,
        description="Check interval in minutes"
    )
    alert_threshold: int = Field(
        default=1,
        ge=1,
        description="Alert threshold for notifications"
    )
    webhook_url: Optional[str] = Field(
        default=None,
        description="Webhook URL for notifications"
    )
    
    class Config:
        """Pydantic model configuration."""
        from_attributes = True
