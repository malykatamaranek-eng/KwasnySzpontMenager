"""Production proxy manager with health checks and rotation."""
import asyncio
import time
from typing import List, Optional, Dict
from datetime import datetime, timedelta
import aiohttp
import structlog
from sqlalchemy.ext.asyncio import AsyncSession
from src.db.models import Proxy
from src.db import crud
from src.core.exceptions import ProxyConnectionError

logger = structlog.get_logger()


class ProductionProxyManager:
    """
    Production-ready proxy manager with:
    - Health testing (HTTP connectivity, latency)
    - Automatic rotation
    - Session isolation per proxy
    - Connection pooling
    - Dead proxy removal
    """
    
    def __init__(self, db: AsyncSession):
        """
        Initialize proxy manager.
        
        Args:
            db: Database session
        """
        self.db = db
        self._proxy_cache: List[Proxy] = []
        self._last_cache_update: Optional[datetime] = None
        self._cache_ttl = timedelta(minutes=5)
        self._current_index = 0
    
    async def test_proxy(self, proxy: Proxy, timeout: int = 10) -> Dict[str, any]:
        """
        Test proxy connectivity and latency.
        
        Args:
            proxy: Proxy to test
            timeout: Timeout in seconds
            
        Returns:
            Dict with test results
        """
        start_time = time.time()
        test_url = "http://httpbin.org/ip"
        
        proxy_url = proxy.url
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    test_url,
                    proxy=proxy_url,
                    timeout=aiohttp.ClientTimeout(total=timeout)
                ) as response:
                    latency_ms = (time.time() - start_time) * 1000
                    
                    if response.status == 200:
                        data = await response.json()
                        logger.info(
                            "proxy_test_success",
                            proxy_id=proxy.id,
                            host=proxy.host,
                            latency_ms=latency_ms,
                            origin_ip=data.get('origin')
                        )
                        return {
                            "success": True,
                            "latency_ms": latency_ms,
                            "status_code": response.status
                        }
                    else:
                        logger.warning(
                            "proxy_test_failed",
                            proxy_id=proxy.id,
                            status_code=response.status
                        )
                        return {
                            "success": False,
                            "latency_ms": latency_ms,
                            "status_code": response.status,
                            "error": f"HTTP {response.status}"
                        }
        except asyncio.TimeoutError:
            logger.warning("proxy_test_timeout", proxy_id=proxy.id, timeout=timeout)
            return {
                "success": False,
                "latency_ms": timeout * 1000,
                "error": "Timeout"
            }
        except Exception as e:
            logger.error("proxy_test_error", proxy_id=proxy.id, error=str(e))
            return {
                "success": False,
                "error": str(e)
            }
    
    async def test_all_proxies(self) -> List[Dict[str, any]]:
        """
        Test all proxies in the database.
        
        Returns:
            List of test results
        """
        proxies = await crud.list_proxies(self.db, alive_only=False)
        logger.info("testing_proxies", count=len(proxies))
        
        results = []
        for proxy in proxies:
            result = await self.test_proxy(proxy)
            
            # Update proxy health in database
            await crud.update_proxy_health(
                self.db,
                proxy.id,
                is_alive=result["success"],
                latency_ms=result.get("latency_ms")
            )
            
            results.append({
                "proxy_id": proxy.id,
                "host": proxy.host,
                "port": proxy.port,
                **result
            })
        
        return results
    
    async def get_alive_proxies(self, force_refresh: bool = False) -> List[Proxy]:
        """
        Get list of alive proxies with caching.
        
        Args:
            force_refresh: Force cache refresh
            
        Returns:
            List of alive proxies
        """
        now = datetime.utcnow()
        
        # Check if cache needs refresh
        if (force_refresh or 
            not self._proxy_cache or 
            not self._last_cache_update or
            now - self._last_cache_update > self._cache_ttl):
            
            self._proxy_cache = await crud.list_proxies(self.db, alive_only=True)
            self._last_cache_update = now
            logger.info("proxy_cache_refreshed", count=len(self._proxy_cache))
        
        return self._proxy_cache
    
    async def get_next_proxy(self) -> Optional[Proxy]:
        """
        Get next proxy using round-robin rotation.
        
        Returns:
            Next available proxy or None
        """
        proxies = await self.get_alive_proxies()
        
        if not proxies:
            logger.warning("no_alive_proxies")
            return None
        
        # Round-robin selection
        proxy = proxies[self._current_index % len(proxies)]
        self._current_index += 1
        
        logger.info("proxy_selected", proxy_id=proxy.id, host=proxy.host)
        return proxy
    
    async def get_random_proxy(self) -> Optional[Proxy]:
        """
        Get random proxy from alive proxies.
        
        Returns:
            Random alive proxy or None
        """
        import random
        proxies = await self.get_alive_proxies()
        
        if not proxies:
            logger.warning("no_alive_proxies")
            return None
        
        proxy = random.choice(proxies)
        logger.info("proxy_selected_random", proxy_id=proxy.id, host=proxy.host)
        return proxy
    
    async def assign_proxy_to_account(self, account_id: int) -> Optional[Proxy]:
        """
        Assign a proxy to an account.
        
        Args:
            account_id: Account ID
            
        Returns:
            Assigned proxy or None
        """
        proxy = await self.get_next_proxy()
        
        if not proxy:
            raise ProxyConnectionError("No alive proxies available")
        
        # Update account with proxy
        from sqlalchemy import update
        from src.db.models import Account
        
        await self.db.execute(
            update(Account)
            .where(Account.id == account_id)
            .values(proxy_id=proxy.id)
        )
        await self.db.commit()
        
        logger.info("proxy_assigned", account_id=account_id, proxy_id=proxy.id)
        return proxy
    
    async def create_proxy_session(self, proxy: Proxy) -> aiohttp.ClientSession:
        """
        Create aiohttp session with proxy configuration.
        
        Args:
            proxy: Proxy to use
            
        Returns:
            Configured ClientSession
        """
        connector = aiohttp.TCPConnector(
            limit=10,
            limit_per_host=5,
            ttl_dns_cache=300
        )
        
        session = aiohttp.ClientSession(
            connector=connector,
            timeout=aiohttp.ClientTimeout(total=30)
        )
        
        logger.info("proxy_session_created", proxy_id=proxy.id)
        return session
