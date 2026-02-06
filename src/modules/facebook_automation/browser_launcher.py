"""Browser launcher for Facebook automation.

This module handles browser initialization with Playwright, including:
- Proxy configuration
- Cookie loading from database
- Human-like browser configuration
- Persistent context management
"""

import logging
from typing import Optional

from playwright.async_api import Browser, BrowserContext, Playwright, async_playwright
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.config import Settings
from src.db.crud import get_facebook_account_cookies
from src.modules.facebook_automation.models import BrowserConfig

logger = logging.getLogger(__name__)


class BrowserLauncher:
    """Manages browser instance creation and configuration.
    
    Handles Playwright browser setup with proxy support, cookie restoration,
    and human-like browser fingerprinting to avoid detection.
    """
    
    def __init__(self, settings: Optional[Settings] = None):
        """Initialize browser launcher.
        
        Args:
            settings: Application settings, uses default if not provided
        """
        self.settings = settings or Settings()
        self._playwright: Optional[Playwright] = None
        self._browser: Optional[Browser] = None
        
    async def __aenter__(self) -> "BrowserLauncher":
        """Async context manager entry."""
        self._playwright = await async_playwright().start()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Async context manager exit."""
        await self.close()
    
    async def launch_browser(
        self,
        config: BrowserConfig,
        persistent_context: bool = False,
        context_path: Optional[str] = None,
        facebook_account_id: Optional[int] = None,
        db_session: Optional[AsyncSession] = None
    ) -> tuple[Browser, BrowserContext]:
        """Launch browser with specified configuration.
        
        Args:
            config: Browser configuration settings
            persistent_context: Whether to use persistent browser context
            context_path: Path for persistent context data
            facebook_account_id: Facebook account ID for loading cookies
            db_session: Database session for loading cookies
            
        Returns:
            Tuple of (Browser, BrowserContext)
            
        Raises:
            Exception: If browser launch fails
        """
        logger.info("Launching browser with Playwright")
        
        if not self._playwright:
            self._playwright = await async_playwright().start()
        
        try:
            # Prepare browser launch options
            launch_options = {
                "headless": config.headless,
                "args": [
                    "--disable-blink-features=AutomationControlled",
                    "--disable-dev-shm-usage",
                    "--disable-web-security",
                    "--no-sandbox",
                    "--disable-setuid-sandbox",
                ],
            }
            
            # Add proxy if configured
            if config.proxy:
                logger.info(f"Configuring proxy: {self._sanitize_proxy_url(config.proxy)}")
                proxy_parts = self._parse_proxy(config.proxy)
                launch_options["proxy"] = proxy_parts
            
            # Launch browser
            self._browser = await self._playwright.chromium.launch(**launch_options)
            logger.info("Browser launched successfully")
            
            # Create context
            if persistent_context and context_path:
                context = await self._create_persistent_context(
                    context_path,
                    config
                )
            else:
                context = await self._create_context(config)
            
            # Load cookies if account specified
            if facebook_account_id and db_session:
                await self._load_cookies(
                    context,
                    facebook_account_id,
                    db_session
                )
            
            # Configure anti-detection measures
            await self._setup_anti_detection(context)
            
            logger.info("Browser context created and configured")
            return self._browser, context
            
        except Exception as e:
            logger.error(f"Failed to launch browser: {e}")
            await self.close()
            raise
    
    async def _create_context(
        self,
        config: BrowserConfig
    ) -> BrowserContext:
        """Create new browser context with configuration.
        
        Args:
            config: Browser configuration
            
        Returns:
            BrowserContext instance
        """
        context_options = {
            "viewport": {
                "width": config.viewport_width,
                "height": config.viewport_height
            },
            "user_agent": config.user_agent or self._get_default_user_agent(),
            "locale": "en-US",
            "timezone_id": "America/New_York",
            "permissions": ["geolocation"],
            "geolocation": {"latitude": 40.7128, "longitude": -74.0060},  # New York
            "color_scheme": "light",
        }
        
        if not self._browser:
            raise RuntimeError("Browser not initialized")
        
        return await self._browser.new_context(**context_options)
    
    async def _create_persistent_context(
        self,
        context_path: str,
        config: BrowserConfig
    ) -> BrowserContext:
        """Create persistent browser context.
        
        Args:
            context_path: Path to store context data
            config: Browser configuration
            
        Returns:
            BrowserContext instance
        """
        if not self._playwright:
            raise RuntimeError("Playwright not initialized")
        
        context_options = {
            "viewport": {
                "width": config.viewport_width,
                "height": config.viewport_height
            },
            "user_agent": config.user_agent or self._get_default_user_agent(),
            "locale": "en-US",
            "timezone_id": "America/New_York",
            "headless": config.headless,
        }
        
        if config.proxy:
            proxy_parts = self._parse_proxy(config.proxy)
            context_options["proxy"] = proxy_parts
        
        return await self._playwright.chromium.launch_persistent_context(
            context_path,
            **context_options
        )
    
    async def _load_cookies(
        self,
        context: BrowserContext,
        facebook_account_id: int,
        db_session: AsyncSession
    ) -> None:
        """Load cookies from database into browser context.
        
        Args:
            context: Browser context to load cookies into
            facebook_account_id: Facebook account ID
            db_session: Database session
        """
        logger.info(f"Loading cookies for Facebook account {facebook_account_id}")
        
        try:
            cookies = await get_facebook_account_cookies(
                db_session,
                facebook_account_id
            )
            
            if cookies:
                await context.add_cookies(cookies)
                logger.info(f"Loaded {len(cookies)} cookies")
            else:
                logger.info("No cookies found for account")
                
        except Exception as e:
            logger.error(f"Failed to load cookies: {e}")
    
    async def _setup_anti_detection(self, context: BrowserContext) -> None:
        """Setup anti-detection measures in browser context.
        
        Args:
            context: Browser context to configure
        """
        logger.debug("Setting up anti-detection measures")
        
        try:
            # Override navigator.webdriver
            await context.add_init_script("""
                Object.defineProperty(navigator, 'webdriver', {
                    get: () => undefined
                });
            """)
            
            # Add plugins to navigator
            await context.add_init_script("""
                Object.defineProperty(navigator, 'plugins', {
                    get: () => [1, 2, 3, 4, 5]
                });
            """)
            
            # Override languages
            await context.add_init_script("""
                Object.defineProperty(navigator, 'languages', {
                    get: () => ['en-US', 'en']
                });
            """)
            
            logger.debug("Anti-detection setup completed")
            
        except Exception as e:
            logger.warning(f"Failed to setup anti-detection: {e}")
    
    def _parse_proxy(self, proxy_url: str) -> dict:
        """Parse proxy URL into Playwright proxy configuration.
        
        Args:
            proxy_url: Proxy URL in format "http://user:pass@host:port"
            
        Returns:
            Dictionary with proxy configuration
        """
        # Basic proxy parsing
        # Format: http://user:pass@host:port or http://host:port
        if "@" in proxy_url:
            protocol_and_auth, host_and_port = proxy_url.split("@")
            protocol, auth = protocol_and_auth.split("//")
            username, password = auth.split(":")
            
            return {
                "server": f"{protocol}//{host_and_port}",
                "username": username,
                "password": password,
            }
        else:
            return {"server": proxy_url}
    
    def _sanitize_proxy_url(self, proxy_url: str) -> str:
        """Sanitize proxy URL for logging (hide credentials).
        
        Args:
            proxy_url: Original proxy URL
            
        Returns:
            Sanitized proxy URL
        """
        if "@" in proxy_url:
            protocol_and_auth, host_and_port = proxy_url.split("@")
            protocol = protocol_and_auth.split("//")[0]
            return f"{protocol}//***:***@{host_and_port}"
        return proxy_url
    
    def _get_default_user_agent(self) -> str:
        """Get default user agent string.
        
        Returns:
            User agent string
        """
        return (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        )
    
    async def close(self) -> None:
        """Close browser and playwright instances."""
        logger.info("Closing browser")
        
        try:
            if self._browser:
                await self._browser.close()
                self._browser = None
            
            if self._playwright:
                await self._playwright.stop()
                self._playwright = None
                
            logger.info("Browser closed successfully")
            
        except Exception as e:
            logger.error(f"Error closing browser: {e}")
