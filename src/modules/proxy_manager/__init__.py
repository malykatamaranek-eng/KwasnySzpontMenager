"""Proxy Manager module for Facebook automation system.

This module provides comprehensive proxy management including:
- Proxy configuration and credential management
- Round-robin proxy rotation
- Health checking and monitoring
- Automatic failure handling
- Connection pooling

Example usage:
    >>> from src.modules.proxy_manager import ProxyManager, ProxyConfig
    >>> from src.db.database import get_async_session
    >>> 
    >>> async with get_async_session() as db:
    >>>     manager = ProxyManager(db)
    >>>     
    >>>     # Add proxy
    >>>     config = await manager.add_proxy("192.168.1.1:1080:user:pass")
    >>>     
    >>>     # Get next proxy for rotation
    >>>     proxy = await manager.get_next_proxy()
    >>>     
    >>>     # Test proxy
    >>>     result = await manager.test_proxy(proxy.id)
    >>>     
    >>>     # Get statistics
    >>>     stats = await manager.get_proxy_stats(proxy.id)
"""

from src.modules.proxy_manager.manager import ProxyManager
from src.modules.proxy_manager.models import ProxyConfig, ProxyStats, ProxyTestResult
from src.modules.proxy_manager.tester import test_multiple_proxies, test_proxy

__all__ = [
    "ProxyManager",
    "ProxyConfig",
    "ProxyStats",
    "ProxyTestResult",
    "test_proxy",
    "test_multiple_proxies",
]
