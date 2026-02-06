"""Facebook 2FA handler with Playwright integration."""
import asyncio
import re
from typing import Optional
from playwright.async_api import Page, Browser, BrowserContext
import structlog
from src.modules.email_processor.imap_client import AsyncIMAPProcessor
from src.core.exceptions import FacebookAutomationError, TwoFactorCodeNotFoundError

logger = structlog.get_logger()


class FacebookTwoFactorHandler:
    """
    Facebook 2FA handler with full Playwright integration.
    
    Configuration:
    - Mobile User Agent for better compatibility
    - Tinder OAuth Client ID for token extraction
    - Complete 2FA flow handling
    """
    
    MOBILE_USER_AGENT = (
        "Mozilla/5.0 (Linux; U; en-gb; KFTHWI Build/JDQ39) "
        "AppleWebKit/535.19 (KHTML, like Gecko) Silk/3.16 Safari/535.19"
    )
    
    CLIENT_ID = '464891386855067'  # Tinder OAuth
    
    def __init__(self, imap_client: AsyncIMAPProcessor):
        """
        Initialize 2FA handler.
        
        Args:
            imap_client: IMAP client for code retrieval
        """
        self.imap_client = imap_client
    
    def get_oauth_url(self, state: str = "state123") -> str:
        """
        Get Facebook OAuth URL.
        
        Args:
            state: OAuth state parameter
            
        Returns:
            OAuth URL
        """
        return (
            f"https://www.facebook.com/v2.6/dialog/oauth"
            f"?redirect_uri=fb{self.CLIENT_ID}://authorize/"
            f"&display=touch"
            f"&state={state}"
            f"&scope=user_birthday,user_photos,user_education_history,email,user_relationship_details,"
            f"user_friends,user_work_history,user_likes"
            f"&response_type=token,signed_request"
            f"&client_id={self.CLIENT_ID}"
        )
    
    async def detect_2fa_page(self, page: Page) -> bool:
        """
        Detect if we're on a 2FA challenge page.
        
        Args:
            page: Playwright page
            
        Returns:
            True if on 2FA page
        """
        try:
            # Look for 2FA code input
            code_input = await page.query_selector('input[name="approvals_code"]')
            if code_input:
                logger.info("2fa_page_detected")
                return True
            
            # Alternative selectors
            alternative_selectors = [
                'input[placeholder*="code"]',
                'input[type="tel"]',
                '[data-testid="2fa-code-input"]'
            ]
            
            for selector in alternative_selectors:
                element = await page.query_selector(selector)
                if element:
                    logger.info("2fa_page_detected_alternative", selector=selector)
                    return True
            
            return False
            
        except Exception as e:
            logger.warning("2fa_detection_error", error=str(e))
            return False
    
    async def handle_2fa_challenge(
        self, 
        page: Page,
        max_wait_minutes: int = 5,
        retry_interval: int = 10
    ) -> bool:
        """
        Handle complete 2FA challenge flow.
        
        Args:
            page: Playwright page
            max_wait_minutes: Maximum minutes to wait for code
            retry_interval: Seconds between IMAP checks
            
        Returns:
            True if 2FA completed successfully
            
        Raises:
            FacebookAutomationError: If 2FA fails
        """
        try:
            logger.info("2fa_challenge_start")
            
            # Step 1: Detect 2FA page
            if not await self.detect_2fa_page(page):
                logger.warning("not_on_2fa_page")
                return False
            
            # Step 2: Get code from email
            code = await self._wait_for_code(max_wait_minutes, retry_interval)
            
            if not code:
                raise TwoFactorCodeNotFoundError("2FA code not found in email")
            
            logger.info("2fa_code_received", code=code)
            
            # Step 3: Fill code
            code_input = await page.wait_for_selector(
                'input[name="approvals_code"]',
                timeout=5000
            )
            await code_input.fill(str(code))
            await asyncio.sleep(0.5)
            
            # Step 4: Submit code
            submit_button = await page.wait_for_selector(
                'button[name="submit[Submit Code]"], button[type="submit"]',
                timeout=5000
            )
            await submit_button.click()
            
            logger.info("2fa_code_submitted")
            await asyncio.sleep(3)
            
            # Step 5: Handle "Continue" prompts
            await self._handle_continue_prompts(page)
            
            # Step 6: Handle "This was me" confirmation
            await self._handle_this_was_me(page)
            
            # Step 7: Handle "Save browser" prompt
            await self._handle_save_browser(page)
            
            # Step 8: Handle final confirmation
            await self._handle_final_confirmation(page)
            
            logger.info("2fa_challenge_completed")
            return True
            
        except Exception as e:
            logger.error("2fa_challenge_failed", error=str(e))
            raise FacebookAutomationError(f"2FA challenge failed: {str(e)}")
    
    async def _wait_for_code(
        self, 
        max_minutes: int,
        retry_interval: int
    ) -> Optional[str]:
        """
        Wait for 2FA code from email.
        
        Args:
            max_minutes: Maximum minutes to wait
            retry_interval: Seconds between checks
            
        Returns:
            2FA code or None
        """
        max_attempts = (max_minutes * 60) // retry_interval
        
        for attempt in range(max_attempts):
            logger.info("checking_for_code", attempt=attempt + 1)
            
            try:
                code = await self.imap_client.find_latest_code(
                    search_minutes=max_minutes,
                    code_length=6  # Facebook uses 6-digit codes
                )
                
                if code:
                    return code
                
            except Exception as e:
                logger.warning("code_check_failed", error=str(e))
            
            await asyncio.sleep(retry_interval)
        
        return None
    
    async def _handle_continue_prompts(self, page: Page) -> None:
        """Handle Continue button prompts."""
        try:
            continue_selectors = [
                'button[name="submit[Continue]"]',
                'button:has-text("Continue")',
                'button:has-text("Kontynuuj")'
            ]
            
            for selector in continue_selectors:
                try:
                    button = await page.wait_for_selector(selector, timeout=3000)
                    if button:
                        await button.click()
                        logger.info("continue_clicked")
                        await asyncio.sleep(2)
                        break
                except Exception:
                    continue
                    
        except Exception as e:
            logger.debug("no_continue_prompt", error=str(e))
    
    async def _handle_this_was_me(self, page: Page) -> None:
        """Handle 'This was me' confirmation."""
        try:
            this_was_me_selectors = [
                'button[name="submit[This was me]"]',
                'button:has-text("This was me")',
                'button:has-text("To byłem ja")'
            ]
            
            for selector in this_was_me_selectors:
                try:
                    button = await page.wait_for_selector(selector, timeout=3000)
                    if button:
                        await button.click()
                        logger.info("this_was_me_clicked")
                        await asyncio.sleep(2)
                        break
                except Exception:
                    continue
                    
        except Exception as e:
            logger.debug("no_this_was_me_prompt", error=str(e))
    
    async def _handle_save_browser(self, page: Page) -> None:
        """Handle save browser prompt."""
        try:
            save_selectors = [
                'button[name="submit[Continue]"]',
                'button:has-text("Save")',
                'button:has-text("Don\'t Save")',
                'button:has-text("Nie zapisuj")'
            ]
            
            for selector in save_selectors:
                try:
                    button = await page.wait_for_selector(selector, timeout=3000)
                    if button:
                        await button.click()
                        logger.info("save_browser_handled")
                        await asyncio.sleep(2)
                        break
                except Exception:
                    continue
                    
        except Exception as e:
            logger.debug("no_save_browser_prompt", error=str(e))
    
    async def _handle_final_confirmation(self, page: Page) -> None:
        """Handle final confirmation button."""
        try:
            confirm_selectors = [
                'button[name="__CONFIRM__"]',
                'button:has-text("OK")',
                'button:has-text("Confirm")',
                'button:has-text("Potwierdź")'
            ]
            
            for selector in confirm_selectors:
                try:
                    button = await page.wait_for_selector(selector, timeout=3000)
                    if button:
                        await button.click()
                        logger.info("final_confirmation_clicked")
                        await asyncio.sleep(2)
                        break
                except Exception:
                    continue
                    
        except Exception as e:
            logger.debug("no_final_confirmation", error=str(e))
    
    async def extract_access_token(self, page: Page) -> Optional[str]:
        """
        Extract access token from page URL or content.
        
        Args:
            page: Playwright page
            
        Returns:
            Access token or None
        """
        try:
            # Wait for redirect
            await asyncio.sleep(2)
            
            # Check URL for token
            current_url = page.url
            token_match = re.search(r'access_token=([\w\d]+)', current_url)
            
            if token_match:
                token = token_match.group(1)
                logger.info("access_token_extracted", token_length=len(token))
                return token
            
            # Check page content
            content = await page.content()
            token_match = re.search(r'access_token["\']?\s*[:=]\s*["\']?([\w\d]+)', content)
            
            if token_match:
                token = token_match.group(1)
                logger.info("access_token_extracted_from_content", token_length=len(token))
                return token
            
            logger.warning("access_token_not_found")
            return None
            
        except Exception as e:
            logger.error("token_extraction_failed", error=str(e))
            return None
    
    async def login_with_2fa(
        self,
        page: Page,
        email: str,
        password: str
    ) -> Optional[str]:
        """
        Complete Facebook login with 2FA.
        
        Args:
            page: Playwright page
            email: Facebook email
            password: Facebook password
            
        Returns:
            Access token or None
            
        Raises:
            FacebookAutomationError: If login fails
        """
        try:
            # Navigate to OAuth URL
            oauth_url = self.get_oauth_url()
            await page.goto(oauth_url, wait_until="networkidle")
            await asyncio.sleep(2)
            
            # Fill email
            email_input = await page.wait_for_selector('input[name="email"], input[type="email"]', timeout=10000)
            await email_input.fill(email)
            await asyncio.sleep(0.5)
            
            # Fill password
            password_input = await page.wait_for_selector('input[name="pass"], input[type="password"]', timeout=10000)
            await password_input.fill(password)
            await asyncio.sleep(0.5)
            
            # Click login
            login_button = await page.wait_for_selector('button[name="login"], button[type="submit"]', timeout=10000)
            await login_button.click()
            
            await asyncio.sleep(3)
            
            # Check if 2FA is required
            if await self.detect_2fa_page(page):
                logger.info("2fa_required")
                await self.handle_2fa_challenge(page)
            
            # Extract token
            token = await self.extract_access_token(page)
            
            if token:
                logger.info("facebook_login_success")
                return token
            else:
                raise FacebookAutomationError("Login succeeded but token not found")
                
        except Exception as e:
            logger.error("facebook_login_failed", error=str(e))
            raise FacebookAutomationError(f"Facebook login failed: {str(e)}")
