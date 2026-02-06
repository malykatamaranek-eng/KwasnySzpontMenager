"""Main Proxy Manager class for the Proxy Manager module.

This module provides the ProxyManager class for managing proxy servers,
including adding, testing, rotating, and maintaining proxy health.
"""

import asyncio
from datetime import datetime, timezone
from typing import Optional, Sequence

from sqlalchemy.ext.asyncio import AsyncSession

from src.core.config import settings
from src.core.exceptions import InvalidProxyFormat, ProxyException, RecordNotFoundError
from src.core.logging import get_logger
from src.core.security import encryption_manager
from src.db import crud
from src.db.models import Proxy
from src.modules.proxy_manager.models import ProxyConfig, ProxyStats, ProxyTestResult
from src.modules.proxy_manager.tester import test_multiple_proxies, test_proxy

logger = get_logger(__name__)


class ProxyManager:
    """Manager for proxy servers with rotation, testing, and health monitoring.
    
    Provides comprehensive proxy management including:
    - Adding and removing proxies with credential encryption
    - Round-robin proxy rotation for load distribution
    - Automated health checking and monitoring
    - Connection pooling and performance tracking
    - Automatic exclusion of unhealthy proxies
    
    Attributes:
        _db: Database session for persistence.
        _rotation_index: Current index in rotation sequence.
        _max_failure_threshold: Max failures before auto-disabling proxy.
        _test_timeout: Timeout for proxy health checks.
    """
    
    def __init__(
        self,
        db: AsyncSession,
        max_failure_threshold: int = 5,
        test_timeout: int = 10,
    ) -> None:
        """Initialize proxy manager.
        
        Args:
            db: Database session for proxy persistence.
            max_failure_threshold: Maximum consecutive failures before
                auto-disabling a proxy (default: 5).
            test_timeout: Timeout for proxy tests in seconds (default: 10).
        """
        self._db = db
        self._rotation_index = 0
        self._max_failure_threshold = max_failure_threshold
        self._test_timeout = test_timeout
        logger.info(
            "ProxyManager initialized",
            max_failure_threshold=max_failure_threshold,
            test_timeout=test_timeout,
        )
    
    async def add_proxy(self, proxy_str: str) -> ProxyConfig:
        """Parse and add a new proxy from string format.
        
        Parses proxy string in format HOST:PORT:USER:PASSWORD or HOST:PORT
        and adds it to the database with encrypted credentials.
        
        Args:
            proxy_str: Proxy string in format HOST:PORT[:USER:PASSWORD].
        
        Returns:
            ProxyConfig: Configuration of the added proxy.
        
        Raises:
            InvalidProxyFormat: If proxy string format is invalid.
            ProxyException: If proxy creation fails.
        """
        try:
            # Parse proxy string
            parts = proxy_str.strip().split(":")
            
            if len(parts) < 2:
                raise InvalidProxyFormat(
                    proxy_str,
                    "Minimum format is HOST:PORT",
                )
            
            host = parts[0].strip()
            try:
                port = int(parts[1].strip())
            except ValueError:
                raise InvalidProxyFormat(
                    proxy_str,
                    "Port must be a valid integer",
                )
            
            username = None
            password_encrypted = None
            
            # Parse optional credentials
            if len(parts) >= 4:
                username = parts[2].strip() if parts[2].strip() else None
                password = parts[3].strip() if parts[3].strip() else None
                
                if password:
                    # Encrypt password before storage
                    password_encrypted = encryption_manager.encrypt(password)
            elif len(parts) == 3:
                raise InvalidProxyFormat(
                    proxy_str,
                    "If username provided, password is also required",
                )
            
            # Validate host
            if not host:
                raise InvalidProxyFormat(proxy_str, "Host cannot be empty")
            
            # Validate port range
            if port < 1 or port > 65535:
                raise InvalidProxyFormat(
                    proxy_str,
                    "Port must be between 1 and 65535",
                )
            
            # Check if proxy already exists
            existing = await crud.get_proxy_by_host_port(self._db, host, port)
            if existing:
                logger.warning(
                    "Proxy already exists",
                    host=host,
                    port=port,
                    proxy_id=existing.id,
                )
                return self._proxy_to_config(existing)
            
            # Create proxy in database
            proxy = await crud.create_proxy(
                db=self._db,
                host=host,
                port=port,
                username=username,
                password_encrypted=password_encrypted,
                protocol="socks5",
                is_active=True,
            )
            
            logger.info(
                "Proxy added successfully",
                proxy_id=proxy.id,
                host=host,
                port=port,
                has_auth=bool(username),
            )
            
            return self._proxy_to_config(proxy)
        
        except InvalidProxyFormat:
            raise
        except Exception as e:
            logger.error("Failed to add proxy", proxy_str=proxy_str, error=str(e))
            raise ProxyException(
                message=f"Failed to add proxy: {str(e)}",
                details={"proxy_str": proxy_str},
            )
    
    async def get_next_proxy(self) -> Optional[ProxyConfig]:
        """Get next available proxy using round-robin rotation.
        
        Returns active proxies in rotation, automatically skipping
        unhealthy or disabled proxies.
        
        Returns:
            Optional[ProxyConfig]: Next proxy configuration, or None if
                no active proxies available.
        """
        try:
            # Get all active proxies sorted by performance
            proxies = await crud.get_active_proxies(self._db, limit=100)
            
            if not proxies:
                logger.warning("No active proxies available")
                return None
            
            # Use round-robin rotation
            proxy = proxies[self._rotation_index % len(proxies)]
            self._rotation_index = (self._rotation_index + 1) % len(proxies)
            
            logger.debug(
                "Proxy selected for rotation",
                proxy_id=proxy.id,
                host=proxy.host,
                rotation_index=self._rotation_index,
            )
            
            return self._proxy_to_config(proxy)
        
        except Exception as e:
            logger.error("Failed to get next proxy", error=str(e))
            return None
    
    async def test_proxy(self, proxy_id: int) -> ProxyTestResult:
        """Test specific proxy connectivity and latency.
        
        Args:
            proxy_id: ID of the proxy to test.
        
        Returns:
            ProxyTestResult: Test result with success status and latency.
        
        Raises:
            RecordNotFoundError: If proxy not found.
            ProxyException: If test fails unexpectedly.
        """
        try:
            # Get proxy from database
            proxy = await crud.get_proxy(self._db, proxy_id)
            if not proxy:
                raise RecordNotFoundError("Proxy", proxy_id)
            
            # Convert to config for testing
            config = self._proxy_to_config(proxy)
            
            logger.debug("Testing proxy", proxy_id=proxy_id, host=config.host)
            
            # Run test
            result = await test_proxy(config, timeout=self._test_timeout)
            
            # Update statistics in database
            await crud.update_proxy_stats(
                db=self._db,
                proxy_id=proxy_id,
                success=result.success,
                latency_ms=result.latency_ms,
            )
            
            # Auto-disable if failure threshold exceeded
            if not result.success:
                await self._check_failure_threshold(proxy)
            
            return result
        
        except RecordNotFoundError:
            raise
        except Exception as e:
            logger.error("Failed to test proxy", proxy_id=proxy_id, error=str(e))
            raise ProxyException(
                message=f"Failed to test proxy: {str(e)}",
                details={"proxy_id": proxy_id},
            )
    
    async def test_all_proxies(self) -> list[ProxyTestResult]:
        """Test all active proxies concurrently.
        
        Tests all proxies in the database concurrently with rate limiting
        and updates their statistics based on results.
        
        Returns:
            list[ProxyTestResult]: List of test results for all proxies.
        """
        try:
            # Get all proxies (including inactive for re-testing)
            proxies = await crud.list_proxies(self._db, limit=1000)
            
            if not proxies:
                logger.info("No proxies to test")
                return []
            
            # Convert to configs
            configs = [self._proxy_to_config(p) for p in proxies]
            
            logger.info("Testing all proxies", count=len(configs))
            
            # Test all proxies concurrently
            results = await test_multiple_proxies(
                configs,
                timeout=self._test_timeout,
                max_concurrent=settings.proxy_max_concurrent_tasks,
            )
            
            # Update database with results
            for result in results:
                try:
                    await crud.update_proxy_stats(
                        db=self._db,
                        proxy_id=result.proxy_id,
                        success=result.success,
                        latency_ms=result.latency_ms,
                    )
                    
                    # Check failure threshold
                    if not result.success:
                        proxy = await crud.get_proxy(self._db, result.proxy_id)
                        if proxy:
                            await self._check_failure_threshold(proxy)
                
                except Exception as e:
                    logger.error(
                        "Failed to update proxy stats",
                        proxy_id=result.proxy_id,
                        error=str(e),
                    )
            
            return results
        
        except Exception as e:
            logger.error("Failed to test all proxies", error=str(e))
            raise ProxyException(
                message=f"Failed to test all proxies: {str(e)}",
            )
    
    async def remove_proxy(self, proxy_id: int) -> bool:
        """Remove proxy from the system.
        
        Args:
            proxy_id: ID of the proxy to remove.
        
        Returns:
            bool: True if removed successfully, False if not found.
        """
        try:
            deleted = await crud.delete_proxy(self._db, proxy_id)
            
            if deleted:
                logger.info("Proxy removed", proxy_id=proxy_id)
            else:
                logger.warning("Proxy not found for removal", proxy_id=proxy_id)
            
            return deleted
        
        except Exception as e:
            logger.error("Failed to remove proxy", proxy_id=proxy_id, error=str(e))
            raise ProxyException(
                message=f"Failed to remove proxy: {str(e)}",
                details={"proxy_id": proxy_id},
            )
    
    async def get_proxy_stats(self, proxy_id: int) -> ProxyStats:
        """Get statistics for a specific proxy.
        
        Args:
            proxy_id: ID of the proxy.
        
        Returns:
            ProxyStats: Proxy statistics including success rate and latency.
        
        Raises:
            RecordNotFoundError: If proxy not found.
        """
        try:
            proxy = await crud.get_proxy(self._db, proxy_id)
            if not proxy:
                raise RecordNotFoundError("Proxy", proxy_id)
            
            return ProxyStats.from_db_proxy(proxy)
        
        except RecordNotFoundError:
            raise
        except Exception as e:
            logger.error("Failed to get proxy stats", proxy_id=proxy_id, error=str(e))
            raise ProxyException(
                message=f"Failed to get proxy stats: {str(e)}",
                details={"proxy_id": proxy_id},
            )
    
    async def mark_proxy_success(self, proxy_id: int) -> None:
        """Mark proxy as successful after usage.
        
        Updates success count and can reactivate previously disabled proxies
        that are now working.
        
        Args:
            proxy_id: ID of the proxy.
        """
        try:
            await crud.update_proxy_stats(
                db=self._db,
                proxy_id=proxy_id,
                success=True,
                latency_ms=None,
            )
            
            # Reactivate if it was disabled but is now working
            proxy = await crud.get_proxy(self._db, proxy_id)
            if proxy and not proxy.is_active:
                await crud.update_proxy(
                    db=self._db,
                    proxy_id=proxy_id,
                    is_active=True,
                )
                logger.info("Proxy reactivated after success", proxy_id=proxy_id)
        
        except Exception as e:
            logger.error(
                "Failed to mark proxy success",
                proxy_id=proxy_id,
                error=str(e),
            )
    
    async def mark_proxy_failure(self, proxy_id: int) -> None:
        """Mark proxy as failed after usage.
        
        Updates failure count and automatically disables proxy if
        failure threshold is exceeded.
        
        Args:
            proxy_id: ID of the proxy.
        """
        try:
            await crud.update_proxy_stats(
                db=self._db,
                proxy_id=proxy_id,
                success=False,
                latency_ms=None,
            )
            
            # Check failure threshold
            proxy = await crud.get_proxy(self._db, proxy_id)
            if proxy:
                await self._check_failure_threshold(proxy)
        
        except Exception as e:
            logger.error(
                "Failed to mark proxy failure",
                proxy_id=proxy_id,
                error=str(e),
            )
    
    async def get_all_proxies(
        self,
        is_active: Optional[bool] = None,
        limit: int = 100,
    ) -> list[ProxyConfig]:
        """Get all proxies with optional filtering.
        
        Args:
            is_active: Filter by active status (None for all).
            limit: Maximum number of proxies to return.
        
        Returns:
            list[ProxyConfig]: List of proxy configurations.
        """
        try:
            proxies = await crud.list_proxies(
                db=self._db,
                skip=0,
                limit=limit,
                is_active=is_active,
            )
            return [self._proxy_to_config(p) for p in proxies]
        
        except Exception as e:
            logger.error("Failed to get all proxies", error=str(e))
            raise ProxyException(
                message=f"Failed to get all proxies: {str(e)}",
            )
    
    async def _check_failure_threshold(self, proxy: Proxy) -> None:
        """Check if proxy has exceeded failure threshold and disable if needed.
        
        Args:
            proxy: Proxy instance to check.
        """
        # Calculate consecutive failure rate
        total = proxy.success_count + proxy.fail_count
        
        # Only disable if we have enough data
        if total < 10:
            return
        
        # Disable if too many recent failures
        if proxy.fail_count >= self._max_failure_threshold:
            failure_rate = proxy.fail_count / total
            
            if failure_rate > 0.5:  # More than 50% failure rate
                await crud.update_proxy(
                    db=self._db,
                    proxy_id=proxy.id,
                    is_active=False,
                )
                logger.warning(
                    "Proxy auto-disabled due to high failure rate",
                    proxy_id=proxy.id,
                    host=proxy.host,
                    fail_count=proxy.fail_count,
                    failure_rate=failure_rate,
                )
    
    def _proxy_to_config(self, proxy: Proxy) -> ProxyConfig:
        """Convert database Proxy model to ProxyConfig.
        
        Args:
            proxy: Database Proxy instance.
        
        Returns:
            ProxyConfig: Proxy configuration with decrypted password.
        """
        password = None
        if proxy.password_encrypted:
            try:
                password = encryption_manager.decrypt(proxy.password_encrypted)
            except Exception as e:
                logger.error(
                    "Failed to decrypt proxy password",
                    proxy_id=proxy.id,
                    error=str(e),
                )
        
        return ProxyConfig(
            id=proxy.id,
            host=proxy.host,
            port=proxy.port,
            username=proxy.username,
            password=password,
            protocol=proxy.protocol,
            latency_ms=proxy.latency_ms,
            is_active=proxy.is_active,
        )
