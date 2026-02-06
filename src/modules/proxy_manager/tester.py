"""Proxy testing functionality for the Proxy Manager module.

This module provides async proxy testing capabilities to verify connectivity,
measure latency, and validate proxy health against multiple test endpoints.
"""

import asyncio
import time
from typing import Optional

import aiohttp

from src.core.config import settings
from src.core.exceptions import ProxyConnectionError, ProxyTimeoutError
from src.core.logging import get_logger
from src.modules.proxy_manager.models import ProxyConfig, ProxyTestResult

logger = get_logger(__name__)


# Test endpoints for proxy validation
TEST_ENDPOINTS = [
    "http://httpbin.org/ip",
    "https://api.ipify.org?format=json",
    "http://ip-api.com/json",
]


async def test_proxy(
    proxy_config: ProxyConfig,
    timeout: int = 10,
    test_endpoint: Optional[str] = None,
) -> ProxyTestResult:
    """Test proxy connectivity and measure latency.
    
    Attempts to connect through the proxy to a test endpoint and measures
    the response time. Tests against multiple endpoints if primary fails.
    
    Args:
        proxy_config: Proxy configuration to test.
        timeout: Connection timeout in seconds (default: 10).
        test_endpoint: Optional specific endpoint to test. If not provided,
            uses default test endpoints with fallback.
    
    Returns:
        ProxyTestResult: Test result with success status and latency.
    """
    endpoints = [test_endpoint] if test_endpoint else TEST_ENDPOINTS.copy()
    
    for endpoint in endpoints:
        try:
            result = await _test_proxy_endpoint(proxy_config, endpoint, timeout)
            if result.success:
                logger.debug(
                    "Proxy test successful",
                    proxy_id=proxy_config.id,
                    host=proxy_config.host,
                    latency_ms=result.latency_ms,
                    endpoint=endpoint,
                )
                return result
        except Exception as e:
            logger.debug(
                "Proxy test failed for endpoint",
                proxy_id=proxy_config.id,
                endpoint=endpoint,
                error=str(e),
            )
            continue
    
    # All endpoints failed
    error_msg = f"All test endpoints failed for proxy {proxy_config.host}:{proxy_config.port}"
    logger.warning(
        "Proxy test failed all endpoints",
        proxy_id=proxy_config.id,
        host=proxy_config.host,
        port=proxy_config.port,
    )
    
    return ProxyTestResult(
        proxy_id=proxy_config.id or 0,
        success=False,
        latency_ms=None,
        error_message=error_msg,
        endpoint=endpoints[0],
    )


