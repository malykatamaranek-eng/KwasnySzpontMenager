"""Login management for Facebook accounts.

This module handles Facebook login automation including:
- Credential entry with human-like behavior
- 2FA handling
- Session cookie management
- Checkpoint detection
"""

import logging
from datetime import datetime, timezone
from typing import Optional

from playwright.async_api import Browser, BrowserContext, Page
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.crud import save_facebook_cookies
from src.modules.facebook_automation.models import BrowserConfig, LoginResult
from src.modules.facebook_automation.utils import (
    check_for_checkpoint,
    extract_cookies,
    human_type,
    move_mouse_randomly,
    random_delay,
    take_screenshot_on_error,
    wait_for_navigation_complete,
)

logger = logging.getLogger(__name__)


# ==========================================
# CSS SELECTORS - REVERSE ENGINEERING REQUIRED
# ==========================================
# These selectors must be discovered by inspecting Facebook's DOM
# 1. Open https://www.facebook.com/login in browser
# 2. Open DevTools (F12)
# 3. Use inspector to find element selectors
# 4. Update the selectors below
# Note: Facebook frequently changes their DOM structure
# ==========================================

# Login page
EMAIL_INPUT_SELECTOR = 'input[name="email"]'  # VERIFY: Email input field
PASSWORD_INPUT_SELECTOR = 'input[name="pass"]'  # VERIFY: Password input field
LOGIN_BUTTON_SELECTOR = 'button[name="login"]'  # VERIFY: Login button

# 2FA page
TWO_FA_CODE_INPUT = 'input[name="approvals_code"]'  # VERIFY: 2FA code input
TWO_FA_SUBMIT_BUTTON = 'button[type="submit"]'  # VERIFY: 2FA submit button
TWO_FA_ALTERNATIVE_SELECTOR = 'a:has-text("Try another way")'  # VERIFY: Alternative 2FA link

# Login verification
LOGGED_IN_INDICATOR = '[aria-label="Account"] , [aria-label="Your profile"]'  # VERIFY: Profile icon
HOME_FEED_SELECTOR = 'div[role="main"]'  # VERIFY: Main feed container

# Error messages
ERROR_MESSAGE_SELECTOR = 'div[role="alert"]'  # VERIFY: Error alert container
INVALID_CREDENTIALS_TEXT = 'text="Wrong credentials"'  # VERIFY: Error message text


