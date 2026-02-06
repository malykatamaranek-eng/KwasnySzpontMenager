"""Password reset automation for Facebook accounts.

This module automates the Facebook password reset process using email verification.
It navigates through the recovery flow, enters verification codes, and sets new passwords.
"""

import logging
from typing import Optional

from playwright.async_api import Browser, BrowserContext, Page

from src.modules.facebook_automation.models import ResetPasswordResult
from src.modules.facebook_automation.utils import (
    check_for_checkpoint,
    human_type,
    random_delay,
    take_screenshot_on_error,
    wait_for_navigation_complete,
)

logger = logging.getLogger(__name__)


# ==========================================
# CSS SELECTORS - REVERSE ENGINEERING REQUIRED
# ==========================================
# These selectors must be discovered by inspecting Facebook's DOM
# 1. Open https://www.facebook.com/login/identify in browser
# 2. Open DevTools (F12)
# 3. Use inspector to find element selectors
# 4. Update the selectors below
# Note: Facebook frequently changes their DOM structure
# ==========================================

# Account recovery page
EMAIL_INPUT_SELECTOR = 'input[name="email"]'  # VERIFY: Email/phone input field
SEARCH_BUTTON_SELECTOR = 'button[type="submit"]'  # VERIFY: Search button
NO_LONGER_ACCESS_SELECTOR = 'a:has-text("No longer have access")'  # VERIFY: Link text

# Recovery method selection
EMAIL_RECOVERY_METHOD_SELECTOR = 'input[type="radio"][value="email"]'  # VERIFY: Email radio button
CONTINUE_BUTTON_SELECTOR = 'button:has-text("Continue")'  # VERIFY: Continue button text

# Code verification
VERIFICATION_CODE_INPUT = 'input[name="code"]'  # VERIFY: Verification code input
CONFIRM_CODE_BUTTON = 'button:has-text("Continue")'  # VERIFY: Confirm code button

# Password reset
NEW_PASSWORD_INPUT = 'input[name="password_new"]'  # VERIFY: New password field
CONFIRM_PASSWORD_INPUT = 'input[name="password_confirm"]'  # VERIFY: Confirm password field
RESET_PASSWORD_BUTTON = 'button[type="submit"]'  # VERIFY: Submit button

# Success/Error indicators
SUCCESS_MESSAGE_SELECTOR = 'div:has-text("Password Changed")'  # VERIFY: Success message
ERROR_MESSAGE_SELECTOR = 'div[role="alert"]'  # VERIFY: Error message container


