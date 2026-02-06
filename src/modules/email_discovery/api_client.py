"""HTTP client for email provider interactions with advanced features.

This module provides an asynchronous HTTP client with proxy support,
retry logic, cookie management, and user-agent rotation.
"""

import asyncio
import random
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta
import structlog

import httpx
from httpx import AsyncClient, Response, Timeout

from ..proxy_manager.models import ProxyConfig


logger = structlog.get_logger(__name__)


class AsyncHTTPClient:
    """Advanced asynchronous HTTP client for email provider APIs.
    
    Features:
        - Automatic retry with exponential backoff
        - Proxy rotation support
        - Cookie persistence
        - User-Agent randomization
        - Request/response logging
        
    Args:
        timeout_seconds: Default request timeout
        max_retries: Maximum retry attempts
        backoff_factor: Exponential backoff multiplier
        verify_ssl: SSL certificate verification
        
    Example:
        >>> client = AsyncHTTPClient(timeout_seconds=30)
        >>> async with client:
        ...     response = await client.get("https://example.com")
    """
    
    _USER_AGENTS = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:122.0) Gecko/20100101",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 14.2) AppleWebKit/605.1.15",
    ]
    
    def __init__(
        self,
        timeout_seconds: int = 30,
        max_retries: int = 3,
        backoff_factor: float = 2.0,
        verify_ssl: bool = True
    ):
        """Initialize HTTP client with configuration."""
        self.timeout_seconds = timeout_seconds
        self.max_retries = max_retries
        self.backoff_factor = backoff_factor
        self.verify_ssl = verify_ssl
        
        self._http_client: Optional[AsyncClient] = None
        self._cookie_storage: Dict[str, str] = {}
        self._request_count = 0
        self._active_proxy: Optional[ProxyConfig] = None
        
        logger.info(
            "http_client_initialized",
            timeout=timeout_seconds,
            retries=max_retries,
            backoff=backoff_factor
        )
    
    async def __aenter__(self):
        """Context manager entry."""
        await self._initialize_client()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        await self.shutdown()
    
    async def _initialize_client(self):
        """Create underlying HTTP client instance."""
        timeout_config = Timeout(
            connect=self.timeout_seconds,
            read=self.timeout_seconds,
            write=self.timeout_seconds,
            pool=self.timeout_seconds
        )
        
        self._http_client = AsyncClient(
            timeout=timeout_config,
            verify=self.verify_ssl,
            follow_redirects=True,
            http2=False
        )
        
        logger.debug("http_client_created")
    
    async def shutdown(self):
        """Close HTTP client and cleanup resources."""
        if self._http_client:
            await self._http_client.aclose()
            self._http_client = None
            logger.debug("http_client_closed")
    
    def _select_user_agent(self) -> str:
        """Choose random User-Agent string."""
        return random.choice(self._USER_AGENTS)
    
    def _build_proxy_url(self, proxy_cfg: ProxyConfig) -> str:
        """Construct proxy URL from configuration.
        
        Args:
            proxy_cfg: Proxy configuration object
            
        Returns:
            str: Formatted proxy URL
        """
        if proxy_cfg.username and proxy_cfg.password:
            auth_part = f"{proxy_cfg.username}:{proxy_cfg.password}@"
        else:
            auth_part = ""
        
        return f"{proxy_cfg.protocol}://{auth_part}{proxy_cfg.host}:{proxy_cfg.port}"
    
    def inject_cookies(self, cookie_dict: Dict[str, str]):
        """Add cookies to internal storage.
        
        Args:
            cookie_dict: Cookies to add
        """
        self._cookie_storage.update(cookie_dict)
        logger.debug("cookies_injected", count=len(cookie_dict))
    
    def extract_cookies(self) -> Dict[str, str]:
        """Retrieve stored cookies.
        
        Returns:
            Dict[str, str]: Current cookie storage
        """
        return self._cookie_storage.copy()
    
    def purge_cookies(self):
        """Clear all stored cookies."""
        self._cookie_storage.clear()
        logger.debug("cookies_purged")
    
    async def _execute_with_retry(
        self,
        method: str,
        url: str,
        **request_kwargs
    ) -> Response:
        """Execute HTTP request with retry logic.
        
        Args:
            method: HTTP method (GET, POST, etc.)
            url: Target URL
            **request_kwargs: Additional request parameters
            
        Returns:
            Response: HTTP response object
            
        Raises:
            httpx.HTTPError: On final failure after retries
        """
        if not self._http_client:
            await self._initialize_client()
        
        last_error = None
        
        for attempt_num in range(self.max_retries + 1):
            try:
                self._request_count += 1
                
                headers = request_kwargs.pop("headers", {})
                headers.setdefault("User-Agent", self._select_user_agent())
                
                if self._cookie_storage:
                    cookie_str = "; ".join(f"{k}={v}" for k, v in self._cookie_storage.items())
                    headers["Cookie"] = cookie_str
                
                logger.debug(
                    "http_request_starting",
                    method=method,
                    url=url,
                    attempt=attempt_num + 1,
                    request_id=self._request_count
                )
                
                response = await self._http_client.request(
                    method=method,
                    url=url,
                    headers=headers,
                    **request_kwargs
                )
                
                self._capture_response_cookies(response)
                
                logger.info(
                    "http_request_completed",
                    method=method,
                    url=url,
                    status=response.status_code,
                    attempt=attempt_num + 1
                )
                
                return response
                
            except Exception as error:
                last_error = error
                
                logger.warning(
                    "http_request_failed",
                    method=method,
                    url=url,
                    attempt=attempt_num + 1,
                    error=str(error),
                    error_type=type(error).__name__
                )
                
                if attempt_num < self.max_retries:
                    delay = (self.backoff_factor ** attempt_num) + random.uniform(0, 1)
                    await asyncio.sleep(delay)
                else:
                    raise
        
        raise last_error
    
    def _capture_response_cookies(self, response: Response):
        """Extract and store cookies from response.
        
        Args:
            response: HTTP response object
        """
        if response.cookies:
            for name, value in response.cookies.items():
                self._cookie_storage[name] = value
            logger.debug("cookies_captured", count=len(response.cookies))
    
    async def get(
        self,
        url: str,
        params: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
        proxy_config: Optional[ProxyConfig] = None
    ) -> Response:
        """Execute GET request.
        
        Args:
            url: Target URL
            params: Query parameters
            headers: HTTP headers
            proxy_config: Proxy configuration
            
        Returns:
            Response: HTTP response
        """
        kwargs = {"params": params, "headers": headers or {}}
        
        if proxy_config:
            kwargs["proxy"] = self._build_proxy_url(proxy_config)
            self._active_proxy = proxy_config
        
        return await self._execute_with_retry("GET", url, **kwargs)
    
    async def post(
        self,
        url: str,
        data: Optional[Dict[str, Any]] = None,
        json_data: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
        proxy_config: Optional[ProxyConfig] = None
    ) -> Response:
        """Execute POST request.
        
        Args:
            url: Target URL
            data: Form data
            json_data: JSON payload
            headers: HTTP headers
            proxy_config: Proxy configuration
            
        Returns:
            Response: HTTP response
        """
        kwargs = {"headers": headers or {}}
        
        if data:
            kwargs["data"] = data
        if json_data:
            kwargs["json"] = json_data
        
        if proxy_config:
            kwargs["proxy"] = self._build_proxy_url(proxy_config)
            self._active_proxy = proxy_config
        
        return await self._execute_with_retry("POST", url, **kwargs)
    
    async def put(
        self,
        url: str,
        data: Optional[Dict[str, Any]] = None,
        json_data: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
        proxy_config: Optional[ProxyConfig] = None
    ) -> Response:
        """Execute PUT request.
        
        Args:
            url: Target URL
            data: Form data
            json_data: JSON payload
            headers: HTTP headers
            proxy_config: Proxy configuration
            
        Returns:
            Response: HTTP response
        """
        kwargs = {"headers": headers or {}}
        
        if data:
            kwargs["data"] = data
        if json_data:
            kwargs["json"] = json_data
        
        if proxy_config:
            kwargs["proxy"] = self._build_proxy_url(proxy_config)
            self._active_proxy = proxy_config
        
        return await self._execute_with_retry("PUT", url, **kwargs)
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get client usage statistics.
        
        Returns:
            Dict: Statistics including request count, cookies, etc.
        """
        return {
            "total_requests": self._request_count,
            "stored_cookies": len(self._cookie_storage),
            "active_proxy": self._active_proxy.host if self._active_proxy else None,
            "client_active": self._http_client is not None
        }