class LoginManager:
    """Manages Facebook login automation.
    
    Handles the complete login flow including credential entry,
    2FA verification, cookie management, and error handling.
    """
    
    def __init__(self, browser: Browser, context: BrowserContext):
        """Initialize login manager.
        
        Args:
            browser: Playwright browser instance
            context: Playwright browser context
        """
        self.browser = browser
        self.context = context
        self.page: Optional[Page] = None
    
    async def login(
        self,
        email: str,
        password: str,
        two_fa_code: Optional[str] = None,
        facebook_account_id: Optional[int] = None,
        db_session: Optional[AsyncSession] = None
    ) -> LoginResult:
        """Login to Facebook account.
        
        Args:
            email: Facebook account email
            password: Account password
            two_fa_code: 2FA verification code if required
            facebook_account_id: Account ID for saving cookies
            db_session: Database session for cookie persistence
            
        Returns:
            LoginResult with login outcome
        """
        logger.info(f"Starting login for: {email}")
        
        try:
            # Create new page
            self.page = await self.context.new_page()
            
            # Step 1: Navigate to login page
            await self._navigate_to_login()
            
            # Step 2: Enter credentials
            await self._enter_credentials(email, password)
            
            # Wait for navigation after login
            await random_delay(2.0, 3.0)
            
            # Step 3: Check for 2FA requirement
            requires_2fa = await self._check_2fa_required()
            
            if requires_2fa:
                if two_fa_code:
                    logger.info("2FA required - entering code")
                    await self._handle_2fa(two_fa_code)
                else:
                    logger.warning("2FA required but no code provided")
                    return LoginResult(
                        success=False,
                        two_fa_required=True,
                        error_message="2FA code required but not provided"
                    )
            
            # Step 4: Check for checkpoint
            checkpoint = await check_for_checkpoint(self.page)
            if checkpoint:
                logger.warning("Facebook checkpoint detected")
                return LoginResult(
                    success=False,
                    checkpoint_required=True,
                    error_message="Facebook security checkpoint detected"
                )
            
            # Step 5: Verify login success
            login_successful = await self._verify_login()
            
            if login_successful:
                logger.info("Login successful")
                
                # Extract cookies
                cookies = await extract_cookies(self.context)
                
                # Save cookies to database if account ID provided
                if facebook_account_id and db_session and cookies:
                    await save_facebook_cookies(
                        db_session,
                        facebook_account_id,
                        cookies
                    )
                    logger.info("Cookies saved to database")
                
                # Get session data
                session_data = await self._extract_session_data()
                
                return LoginResult(
                    success=True,
                    session_data=session_data,
                    cookies=cookies
                )
            else:
                # Check for error message
                error_message = await self._get_error_message()
                
                logger.error(f"Login failed: {error_message}")
                return LoginResult(
                    success=False,
                    error_message=error_message or "Login verification failed"
                )
        
        except Exception as e:
            logger.error(f"Login failed with exception: {e}")
            
            # Take screenshot for debugging
            if self.page:
                await take_screenshot_on_error(
                    self.page,
                    f"login_error_{email.split('@')[0]}.png"
                )
            
            return LoginResult(
                success=False,
                error_message=str(e)
            )
        
        finally:
            if self.page:
                await self.page.close()
    
    async def _navigate_to_login(self) -> None:
        """Navigate to Facebook login page."""
        logger.info("Navigating to login page")
        
        if not self.page:
            raise RuntimeError("Page not initialized")
        
        await self.page.goto(
            "https://www.facebook.com/login",
            wait_until="networkidle"
        )
        await random_delay(1.0, 2.0)
        
        # Random mouse movement for human behavior
        await move_mouse_randomly(self.page)
        
        logger.debug("Login page loaded")
    
    async def _enter_credentials(self, email: str, password: str) -> None:
        """Enter email and password with human-like behavior.
        
        Args:
            email: Account email
            password: Account password
        """
        logger.info("Entering credentials")
        
        if not self.page:
            raise RuntimeError("Page not initialized")
        
        # Wait for email input
        email_input = await self.page.wait_for_selector(
            EMAIL_INPUT_SELECTOR,
            timeout=10000
        )
        
        # Type email with human-like delays
        await human_type(self.page, EMAIL_INPUT_SELECTOR, email, delay_ms=120)
        await random_delay(0.5, 1.0)
        
        # Random mouse movement
        await move_mouse_randomly(self.page, movements=2)
        
        # Type password
        await human_type(self.page, PASSWORD_INPUT_SELECTOR, password, delay_ms=100)
        await random_delay(1.0, 2.0)
        
        # Click login button
        login_button = await self.page.wait_for_selector(LOGIN_BUTTON_SELECTOR)
        await login_button.click()
        
        # Wait for navigation
        await wait_for_navigation_complete(self.page, timeout=30000)
        
        logger.debug("Credentials submitted")
    
    async def _check_2fa_required(self) -> bool:
        """Check if 2FA verification is required.
        
        Returns:
            True if 2FA required, False otherwise
        """
        logger.debug("Checking for 2FA requirement")
        
        if not self.page:
            raise RuntimeError("Page not initialized")
        
        try:
            # Look for 2FA input field
            two_fa_input = await self.page.wait_for_selector(
                TWO_FA_CODE_INPUT,
                timeout=5000
            )
            
            if two_fa_input:
                logger.info("2FA input detected")
                return True
                
        except Exception:
            logger.debug("No 2FA input found")
        
        return False
    
    async def _handle_2fa(self, code: str) -> None:
        """Handle 2FA verification.
        
        Args:
            code: 2FA verification code
        """
        logger.info("Handling 2FA verification")
        
        if not self.page:
            raise RuntimeError("Page not initialized")
        
        await random_delay(1.0, 2.0)
        
        # Type 2FA code
        await human_type(self.page, TWO_FA_CODE_INPUT, code, delay_ms=150)
        await random_delay(0.5, 1.0)
        
        # Click submit button
        submit_button = await self.page.wait_for_selector(TWO_FA_SUBMIT_BUTTON)
        await submit_button.click()
        
        # Wait for navigation
        await wait_for_navigation_complete(self.page, timeout=30000)
        
        logger.debug("2FA code submitted")
    
    async def _verify_login(self) -> bool:
        """Verify that login was successful.
        
        Returns:
            True if logged in, False otherwise
        """
        logger.info("Verifying login status")
        
        if not self.page:
            raise RuntimeError("Page not initialized")
        
        await random_delay(1.0, 2.0)
        
        # Check for logged-in indicators
        try:
            # Look for profile icon or home feed
            logged_in = await self.page.wait_for_selector(
                LOGGED_IN_INDICATOR,
                timeout=10000
            )
            
            if logged_in:
                logger.info("Login verified - profile icon found")
                return True
                
        except Exception:
            logger.debug("Profile icon not found")
        
        # Check if on home feed
        try:
            home_feed = await self.page.wait_for_selector(
                HOME_FEED_SELECTOR,
                timeout=5000
            )
            
            if home_feed:
                logger.info("Login verified - home feed found")
                return True
                
        except Exception:
            logger.debug("Home feed not found")
        
        # Check URL - if not on login page anymore, likely successful
        current_url = self.page.url
        # Proper domain validation: check if URL starts with Facebook domain
        if (current_url.startswith("https://www.facebook.com") or 
            current_url.startswith("https://facebook.com")) and "/login" not in current_url:
            logger.info("Login verified - redirected from login page")
            return True
        
        logger.warning("Could not verify login status")
        return False
    
    async def _get_error_message(self) -> Optional[str]:
        """Extract error message from page.
        
        Returns:
            Error message text or None if no error
        """
        if not self.page:
            return None
        
        try:
            error_element = await self.page.wait_for_selector(
                ERROR_MESSAGE_SELECTOR,
                timeout=3000
            )
            
            if error_element:
                error_text = await error_element.inner_text()
                return error_text
                
        except Exception:
            logger.debug("No error message found")
        
        return None
    
    async def _extract_session_data(self) -> dict:
        """Extract session data from logged-in page.
        
        Returns:
            Dictionary with session information
        """
        if not self.page:
            return {}
        
        try:
            # Get user ID from page
            user_id = await self.page.evaluate("""
                () => {
                    const element = document.querySelector('[data-testid="blue_bar_profile_link"]');
                    if (element && element.href) {
                        const match = element.href.match(/\\/profile\\.php\\?id=(\\d+)/);
                        return match ? match[1] : null;
                    }
                    return null;
                }
            """)
            
            return {
                "user_id": user_id,
                "url": self.page.url,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            
        except Exception as e:
            logger.warning(f"Could not extract session data: {e}")
            return {}