class PasswordResetter:
    """Handles automated Facebook password reset via email verification.
    
    This class automates the complete password reset flow:
    1. Navigate to recovery page
    2. Enter account email
    3. Select email recovery method
    4. Enter verification code from email
    5. Set new password
    """
    
    def __init__(self, browser: Browser, context: BrowserContext):
        """Initialize password resetter.
        
        Args:
            browser: Playwright browser instance
            context: Playwright browser context
        """
        self.browser = browser
        self.context = context
        self.page: Optional[Page] = None
    
    async def reset_password(
        self,
        email: str,
        current_password: str,
        new_password: str,
        email_code: Optional[str] = None,
        wait_for_code_callback: Optional[callable] = None
    ) -> ResetPasswordResult:
        """Reset Facebook account password.
        
        Args:
            email: Facebook account email
            current_password: Current password (may not be used)
            new_password: New password to set
            email_code: Verification code from email (if already received)
            wait_for_code_callback: Async callback to wait for code if not provided
            
        Returns:
            ResetPasswordResult with operation outcome
        """
        logger.info(f"Starting password reset for: {email}")
        
        try:
            # Create new page
            self.page = await self.context.new_page()
            
            # Step 1: Navigate to recovery page
            await self._navigate_to_recovery_page()
            
            # Step 2: Enter email and search
            await self._enter_email(email)
            
            # Step 3: Select email recovery method
            await self._select_email_recovery()
            
            # Step 4: Get verification code
            if not email_code:
                if wait_for_code_callback:
                    logger.info("Waiting for verification code via callback")
                    email_code = await wait_for_code_callback()
                else:
                    error_msg = "No verification code provided and no callback specified"
                    logger.error(error_msg)
                    return ResetPasswordResult(
                        success=False,
                        error_message=error_msg
                    )
            
            # Step 5: Enter verification code
            await self._enter_verification_code(email_code)
            
            # Step 6: Set new password
            await self._set_new_password(new_password)
            
            # Step 7: Verify success
            success = await self._verify_password_reset()
            
            if success:
                logger.info("Password reset completed successfully")
                return ResetPasswordResult(
                    success=True,
                    new_password=new_password
                )
            else:
                # Check for checkpoint
                checkpoint = await check_for_checkpoint(self.page)
                
                return ResetPasswordResult(
                    success=False,
                    error_message="Password reset verification failed",
                    checkpoint_required=checkpoint
                )
                
        except Exception as e:
            logger.error(f"Password reset failed: {e}")
            
            # Take screenshot for debugging
            if self.page:
                await take_screenshot_on_error(
                    self.page,
                    f"password_reset_error_{email.split('@')[0]}.png"
                )
            
            return ResetPasswordResult(
                success=False,
                error_message=str(e)
            )
        
        finally:
            if self.page:
                await self.page.close()
    
    async def _navigate_to_recovery_page(self) -> None:
        """Navigate to Facebook account recovery page."""
        logger.info("Navigating to recovery page")
        
        if not self.page:
            raise RuntimeError("Page not initialized")
        
        await self.page.goto(
            "https://www.facebook.com/login/identify",
            wait_until="networkidle"
        )
        await random_delay(1.0, 2.0)
        
        logger.debug("Recovery page loaded")
    
    async def _enter_email(self, email: str) -> None:
        """Enter email and submit search.
        
        Args:
            email: Account email address
        """
        logger.info("Entering email address")
        
        if not self.page:
            raise RuntimeError("Page not initialized")
        
        # Wait for email input field
        email_input = await self.page.wait_for_selector(
            EMAIL_INPUT_SELECTOR,
            timeout=10000
        )
        
        # Type email with human-like delays
        await human_type(self.page, EMAIL_INPUT_SELECTOR, email, delay_ms=120)
        await random_delay(0.5, 1.0)
        
        # Click search button
        search_button = await self.page.wait_for_selector(SEARCH_BUTTON_SELECTOR)
        await search_button.click()
        
        # Wait for navigation
        await wait_for_navigation_complete(self.page)
        
        logger.debug("Email submitted successfully")
    
    async def _select_email_recovery(self) -> None:
        """Select email as recovery method."""
        logger.info("Selecting email recovery method")
        
        if not self.page:
            raise RuntimeError("Page not initialized")
        
        await random_delay(1.0, 2.0)
        
        # Look for email recovery option
        try:
            email_radio = await self.page.wait_for_selector(
                EMAIL_RECOVERY_METHOD_SELECTOR,
                timeout=10000
            )
            await email_radio.click()
            await random_delay(0.5, 1.0)
            
        except Exception as e:
            logger.warning(f"Could not find email radio button: {e}")
            # May already be selected or interface different
        
        # Click continue button
        continue_button = await self.page.wait_for_selector(CONTINUE_BUTTON_SELECTOR)
        await continue_button.click()
        
        await wait_for_navigation_complete(self.page)
        
        logger.debug("Email recovery method selected")
    
    async def _enter_verification_code(self, code: str) -> None:
        """Enter email verification code.
        
        Args:
            code: Verification code from email
        """
        logger.info("Entering verification code")
        
        if not self.page:
            raise RuntimeError("Page not initialized")
        
        await random_delay(1.0, 2.0)
        
        # Wait for code input field
        code_input = await self.page.wait_for_selector(
            VERIFICATION_CODE_INPUT,
            timeout=15000
        )
        
        # Type code with human-like delays
        await human_type(self.page, VERIFICATION_CODE_INPUT, code, delay_ms=150)
        await random_delay(0.5, 1.0)
        
        # Click confirm button
        confirm_button = await self.page.wait_for_selector(CONFIRM_CODE_BUTTON)
        await confirm_button.click()
        
        await wait_for_navigation_complete(self.page)
        
        logger.debug("Verification code submitted")
    
    async def _set_new_password(self, new_password: str) -> None:
        """Set new password.
        
        Args:
            new_password: New password to set
        """
        logger.info("Setting new password")
        
        if not self.page:
            raise RuntimeError("Page not initialized")
        
        await random_delay(1.0, 2.0)
        
        # Wait for password input fields
        password_input = await self.page.wait_for_selector(
            NEW_PASSWORD_INPUT,
            timeout=10000
        )
        
        # Type new password
        await human_type(self.page, NEW_PASSWORD_INPUT, new_password, delay_ms=100)
        await random_delay(0.5, 1.0)
        
        # Type password confirmation if field exists
        try:
            await human_type(
                self.page,
                CONFIRM_PASSWORD_INPUT,
                new_password,
                delay_ms=100
            )
            await random_delay(0.5, 1.0)
        except Exception:
            logger.debug("No password confirmation field found")
        
        # Click reset button
        reset_button = await self.page.wait_for_selector(RESET_PASSWORD_BUTTON)
        await reset_button.click()
        
        await wait_for_navigation_complete(self.page)
        
        logger.debug("New password submitted")
    
    async def _verify_password_reset(self) -> bool:
        """Verify that password reset was successful.
        
        Returns:
            True if successful, False otherwise
        """
        logger.info("Verifying password reset")
        
        if not self.page:
            raise RuntimeError("Page not initialized")
        
        await random_delay(1.0, 2.0)
        
        # Check for success message
        try:
            success_element = await self.page.wait_for_selector(
                SUCCESS_MESSAGE_SELECTOR,
                timeout=5000
            )
            if success_element:
                logger.info("Password reset success message found")
                return True
        except Exception:
            logger.debug("No success message found")
        
        # Check for error message
        try:
            error_element = await self.page.wait_for_selector(
                ERROR_MESSAGE_SELECTOR,
                timeout=3000
            )
            if error_element:
                error_text = await error_element.inner_text()
                logger.error(f"Password reset error: {error_text}")
                return False
        except Exception:
            logger.debug("No error message found")
        
        # Check if we're on Facebook home page (successful login)
        current_url = self.page.url
        if "facebook.com" in current_url and "/login" not in current_url:
            logger.info("Redirected to Facebook home - password reset successful")
            return True
        
        logger.warning("Could not verify password reset status")
        return False
