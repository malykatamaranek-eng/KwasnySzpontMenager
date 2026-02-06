"""WP.pl email provider implementation."""
import asyncio
from typing import Optional
from playwright.async_api import Page
import structlog
from src.modules.email_discovery.providers.base import BaseEmailProvider
from src.core.exceptions import EmailProviderError

logger = structlog.get_logger()


class WpPlProvider(BaseEmailProvider):
    """WP.pl email provider."""
    
    @property
    def provider_name(self) -> str:
        return "wp.pl"
    
    @property
    def login_url(self) -> str:
        return "https://profil.wp.pl/login"
    
    @property
    def imap_host(self) -> str:
        return "imap.wp.pl"
    
    @property
    def imap_port(self) -> int:
        return 993
    
    async def login(self, page: Page) -> bool:
        """
        Perform login to WP.pl.
        
        Args:
            page: Playwright page
            
        Returns:
            True if login successful
            
        Raises:
            EmailProviderError: If login fails
        """
        try:
            logger.info("wp_pl_login_start", email=self.email)
            
            # Navigate to login page
            await page.goto(self.login_url, wait_until="networkidle", timeout=30000)
            await asyncio.sleep(1)
            
            # Fill email
            email_input = await page.wait_for_selector('input[name="login"], input[type="email"], input[id*="login"]', timeout=10000)
            await email_input.fill(self.email)
            await asyncio.sleep(0.5)
            
            # Fill password
            password_input = await page.wait_for_selector('input[name="password"], input[type="password"]', timeout=10000)
            await password_input.fill(self.password)
            await asyncio.sleep(0.5)
            
            # Click login button
            login_button = await page.wait_for_selector('button[type="submit"], input[type="submit"], button:has-text("Zaloguj")', timeout=10000)
            await login_button.click()
            
            # Wait for navigation
            await asyncio.sleep(3)
            await self.wait_for_navigation(page)
            
            # Check for errors
            error = await self.handle_errors(page)
            if error:
                raise EmailProviderError(f"WP.pl login failed: {error}")
            
            # Check if logged in (look for logout button or user menu)
            try:
                await page.wait_for_selector('[href*="logout"], [class*="user"], [class*="profile"]', timeout=5000)
                await self.save_cookies(page)
                logger.info("wp_pl_login_success", email=self.email)
                return True
            except Exception:
                # Try alternative success indicators
                current_url = page.url
                if "profil.wp.pl/login" not in current_url:
                    await self.save_cookies(page)
                    logger.info("wp_pl_login_success", email=self.email)
                    return True
                else:
                    raise EmailProviderError("WP.pl login failed: Could not verify successful login")
                
        except Exception as e:
            logger.error("wp_pl_login_failed", email=self.email, error=str(e))
            raise EmailProviderError(f"WP.pl login failed: {str(e)}")
