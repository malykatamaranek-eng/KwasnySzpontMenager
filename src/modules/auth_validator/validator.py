"""Credential validation with retry logic and database integration.

This module provides async credential validation with exponential backoff,
integration with email providers, and database status updates.
"""

import asyncio
from datetime import datetime
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from src.core.config import settings
from src.core.logging import get_logger
from src.core.exceptions import EmailProviderError
from src.db import crud
from src.db.models import EmailAccountStatus
from src.modules.auth_validator.models import ValidationResult, ValidationStatus
from src.modules.email_discovery.detector import EmailProviderDetector
from src.modules.email_discovery.models import EmailCredentials
from src.modules.proxy_manager.models import ProxyConfig

logger = get_logger(__name__)


class AuthValidator:
    """Validate email credentials with retry logic and database updates.
    
    Provides async credential validation with:
    - Exponential backoff retry (max 3 attempts)
    - Integration with email provider authentication
    - Session/cookie storage
    - Database status updates
    """
    
    # Retry configuration
    MAX_RETRIES = 3
    RETRY_DELAYS = [1, 2, 4]  # Seconds
    
    def __init__(self, db: AsyncSession) -> None:
        """Initialize auth validator.
        
        Args:
            db: Database session for status updates.
        """
        self.db = db
        self.detector = EmailProviderDetector()
        logger.debug("AuthValidator initialized")
    
    async def validate_credentials(
        self,
        email: str,
        password: str,
        proxy: Optional[ProxyConfig] = None
    ) -> ValidationResult:
        """Validate email credentials with retry logic.
        
        Args:
            email: Email address to validate.
            password: Email password.
            proxy: Optional proxy configuration.
        
        Returns:
            ValidationResult: Validation outcome with session data.
        """
        logger.info("Validating credentials", email=email)
        
        # Detect provider
        provider = self.detector.detect_provider(email)
        if not provider:
            logger.error("Unknown email provider", email=email)
            return ValidationResult(
                status=ValidationStatus.PROVIDER_ERROR,
                email=email,
                provider="unknown",
                error_message="Unknown email provider",
                attempts=1
            )
        
        logger.debug("Provider detected", email=email, provider=provider.provider_identifier)
        
        # Retry loop with exponential backoff
        for attempt in range(1, self.MAX_RETRIES + 1):
            try:
                logger.debug(
                    "Validation attempt",
                    email=email,
                    attempt=attempt,
                    max_retries=self.MAX_RETRIES
                )
                
                # Attempt authentication
                result = await self._attempt_validation(
                    email=email,
                    password=password,
                    provider_name=provider.provider_identifier,
                    provider=provider,
                    proxy=proxy
                )
                
                if result.status == ValidationStatus.SUCCESS:
                    logger.info(
                        "Validation successful",
                        email=email,
                        attempts=attempt
                    )
                    result.attempts = attempt
                    
                    # Update database
                    await self._update_database(email, result)
                    
                    return result
                
                # Non-retryable errors
                if result.status == ValidationStatus.INVALID_CREDENTIALS:
                    logger.warning("Invalid credentials", email=email)
                    result.attempts = attempt
                    await self._update_database(email, result)
                    return result
                
                # Retryable errors - wait before retry
                if attempt < self.MAX_RETRIES:
                    delay = self.RETRY_DELAYS[attempt - 1]
                    logger.info(
                        "Retrying validation",
                        email=email,
                        attempt=attempt,
                        delay=delay
                    )
                    await asyncio.sleep(delay)
                else:
                    # Max retries reached
                    logger.error(
                        "Max retries reached",
                        email=email,
                        attempts=attempt
                    )
                    result.attempts = attempt
                    await self._update_database(email, result)
                    return result
                    
            except Exception as e:
                logger.error(
                    "Validation exception",
                    email=email,
                    attempt=attempt,
                    error=str(e)
                )
                
                if attempt >= self.MAX_RETRIES:
                    result = ValidationResult(
                        status=ValidationStatus.NETWORK_ERROR,
                        email=email,
                        provider=provider.provider_identifier,
                        error_message=str(e),
                        attempts=attempt
                    )
                    await self._update_database(email, result)
                    return result
                
                # Wait before retry
                delay = self.RETRY_DELAYS[attempt - 1]
                await asyncio.sleep(delay)
        
        # Should not reach here, but return error as fallback
        result = ValidationResult(
            status=ValidationStatus.NETWORK_ERROR,
            email=email,
            provider=provider.provider_identifier,
            error_message="Max retries exceeded",
            attempts=self.MAX_RETRIES
        )
        await self._update_database(email, result)
        return result
    
    async def _attempt_validation(
        self,
        email: str,
        password: str,
        provider_name: str,
        provider: "BaseEmailProvider",
        proxy: Optional[ProxyConfig] = None
    ) -> ValidationResult:
        """Single validation attempt.
        
        Args:
            email: Email address.
            password: Email password.
            provider_name: Provider identifier.
            provider: Provider instance.
            proxy: Optional proxy configuration.
        
        Returns:
            ValidationResult: Validation outcome.
        """
        try:
            # Create credentials
            credentials = EmailCredentials(
                email_address=email,
                password=password
            )
            
            # Attempt authentication with timeout
            login_result = await asyncio.wait_for(
                provider.authenticate_user(credentials, proxy_cfg=proxy),
                timeout=settings.email_imap_timeout
            )
            
            if login_result.success:
                return ValidationResult(
                    status=ValidationStatus.SUCCESS,
                    email=email,
                    provider=provider_name,
                    session_data={
                        "session_id": login_result.session_id,
                        "cookies": login_result.cookies,
                        "metadata": login_result.metadata
                    }
                )
            else:
                # Determine error type from message
                error_lower = (login_result.error_message or "").lower()
                
                if any(term in error_lower for term in ["password", "credentials", "authentication", "login"]):
                    status = ValidationStatus.INVALID_CREDENTIALS
                elif any(term in error_lower for term in ["network", "connection", "timeout"]):
                    status = ValidationStatus.NETWORK_ERROR
                else:
                    status = ValidationStatus.PROVIDER_ERROR
                
                return ValidationResult(
                    status=status,
                    email=email,
                    provider=provider_name,
                    error_message=login_result.error_message
                )
                
        except asyncio.TimeoutError:
            logger.error("Validation timeout", email=email)
            return ValidationResult(
                status=ValidationStatus.TIMEOUT,
                email=email,
                provider=provider_name,
                error_message="Authentication timeout"
            )
        except EmailProviderError as e:
            logger.error("Provider error", email=email, error=str(e))
            return ValidationResult(
                status=ValidationStatus.PROVIDER_ERROR,
                email=email,
                provider=provider_name,
                error_message=str(e)
            )
        except Exception as e:
            logger.error("Unexpected error", email=email, error=str(e))
            return ValidationResult(
                status=ValidationStatus.NETWORK_ERROR,
                email=email,
                provider=provider_name,
                error_message=str(e)
            )
    
    async def _update_database(
        self,
        email: str,
        result: ValidationResult
    ) -> None:
        """Update email account status in database.
        
        Args:
            email: Email address.
            result: Validation result.
        """
        try:
            # Get email account
            account = await crud.get_email_account_by_email(self.db, email)
            
            if not account:
                logger.warning(
                    "Email account not found in database",
                    email=email
                )
                return
            
            # Map validation status to database status
            if result.status == ValidationStatus.SUCCESS:
                db_status = EmailAccountStatus.VALIDATED
            elif result.status == ValidationStatus.INVALID_CREDENTIALS:
                db_status = EmailAccountStatus.INVALID
            else:
                db_status = EmailAccountStatus.ERROR
            
            # Update account
            await crud.update_email_account_status(
                db=self.db,
                account_id=account.id,
                status=db_status,
                session_data=result.session_data
            )
            
            logger.info(
                "Email account status updated",
                email=email,
                status=db_status.value
            )
            
        except Exception as e:
            logger.error(
                "Failed to update database",
                email=email,
                error=str(e)
            )
