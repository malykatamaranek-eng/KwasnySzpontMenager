"""Facebook password reset automation."""
import asyncio
import re
from typing import Optional
from playwright.async_api import Page
import structlog
from src.modules.email_processor.imap_client import AsyncIMAPProcessor
from src.core.exceptions import PasswordResetError

logger = structlog.get_logger()


class FacebookPasswordResetter:
    """
    Facebook password reset automation with:
    - Navigation to forgot password
    - Email code retrieval
    - New password setting
    - Post-reset login
    - Security session cleanup
    """
    
    def __init__(self, imap_client: AsyncIMAPProcessor):
        """
        Initialize password resetter.
        
        Args:
            imap_client: IMAP client for code retrieval
        """
        self.imap_client = imap_client
    
    async def reset_password(
        self,
        page: Page,
        email: str,
        new_password: str,
        max_wait_minutes: int = 5
    ) -> bool:
        """
        Perform complete password reset flow.
        
        Args:
            page: Playwright page
            email: Facebook email
            new_password: New password to set
            max_wait_minutes: Maximum minutes to wait for code
            
        Returns:
            True if reset successful
            
        Raises:
            PasswordResetError: If reset fails
        """
        try:
            logger.info("password_reset_start", email=email)
            
            # Step 1: Navigate to forgot password page
            await page.goto("https://m.facebook.com/login/identify/", wait_until="networkidle")
            await asyncio.sleep(2)
            
            # Step 2: Enter email
            email_input = await page.wait_for_selector(
                'input[name="email"], input[type="email"], input[placeholder*="email"]',
                timeout=10000
            )
            await email_input.fill(email)
            await asyncio.sleep(0.5)
            
            # Step 3: Click search/find button
            search_button = await page.wait_for_selector(
                'button[type="submit"], button:has-text("Search"), button:has-text("Szukaj")',
                timeout=10000
            )
            await search_button.click()
            await asyncio.sleep(3)
            
            # Step 4: Select email recovery option
            await self._select_email_recovery(page)
            
            # Step 5: Request code
            await self._request_reset_code(page)
            
            # Step 6: Wait for code
            code = await self._wait_for_reset_code(max_wait_minutes)
            
            if not code:
                raise PasswordResetError("Reset code not received")
            
            logger.info("reset_code_received", code=code)
            
            # Step 7: Enter code
            code_input = await page.wait_for_selector(
                'input[name="code"], input[type="tel"], input[placeholder*="code"]',
                timeout=10000
            )
            await code_input.fill(str(code))
            await asyncio.sleep(0.5)
            
            # Step 8: Click continue
            continue_button = await page.wait_for_selector(
                'button[type="submit"], button:has-text("Continue"), button:has-text("Kontynuuj")',
                timeout=10000
            )
            await continue_button.click()
            await asyncio.sleep(3)
            
            # Step 9: Enter new password
            await self._set_new_password(page, new_password)
            
            # Step 10: Handle security prompts
            await self._handle_security_prompts(page)
            
            logger.info("password_reset_success", email=email)
            return True
            
        except Exception as e:
            logger.error("password_reset_failed", email=email, error=str(e))
            raise PasswordResetError(f"Password reset failed: {str(e)}")
    
    async def _select_email_recovery(self, page: Page) -> None:
        """Select email as recovery method."""
        try:
            # Look for email option
            email_options = [
                'label:has-text("email")',
                'label:has-text("e-mail")',
                '[data-testid*="email"]',
                'input[type="radio"][value*="email"]'
            ]
            
            for selector in email_options:
                try:
                    option = await page.wait_for_selector(selector, timeout=3000)
                    if option:
                        await option.click()
                        logger.info("email_recovery_selected")
                        await asyncio.sleep(1)
                        return
                except Exception:
                    continue
            
            # If no radio button, might proceed automatically
            logger.info("email_recovery_auto_selected")
            
        except Exception as e:
            logger.warning("email_recovery_selection_error", error=str(e))
    
    async def _request_reset_code(self, page: Page) -> None:
        """Request reset code."""
        try:
            send_code_selectors = [
                'button:has-text("Send Code")',
                'button:has-text("Continue")',
                'button:has-text("Wyślij kod")',
                'button:has-text("Kontynuuj")',
                'button[type="submit"]'
            ]
            
            for selector in send_code_selectors:
                try:
                    button = await page.wait_for_selector(selector, timeout=3000)
                    if button:
                        await button.click()
                        logger.info("reset_code_requested")
                        await asyncio.sleep(2)
                        return
                except Exception:
                    continue
                    
        except Exception as e:
            logger.warning("request_code_error", error=str(e))
    
    async def _wait_for_reset_code(
        self,
        max_minutes: int,
        retry_interval: int = 15
    ) -> Optional[str]:
        """
        Wait for reset code from email.
        
        Args:
            max_minutes: Maximum minutes to wait
            retry_interval: Seconds between checks
            
        Returns:
            Reset code or None
        """
        max_attempts = (max_minutes * 60) // retry_interval
        
        for attempt in range(max_attempts):
            logger.info("checking_for_reset_code", attempt=attempt + 1)
            
            try:
                code = await self.imap_client.find_latest_code(
                    search_minutes=max_minutes,
                    code_length=6
                )
                
                if code:
                    return code
                
            except Exception as e:
                logger.warning("reset_code_check_failed", error=str(e))
            
            await asyncio.sleep(retry_interval)
        
        return None
    
    async def _set_new_password(self, page: Page, new_password: str) -> None:
        """Set new password."""
        try:
            # Find password input
            password_input = await page.wait_for_selector(
                'input[name="password"], input[type="password"], input[name="password_new"]',
                timeout=10000
            )
            await password_input.fill(new_password)
            await asyncio.sleep(0.5)
            
            # Check for confirm password field
            try:
                confirm_input = await page.wait_for_selector(
                    'input[name="password_confirm"], input[name="confirm_password"]',
                    timeout=3000
                )
                if confirm_input:
                    await confirm_input.fill(new_password)
                    await asyncio.sleep(0.5)
            except Exception:
                pass
            
            # Click submit
            submit_button = await page.wait_for_selector(
                'button[type="submit"], button:has-text("Continue"), button:has-text("Save")',
                timeout=10000
            )
            await submit_button.click()
            
            logger.info("new_password_set")
            await asyncio.sleep(3)
            
        except Exception as e:
            logger.error("set_password_error", error=str(e))
            raise PasswordResetError(f"Failed to set new password: {str(e)}")
    
    async def _handle_security_prompts(self, page: Page) -> None:
        """Handle post-reset security prompts."""
        try:
            # Handle "Log out of other devices"
            logout_selectors = [
                'button:has-text("Log Out")',
                'button:has-text("Wyloguj")',
                'button:has-text("Log out of other sessions")'
            ]
            
            for selector in logout_selectors:
                try:
                    button = await page.wait_for_selector(selector, timeout=3000)
                    if button:
                        await button.click()
                        logger.info("other_sessions_logged_out")
                        await asyncio.sleep(2)
                        break
                except Exception:
                    continue
            
            # Handle "Skip" or "Not now" prompts
            skip_selectors = [
                'button:has-text("Skip")',
                'button:has-text("Not Now")',
                'button:has-text("Pomiń")',
                'a:has-text("Skip")'
            ]
            
            for selector in skip_selectors:
                try:
                    button = await page.wait_for_selector(selector, timeout=3000)
                    if button:
                        await button.click()
                        logger.info("security_prompt_skipped")
                        await asyncio.sleep(2)
                        break
                except Exception:
                    continue
                    
        except Exception as e:
            logger.debug("no_security_prompts", error=str(e))
    
    async def reset_and_login(
        self,
        page: Page,
        email: str,
        old_password: str,
        new_password: str
    ) -> bool:
        """
        Reset password and login with new credentials.
        
        Args:
            page: Playwright page
            email: Facebook email
            old_password: Old password (for verification)
            new_password: New password
            
        Returns:
            True if reset and login successful
        """
        try:
            # Reset password
            await self.reset_password(page, email, new_password)
            
            # Wait a bit for reset to complete
            await asyncio.sleep(5)
            
            # Try to login with new password
            await page.goto("https://m.facebook.com/login", wait_until="networkidle")
            await asyncio.sleep(2)
            
            # Fill email
            email_input = await page.wait_for_selector('input[name="email"]', timeout=10000)
            await email_input.fill(email)
            await asyncio.sleep(0.5)
            
            # Fill new password
            password_input = await page.wait_for_selector('input[name="pass"]', timeout=10000)
            await password_input.fill(new_password)
            await asyncio.sleep(0.5)
            
            # Click login
            login_button = await page.wait_for_selector('button[name="login"]', timeout=10000)
            await login_button.click()
            await asyncio.sleep(5)
            
            # Check if logged in
            current_url = page.url
            if "login" not in current_url.lower():
                logger.info("login_with_new_password_success")
                return True
            else:
                logger.error("login_with_new_password_failed")
                return False
                
        except Exception as e:
            logger.error("reset_and_login_failed", error=str(e))
            raise PasswordResetError(f"Reset and login failed: {str(e)}")
