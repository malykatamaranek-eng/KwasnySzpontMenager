"""Base class for email providers."""
from abc import ABC, abstractmethod
from typing import Optional, Dict, Any
from playwright.async_api import Page, Browser, BrowserContext
import structlog
from src.core.exceptions import EmailProviderError

logger = structlog.get_logger()


class BaseEmailProvider(ABC):
    """
    Abstract base class for email providers.
    
    Provides common functionality for:
    - Session management
    - Cookie handling
    - Error retry logic
    - Login abstraction
    """
    
    def __init__(self, email: str, password: str):
        """
        Initialize email provider.
        
        Args:
            email: Email address
            password: Email password
        """
        self.email = email
        self.password = password
        self.cookies: Optional[Dict[str, Any]] = None
        self.session_data: Optional[Dict[str, Any]] = None
        
    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Get provider name."""
        pass
    
    @property
    @abstractmethod
    def login_url(self) -> str:
        """Get login URL."""
        pass
    
    @property
    @abstractmethod
    def imap_host(self) -> str:
        """Get IMAP host."""
        pass
    
    @property
    @abstractmethod
    def imap_port(self) -> int:
        """Get IMAP port."""
        pass
    
    @abstractmethod
    async def login(self, page: Page) -> bool:
        """
        Perform login to email provider.
        
        Args:
            page: Playwright page
            
        Returns:
            True if login successful, False otherwise
            
        Raises:
            EmailProviderError: If login fails
        """
        pass
    
    async def get_imap_config(self) -> Dict[str, Any]:
        """
        Get IMAP configuration.
        
        Returns:
            Dict with IMAP configuration
        """
        return {
            "host": self.imap_host,
            "port": self.imap_port,
            "email": self.email,
            "password": self.password,
            "use_ssl": True
        }
    
    async def save_cookies(self, page: Page) -> None:
        """
        Save cookies from page.
        
        Args:
            page: Playwright page
        """
        context = page.context
        self.cookies = await context.cookies()
        logger.info("cookies_saved", provider=self.provider_name, count=len(self.cookies))
    
    async def load_cookies(self, context: BrowserContext) -> None:
        """
        Load cookies into browser context.
        
        Args:
            context: Browser context
        """
        if self.cookies:
            await context.add_cookies(self.cookies)
            logger.info("cookies_loaded", provider=self.provider_name, count=len(self.cookies))
    
    async def wait_for_navigation(self, page: Page, timeout: int = 30000) -> None:
        """
        Wait for navigation to complete.
        
        Args:
            page: Playwright page
            timeout: Timeout in milliseconds
        """
        try:
            await page.wait_for_load_state("networkidle", timeout=timeout)
        except Exception as e:
            logger.warning("navigation_wait_timeout", provider=self.provider_name, error=str(e))
    
    async def handle_errors(self, page: Page) -> Optional[str]:
        """
        Check for error messages on page.
        
        Args:
            page: Playwright page
            
        Returns:
            Error message if found, None otherwise
        """
        # Common error selectors
        error_selectors = [
            ".error",
            ".alert-error",
            "[class*='error']",
            "[id*='error']",
            ".message.error"
        ]
        
        for selector in error_selectors:
            try:
                error_element = await page.query_selector(selector)
                if error_element:
                    error_text = await error_element.text_content()
                    if error_text and error_text.strip():
                        logger.error("login_error_detected", provider=self.provider_name, error=error_text)
                        return error_text.strip()
            except Exception:
                continue
        
        return None
