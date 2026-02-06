"""Security monitoring for Facebook accounts.

This module provides functionality for checking account security status,
detecting alerts, and storing them in the database.
"""

import asyncio
from datetime import datetime, timezone, timedelta
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from src.core.config import settings
from src.core.logging import get_logger
from src.db import crud
from src.db.models import FacebookAccount
from src.modules.monitoring.models import AlertType, MonitoringConfig, SecurityAlertData

logger = get_logger(__name__)


class SecurityMonitor:
    """Monitor Facebook accounts for security alerts.
    
    Provides functionality for:
    - Checking account security status
    - Detecting and storing alerts
    - Periodic monitoring of all accounts
    """
    
    def __init__(
        self,
        db: AsyncSession,
        config: Optional[MonitoringConfig] = None
    ) -> None:
        """Initialize security monitor.
        
        Args:
            db: Database session.
            config: Monitoring configuration (uses defaults if not provided).
        """
        self.db = db
        self.config = config or MonitoringConfig()
        logger.info(
            "SecurityMonitor initialized",
            check_interval=self.config.check_interval_minutes
        )
    
    async def check_account_security(self, account_id: int) -> list[SecurityAlertData]:
        """Check account for security alerts.
        
        Note: This is a placeholder implementation. Full implementation
        requires Playwright integration to log into Facebook and check
        the security section.
        
        Args:
            account_id: Facebook account ID to check.
        
        Returns:
            list[SecurityAlertData]: List of detected alerts.
        """
        logger.info("Checking account security", account_id=account_id)
        
        try:
            # Get account
            account = await crud.get_facebook_account(self.db, account_id)
            if not account:
                logger.error("Account not found", account_id=account_id)
                return []
            
            # Placeholder: In real implementation, this would:
            # 1. Launch Playwright browser with account cookies
            # 2. Navigate to Facebook security settings
            # 3. Parse security alerts section
            # 4. Extract alert details
            # 5. Return list of SecurityAlertData
            
            # For now, just log and return empty list
            logger.info(
                "Security check placeholder executed",
                account_id=account_id,
                fb_email=account.fb_email
            )
            
            alerts = []
            
            # Store alerts in database
            for alert_data in alerts:
                await self._store_alert(account_id, alert_data)
            
            # Update last checked timestamp
            await crud.update_facebook_account(
                db=self.db,
                account_id=account_id,
                security_alerts_checked=datetime.now(timezone.utc)
            )
            
            return alerts
            
        except Exception as e:
            logger.error(
                "Failed to check account security",
                account_id=account_id,
                error=str(e)
            )
            return []
    
    async def _store_alert(
        self,
        account_id: int,
        alert_data: SecurityAlertData
    ) -> None:
        """Store security alert in database.
        
        Args:
            account_id: Facebook account ID.
            alert_data: Alert data to store.
        """
        try:
            await crud.create_security_alert(
                db=self.db,
                account_id=account_id,
                alert_type=alert_data.alert_type.value,
                alert_data={
                    "location": alert_data.location,
                    "device": alert_data.device,
                    "timestamp": alert_data.timestamp.isoformat(),
                    "ip_address": alert_data.ip_address,
                    "details": alert_data.details
                }
            )
            
            logger.info(
                "Alert stored",
                account_id=account_id,
                alert_type=alert_data.alert_type.value
            )
            
        except Exception as e:
            logger.error(
                "Failed to store alert",
                account_id=account_id,
                error=str(e)
            )
    
    async def get_unhandled_alerts(
        self,
        account_id: Optional[int] = None
    ) -> list[dict]:
        """Get unhandled security alerts.
        
        Args:
            account_id: Optional account ID filter.
        
        Returns:
            list[dict]: List of unhandled alerts.
        """
        try:
            alerts = await crud.get_unhandled_security_alerts(
                db=self.db,
                account_id=account_id
            )
            
            logger.info(
                "Unhandled alerts retrieved",
                account_id=account_id,
                count=len(alerts)
            )
            
            return [
                {
                    "id": alert.id,
                    "account_id": alert.account_id,
                    "alert_type": alert.alert_type,
                    "alert_data": alert.alert_data,
                    "detected_at": alert.detected_at
                }
                for alert in alerts
            ]
            
        except Exception as e:
            logger.error(
                "Failed to get unhandled alerts",
                account_id=account_id,
                error=str(e)
            )
            return []
    
    async def check_all_accounts(self) -> dict[int, list[SecurityAlertData]]:
        """Check security for all active Facebook accounts.
        
        Returns:
            dict[int, list[SecurityAlertData]]: Map of account_id to alerts.
        """
        logger.info("Checking security for all accounts")
        
        try:
            # Get all logged-in accounts
            accounts = await crud.get_facebook_accounts_by_status(
                db=self.db,
                status="logged_in"
            )
            
            logger.info("Active accounts found", count=len(accounts))
            
            results = {}
            
            # Check each account
            for account in accounts:
                try:
                    alerts = await self.check_account_security(account.id)
                    results[account.id] = alerts
                except Exception as e:
                    logger.error(
                        "Failed to check account",
                        account_id=account.id,
                        error=str(e)
                    )
                    results[account.id] = []
            
            logger.info(
                "All accounts checked",
                total_accounts=len(accounts),
                accounts_with_alerts=sum(1 for alerts in results.values() if alerts)
            )
            
            return results
            
        except Exception as e:
            logger.error("Failed to check all accounts", error=str(e))
            return {}
    
    async def schedule_periodic_check(self) -> None:
        """Schedule periodic security checks for all accounts.
        
        Runs continuously with configured check interval.
        This should be run as a background task.
        """
        logger.info(
            "Starting periodic security checks",
            interval_minutes=self.config.check_interval_minutes
        )
        
        while True:
            try:
                logger.debug("Running periodic security check")
                
                # Check all accounts
                results = await self.check_all_accounts()
                
                # Log summary
                total_alerts = sum(len(alerts) for alerts in results.values())
                logger.info(
                    "Periodic check completed",
                    accounts_checked=len(results),
                    total_alerts=total_alerts
                )
                
                # Wait for next check
                await asyncio.sleep(self.config.check_interval_minutes * 60)
                
            except asyncio.CancelledError:
                logger.info("Periodic check cancelled")
                break
            except Exception as e:
                logger.error("Error in periodic check", error=str(e))
                # Wait before retrying
                await asyncio.sleep(60)
