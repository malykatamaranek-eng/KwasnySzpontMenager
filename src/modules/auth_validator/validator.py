"""Account validator for verifying credentials."""
import asyncio
from typing import Dict, Any, Optional
from datetime import datetime, timedelta
import structlog
from sqlalchemy.ext.asyncio import AsyncSession
from src.modules.email_discovery.detector import LiveEmailDiscovery
from src.db.models import Account, AccountStatus
from src.db import crud
from src.core.exceptions import ValidationError, EmailLoginFailedError

logger = structlog.get_logger()


class AccountValidator:
    """
    Account credential validator with:
    - Success/Error status codes
    - Session/cookie persistence
    - Rate limiting per provider
    - Exponential backoff retry
    """
    
    def __init__(self, db: AsyncSession):
        """
        Initialize account validator.
        
        Args:
            db: Database session
        """
        self.db = db
        self._rate_limits: Dict[str, datetime] = {}
        self._retry_delays = [1, 2, 4, 8, 16]
    
    async def check_rate_limit(self, provider: str, limit_seconds: int = 5) -> bool:
        """
        Check if rate limit allows validation.
        
        Args:
            provider: Provider name
            limit_seconds: Minimum seconds between validations
            
        Returns:
            True if validation allowed
        """
        now = datetime.utcnow()
        last_check = self._rate_limits.get(provider)
        
        if last_check and (now - last_check).total_seconds() < limit_seconds:
            remaining = limit_seconds - (now - last_check).total_seconds()
            logger.warning("rate_limit_hit", provider=provider, remaining_seconds=remaining)
            return False
        
        self._rate_limits[provider] = now
        return True
    
    async def validate_account(
        self, 
        account: Account, 
        proxy_url: Optional[str] = None,
        max_retries: int = 3
    ) -> Dict[str, Any]:
        """
        Validate account credentials with retries.
        
        Args:
            account: Account to validate
            proxy_url: Optional proxy URL
            max_retries: Maximum retry attempts
            
        Returns:
            Dict with validation result
        """
        from src.core.security import decrypt_password
        
        logger.info("account_validation_start", account_id=account.id, email=account.email)
        
        # Update status to validating
        await crud.update_account_status(self.db, account.id, AccountStatus.VALIDATING)
        await crud.create_log(self.db, account.id, "validate", "started", "Starting validation")
        
        # Check rate limit
        if not await self.check_rate_limit(account.provider):
            await asyncio.sleep(5)
        
        password = decrypt_password(account.encrypted_password)
        
        for attempt in range(max_retries):
            try:
                async with LiveEmailDiscovery() as discovery:
                    # Try login
                    result = await discovery.login_to_provider(
                        account.email,
                        password,
                        proxy_url
                    )
                    
                    # Verify IMAP works too
                    imap_result = await discovery.verify_imap_credentials(
                        account.email,
                        password
                    )
                    
                    if result["success"] and imap_result["success"]:
                        # Save session
                        await crud.create_session(
                            self.db,
                            account.id,
                            cookies=result["cookies"],
                            expires_at=datetime.utcnow() + timedelta(hours=24)
                        )
                        
                        # Update status
                        await crud.update_account_status(self.db, account.id, AccountStatus.VALID)
                        await crud.create_log(self.db, account.id, "validate", "success", "Account validated successfully")
                        
                        logger.info("account_validation_success", account_id=account.id)
                        
                        return {
                            "success": True,
                            "account_id": account.id,
                            "email": account.email,
                            "provider": account.provider,
                            "status": "VALID",
                            "imap_config": result["imap_config"]
                        }
                    else:
                        raise ValidationError("Login succeeded but IMAP verification failed")
                        
            except Exception as e:
                logger.error(
                    "account_validation_attempt_failed",
                    account_id=account.id,
                    attempt=attempt + 1,
                    error=str(e)
                )
                
                if attempt < max_retries - 1:
                    delay = self._retry_delays[min(attempt, len(self._retry_delays) - 1)]
                    await asyncio.sleep(delay)
                else:
                    # Final failure
                    await crud.update_account_status(self.db, account.id, AccountStatus.INVALID)
                    await crud.create_log(
                        self.db,
                        account.id,
                        "validate",
                        "failed",
                        f"Validation failed: {str(e)}"
                    )
                    
                    return {
                        "success": False,
                        "account_id": account.id,
                        "email": account.email,
                        "status": "INVALID",
                        "error": str(e)
                    }
        
        return {
            "success": False,
            "account_id": account.id,
            "email": account.email,
            "status": "INVALID",
            "error": "Max retries exceeded"
        }
    
    async def batch_validate(self, account_ids: list[int]) -> list[Dict[str, Any]]:
        """
        Validate multiple accounts.
        
        Args:
            account_ids: List of account IDs
            
        Returns:
            List of validation results
        """
        results = []
        
        for account_id in account_ids:
            account = await crud.get_account(self.db, account_id)
            if not account:
                logger.warning("account_not_found", account_id=account_id)
                continue
            
            result = await self.validate_account(account)
            results.append(result)
        
        return results
