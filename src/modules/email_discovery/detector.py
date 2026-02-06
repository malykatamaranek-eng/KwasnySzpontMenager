"""Live email discovery system using Playwright."""
from typing import Optional, Dict, Any
from playwright.async_api import async_playwright, Browser, BrowserContext, Page
import structlog
from src.modules.email_discovery.providers.base import BaseEmailProvider
from src.modules.email_discovery.providers.wp_pl import WpPlProvider
from src.modules.email_discovery.providers.o2_pl import O2PlProvider
from src.modules.email_discovery.providers.onet_pl import OnetPlProvider
from src.modules.email_discovery.providers.interia_pl import InteriaPlProvider
from src.core.exceptions import EmailProviderError
from src.core.config import settings

logger = structlog.get_logger()


class LiveEmailDiscovery:
    """
    System for discovering email endpoints through:
    - Network request analysis in headless browser
    - Form detection with CSS selectors
    - JavaScript endpoint extraction
    - Provider-specific implementations
    """
    
    PROVIDER_MAP = {
        "wp.pl": WpPlProvider,
        "o2.pl": O2PlProvider,
        "onet.pl": OnetPlProvider,
        "interia.pl": InteriaPlProvider,
    }
    
    def __init__(self):
        """Initialize email discovery system."""
        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None
    
    async def __aenter__(self):
        """Async context manager entry."""
        await self.initialize()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()
    
    async def initialize(self) -> None:
        """Initialize Playwright browser."""
        self.playwright = await async_playwright().start()
        self.browser = await self.playwright.chromium.launch(
            headless=settings.PLAYWRIGHT_HEADLESS,
            args=[
                '--disable-blink-features=AutomationControlled',
                '--disable-dev-shm-usage',
                '--no-sandbox'
            ]
        )
        logger.info("browser_initialized")
    
    async def close(self) -> None:
        """Close browser and Playwright."""
        if self.context:
            await self.context.close()
        if self.browser:
            await self.browser.close()
        if hasattr(self, 'playwright'):
            await self.playwright.stop()
        logger.info("browser_closed")
    
    def detect_provider(self, email: str) -> str:
        """
        Detect email provider from email address.
        
        Args:
            email: Email address
            
        Returns:
            Provider name
            
        Raises:
            EmailProviderError: If provider not supported
        """
        domain = email.split("@")[-1].lower()
        
        if domain in self.PROVIDER_MAP:
            return domain
        
        raise EmailProviderError(f"Unsupported email provider: {domain}")
    
    def get_provider_instance(self, email: str, password: str) -> BaseEmailProvider:
        """
        Get provider instance for email.
        
        Args:
            email: Email address
            password: Email password
            
        Returns:
            Provider instance
            
        Raises:
            EmailProviderError: If provider not supported
        """
        provider_name = self.detect_provider(email)
        provider_class = self.PROVIDER_MAP[provider_name]
        return provider_class(email, password)
    
    async def create_context(self, proxy: Optional[str] = None) -> BrowserContext:
        """
        Create browser context with anti-detection measures.
        
        Args:
            proxy: Optional proxy URL
            
        Returns:
            Browser context
        """
        import random
        
        user_agents = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0"
        ]
        
        context_options = {
            "user_agent": random.choice(user_agents),
            "viewport": {
                "width": random.randint(1024, 1920),
                "height": random.randint(768, 1080)
            },
            "locale": "pl-PL",
            "timezone_id": "Europe/Warsaw",
            "permissions": [],
            "java_script_enabled": True,
        }
        
        if proxy:
            context_options["proxy"] = {"server": proxy}
        
        context = await self.browser.new_context(**context_options)
        
        # Anti-detection: Override navigator.webdriver
        await context.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined
            });
        """)
        
        logger.info("browser_context_created", proxy=bool(proxy))
        return context
    
    async def login_to_provider(
        self, 
        email: str, 
        password: str, 
        proxy: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Login to email provider and return session data.
        
        Args:
            email: Email address
            password: Email password
            proxy: Optional proxy URL
            
        Returns:
            Dict with login result and session data
            
        Raises:
            EmailProviderError: If login fails
        """
        provider = self.get_provider_instance(email, password)
        
        logger.info("email_login_start", email=email, provider=provider.provider_name)
        
        context = await self.create_context(proxy)
        page = await context.new_page()
        
        try:
            # Perform login
            success = await provider.login(page)
            
            if not success:
                raise EmailProviderError(f"Login failed for {email}")
            
            # Get IMAP config
            imap_config = await provider.get_imap_config()
            
            # Get cookies
            cookies = await context.cookies()
            
            result = {
                "success": True,
                "provider": provider.provider_name,
                "email": email,
                "cookies": cookies,
                "imap_config": imap_config,
                "session_data": provider.session_data
            }
            
            logger.info("email_login_success", email=email, provider=provider.provider_name)
            return result
            
        except Exception as e:
            logger.error("email_login_failed", email=email, error=str(e))
            raise EmailProviderError(f"Login failed: {str(e)}")
        finally:
            await page.close()
            await context.close()
    
    async def verify_imap_credentials(
        self, 
        email: str, 
        password: str
    ) -> Dict[str, Any]:
        """
        Verify IMAP credentials work.
        
        Args:
            email: Email address
            password: Email password
            
        Returns:
            Dict with verification result
        """
        import imaplib
        import ssl
        
        provider = self.get_provider_instance(email, password)
        imap_config = await provider.get_imap_config()
        
        try:
            context = ssl.create_default_context()
            
            with imaplib.IMAP4_SSL(
                imap_config["host"], 
                imap_config["port"],
                ssl_context=context
            ) as imap:
                imap.login(email, password)
                imap.select("INBOX")
                
                logger.info("imap_verification_success", email=email)
                return {
                    "success": True,
                    "email": email,
                    "imap_host": imap_config["host"],
                    "imap_port": imap_config["port"]
                }
                
        except Exception as e:
            logger.error("imap_verification_failed", email=email, error=str(e))
            return {
                "success": False,
                "email": email,
                "error": str(e)
            }
