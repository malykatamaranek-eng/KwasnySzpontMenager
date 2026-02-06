"""Alert handling and notification system.

This module provides functionality for handling security alerts,
sending notifications via webhooks and email, and logging.
"""

import json
from datetime import datetime
from typing import Optional

import aiohttp
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.config import settings
from src.core.logging import get_logger
from src.db import crud
from src.modules.monitoring.models import MonitoringConfig

logger = get_logger(__name__)


class AlertHandler:
    """Handle security alerts with notifications and logging.
    
    Provides functionality for:
    - Processing security alerts
    - Sending webhook notifications
    - Email notifications
    - Alert status updates
    """
    
    def __init__(
        self,
        db: AsyncSession,
        config: Optional[MonitoringConfig] = None
    ) -> None:
        """Initialize alert handler.
        
        Args:
            db: Database session.
            config: Monitoring configuration (uses defaults if not provided).
        """
        self.db = db
        self.config = config or MonitoringConfig()
        logger.info("AlertHandler initialized")
    
    async def handle_alert(self, alert_id: int) -> bool:
        """Handle security alert with notifications.
        
        Args:
            alert_id: Security alert ID to handle.
        
        Returns:
            bool: True if handled successfully, False otherwise.
        """
        logger.info("Handling alert", alert_id=alert_id)
        
        try:
            # Get alert
            alert = await crud.get_security_alert(self.db, alert_id)
            if not alert:
                logger.error("Alert not found", alert_id=alert_id)
                return False
            
            if alert.handled:
                logger.warning("Alert already handled", alert_id=alert_id)
                return True
            
            # Get account details
            account = await crud.get_facebook_account(self.db, alert.account_id)
            if not account:
                logger.error("Account not found", account_id=alert.account_id)
                return False
            
            # Prepare alert payload
            payload = {
                "alert_id": alert.id,
                "account_id": alert.account_id,
                "fb_email": account.fb_email,
                "alert_type": alert.alert_type,
                "alert_data": alert.alert_data,
                "detected_at": alert.detected_at.isoformat(),
                "timestamp": datetime.utcnow().isoformat()
            }
            
            # Send notifications
            webhook_sent = await self._send_webhook_notification(payload)
            email_sent = await self._send_email_notification(payload)
            
            # Log to file
            await self._log_to_file(payload)
            
            # Mark as handled
            await crud.mark_security_alert_handled(
                db=self.db,
                alert_id=alert_id
            )
            
            logger.info(
                "Alert handled",
                alert_id=alert_id,
                webhook_sent=webhook_sent,
                email_sent=email_sent
            )
            
            return True
            
        except Exception as e:
            logger.error(
                "Failed to handle alert",
                alert_id=alert_id,
                error=str(e)
            )
            return False
    
    async def _send_webhook_notification(self, payload: dict) -> bool:
        """Send alert notification via webhook.
        
        Args:
            payload: Alert data payload.
        
        Returns:
            bool: True if sent successfully, False otherwise.
        """
        if not self.config.webhook_url:
            logger.debug("No webhook URL configured, skipping")
            return False
        
        try:
            logger.info("Sending webhook notification", url=self.config.webhook_url)
            
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    self.config.webhook_url,
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as response:
                    if response.status in [200, 201, 202, 204]:
                        logger.info(
                            "Webhook sent successfully",
                            status=response.status
                        )
                        return True
                    else:
                        logger.error(
                            "Webhook failed",
                            status=response.status,
                            response=await response.text()
                        )
                        return False
                        
        except aiohttp.ClientError as e:
            logger.error("Webhook request failed", error=str(e))
            return False
        except Exception as e:
            logger.error("Unexpected webhook error", error=str(e))
            return False
    
    async def _send_email_notification(self, payload: dict) -> bool:
        """Send alert notification via email.
        
        Note: This is a placeholder implementation. Full implementation
        requires email sending service (SMTP, SendGrid, etc.).
        
        Args:
            payload: Alert data payload.
        
        Returns:
            bool: True if sent successfully, False otherwise.
        """
        logger.debug("Email notification placeholder", payload=payload)
        
        # Placeholder: In real implementation, this would:
        # 1. Format email with alert details
        # 2. Connect to SMTP server or email API
        # 3. Send email to configured recipients
        # 4. Return success/failure
        
        return False
    
    async def _log_to_file(self, payload: dict) -> None:
        """Log alert to file.
        
        Args:
            payload: Alert data payload.
        """
        try:
            log_entry = {
                "timestamp": datetime.utcnow().isoformat(),
                "event": "security_alert",
                "data": payload
            }
            
            # Use structured logging
            logger.warning(
                "Security Alert",
                alert_id=payload.get("alert_id"),
                account_id=payload.get("account_id"),
                alert_type=payload.get("alert_type"),
                fb_email=payload.get("fb_email"),
                detected_at=payload.get("detected_at")
            )
            
            # If log file configured, append to it
            if settings.log_file:
                try:
                    import aiofiles
                    async with aiofiles.open(
                        settings.log_file,
                        mode="a",
                        encoding="utf-8"
                    ) as f:
                        await f.write(json.dumps(log_entry) + "\n")
                except ImportError:
                    logger.debug("aiofiles not available, using sync file write")
                    with open(settings.log_file, "a", encoding="utf-8") as f:
                        f.write(json.dumps(log_entry) + "\n")
                        
        except Exception as e:
            logger.error("Failed to log to file", error=str(e))
    
    async def handle_all_unhandled_alerts(self) -> dict[str, int]:
        """Handle all unhandled security alerts.
        
        Returns:
            dict[str, int]: Summary with counts of processed alerts.
        """
        logger.info("Handling all unhandled alerts")
        
        try:
            # Get all unhandled alerts
            alerts = await crud.get_unhandled_security_alerts(self.db)
            
            logger.info("Unhandled alerts found", count=len(alerts))
            
            success_count = 0
            failure_count = 0
            
            # Handle each alert
            for alert in alerts:
                try:
                    success = await self.handle_alert(alert.id)
                    if success:
                        success_count += 1
                    else:
                        failure_count += 1
                except Exception as e:
                    logger.error(
                        "Error handling alert",
                        alert_id=alert.id,
                        error=str(e)
                    )
                    failure_count += 1
            
            summary = {
                "total": len(alerts),
                "success": success_count,
                "failure": failure_count
            }
            
            logger.info(
                "All alerts processed",
                total=summary["total"],
                success=summary["success"],
                failure=summary["failure"]
            )
            
            return summary
            
        except Exception as e:
            logger.error("Failed to handle all alerts", error=str(e))
            return {"total": 0, "success": 0, "failure": 0}
    
    async def notify_threshold_exceeded(
        self,
        account_id: int,
        alert_count: int
    ) -> None:
        """Send notification when alert threshold is exceeded.
        
        Args:
            account_id: Facebook account ID.
            alert_count: Number of alerts detected.
        """
        if alert_count < self.config.alert_threshold:
            return
        
        logger.warning(
            "Alert threshold exceeded",
            account_id=account_id,
            alert_count=alert_count,
            threshold=self.config.alert_threshold
        )
        
        try:
            account = await crud.get_facebook_account(self.db, account_id)
            if not account:
                return
            
            payload = {
                "event": "threshold_exceeded",
                "account_id": account_id,
                "fb_email": account.fb_email,
                "alert_count": alert_count,
                "threshold": self.config.alert_threshold,
                "timestamp": datetime.utcnow().isoformat()
            }
            
            # Send webhook notification
            await self._send_webhook_notification(payload)
            
            # Log
            await self._log_to_file(payload)
            
        except Exception as e:
            logger.error(
                "Failed to send threshold notification",
                account_id=account_id,
                error=str(e)
            )
