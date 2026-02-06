"""Monitoring module for security alerts and account monitoring.

This module provides functionality for:
- Security monitoring of Facebook accounts
- Alert detection and storage
- Alert handling and notifications
"""

from src.modules.monitoring.alert_handler import AlertHandler
from src.modules.monitoring.models import AlertType, MonitoringConfig, SecurityAlertData
from src.modules.monitoring.security_monitor import SecurityMonitor

__all__ = [
    "SecurityMonitor",
    "AlertHandler",
    "SecurityAlertData",
    "AlertType",
    "MonitoringConfig",
]