async def _test_proxy_endpoint(
    proxy_config: ProxyConfig,
    endpoint: str,
    timeout: int,
) -> ProxyTestResult:
    """Test proxy against a specific endpoint.
    
    Args:
        proxy_config: Proxy configuration to test.
        endpoint: HTTP endpoint to test against.
        timeout: Connection timeout in seconds.
    
    Returns:
        ProxyTestResult: Test result with success status and latency.
    
    Raises:
        ProxyConnectionError: If connection fails.
        ProxyTimeoutError: If connection times out.
    """
    # Build proxy URL
    proxy_url = _build_proxy_url(proxy_config)
    
    # Configure timeout
    timeout_config = aiohttp.ClientTimeout(
        total=timeout,
        connect=timeout,
        sock_read=timeout,
    )
    
    start_time = time.time()
    
    try:
        async with aiohttp.ClientSession(timeout=timeout_config) as session:
            async with session.get(endpoint, proxy=proxy_url) as response:
                # Measure latency
                latency_ms = int((time.time() - start_time) * 1000)
                
                # Check response status
                if response.status == 200:
                    # Try to read response to ensure full connectivity
                    await response.text()
                    
                    return ProxyTestResult(
                        proxy_id=proxy_config.id or 0,
                        success=True,
                        latency_ms=latency_ms,
                        error_message=None,
                        endpoint=endpoint,
                    )
                else:
                    return ProxyTestResult(
                        proxy_id=proxy_config.id or 0,
                        success=False,
                        latency_ms=latency_ms,
                        error_message=f"HTTP {response.status}",
                        endpoint=endpoint,
                    )
    
    except asyncio.TimeoutError:
        latency_ms = int((time.time() - start_time) * 1000)
        error_msg = f"Connection timeout after {timeout}s"
        logger.debug(
            "Proxy connection timeout",
            proxy_id=proxy_config.id,
            host=proxy_config.host,
            timeout=timeout,
        )
        raise ProxyTimeoutError(proxy_config.host, timeout)
    
    except aiohttp.ClientProxyConnectionError as e:
        error_msg = f"Proxy connection error: {str(e)}"
        logger.debug(
            "Proxy connection error",
            proxy_id=proxy_config.id,
            host=proxy_config.host,
            error=str(e),
        )
        raise ProxyConnectionError(
            proxy_config.host,
            proxy_config.port,
            str(e),
        )
    
    except aiohttp.ClientError as e:
        error_msg = f"Client error: {str(e)}"
        logger.debug(
            "Proxy client error",
            proxy_id=proxy_config.id,
            host=proxy_config.host,
            error=str(e),
        )
        return ProxyTestResult(
            proxy_id=proxy_config.id or 0,
            success=False,
            latency_ms=None,
            error_message=error_msg,
            endpoint=endpoint,
        )
    
    except Exception as e:
        error_msg = f"Unexpected error: {str(e)}"
        logger.error(
            "Proxy test unexpected error",
            proxy_id=proxy_config.id,
            host=proxy_config.host,
            error=str(e),
        )
        return ProxyTestResult(
            proxy_id=proxy_config.id or 0,
            success=False,
            latency_ms=None,
            error_message=error_msg,
            endpoint=endpoint,
        )


def _build_proxy_url(proxy_config: ProxyConfig) -> str:
    """Build proxy URL from configuration.
    
    Args:
        proxy_config: Proxy configuration.
    
    Returns:
        str: Formatted proxy URL (e.g., socks5://user:pass@host:port).
    """
    if proxy_config.username and proxy_config.password:
        return (
            f"{proxy_config.protocol}://{proxy_config.username}:"
            f"{proxy_config.password}@{proxy_config.host}:{proxy_config.port}"
        )
    else:
        return f"{proxy_config.protocol}://{proxy_config.host}:{proxy_config.port}"


async def test_multiple_proxies(
    proxy_configs: list[ProxyConfig],
    timeout: int = 10,
    max_concurrent: Optional[int] = None,
) -> list[ProxyTestResult]:
    """Test multiple proxies concurrently.
    
    Args:
        proxy_configs: List of proxy configurations to test.
        timeout: Connection timeout in seconds per proxy (default: 10).
        max_concurrent: Maximum concurrent tests. If not provided,
            uses value from settings.
    
    Returns:
        list[ProxyTestResult]: List of test results for all proxies.
    """
    max_concurrent = max_concurrent or settings.proxy_max_concurrent_tasks
    
    # Create semaphore to limit concurrent tests
    semaphore = asyncio.Semaphore(max_concurrent)
    
    async def test_with_semaphore(proxy: ProxyConfig) -> ProxyTestResult:
        """Test proxy with semaphore for concurrency control."""
        async with semaphore:
            return await test_proxy(proxy, timeout=timeout)
    
    # Run all tests concurrently with limit
    logger.info(
        "Testing multiple proxies",
        count=len(proxy_configs),
        max_concurrent=max_concurrent,
    )
    
    results = await asyncio.gather(
        *[test_with_semaphore(proxy) for proxy in proxy_configs],
        return_exceptions=False,
    )
    
    success_count = sum(1 for r in results if r.success)
    logger.info(
        "Proxy testing completed",
        total=len(results),
        successful=success_count,
        failed=len(results) - success_count,
    )
    
    return results
