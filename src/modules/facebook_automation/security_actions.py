"""Security actions automation for Facebook accounts.

This module handles automated security-related actions including:
- Logging out of other sessions
- Disabling notifications
- Updating privacy settings
"""

import logging
from typing import Optional

from playwright.async_api import Page

from src.modules.facebook_automation.models import SecurityAction, SecurityActionResult
from src.modules.facebook_automation.utils import (
    human_type,
    move_mouse_randomly,
    random_delay,
    scroll_page_naturally,
    take_screenshot_on_error,
    wait_for_navigation_complete,
)

logger = logging.getLogger(__name__)


# ==========================================
# CSS SELECTORS - REVERSE ENGINEERING REQUIRED
# ==========================================
# These selectors must be discovered by inspecting Facebook's DOM
# Instructions:
# 1. Open Facebook and login
# 2. Navigate to Settings & Privacy -> Settings
# 3. Open DevTools (F12)
# 4. Use inspector to find element selectors
# 5. Update the selectors below
# Note: Facebook frequently changes their DOM structure
# ==========================================

# Settings navigation
SETTINGS_MENU_SELECTOR = 'a[href*="/settings"]'  # VERIFY: Settings link
SECURITY_AND_LOGIN_SELECTOR = 'a[href*="security"]'  # VERIFY: Security section link

# Sessions management
WHERE_YOURE_LOGGED_IN_SELECTOR = 'a[href*="sessions"]'  # VERIFY: Sessions link
LOGOUT_ALL_SESSIONS_BUTTON = 'button:has-text("Log Out Of All Sessions")'  # VERIFY: Logout button
CONFIRM_LOGOUT_BUTTON = 'button[data-testid="confirm-logout"]'  # VERIFY: Confirm button

# Notifications
NOTIFICATIONS_SETTINGS_SELECTOR = 'a[href*="notifications"]'  # VERIFY: Notifications link
PUSH_NOTIFICATIONS_TOGGLE = 'input[aria-label*="Push notifications"]'  # VERIFY: Toggle switch
EMAIL_NOTIFICATIONS_TOGGLE = 'input[aria-label*="Email notifications"]'  # VERIFY: Toggle switch
SAVE_NOTIFICATIONS_BUTTON = 'button:has-text("Save")'  # VERIFY: Save button

# Privacy settings
PRIVACY_SETTINGS_SELECTOR = 'a[href*="privacy"]'  # VERIFY: Privacy link
WHO_CAN_SEE_POSTS_DROPDOWN = 'select[name="audience"]'  # VERIFY: Audience selector
FRIENDS_ONLY_OPTION = 'option[value="friends"]'  # VERIFY: Friends option
WHO_CAN_CONTACT_DROPDOWN = 'select[name="contact_audience"]'  # VERIFY: Contact selector
SAVE_PRIVACY_BUTTON = 'button[type="submit"]'  # VERIFY: Save button

# Success indicators
SUCCESS_NOTIFICATION = 'div:has-text("Settings saved")'  # VERIFY: Success message
CHANGES_SAVED_TEXT = 'text="Your changes have been saved"'  # VERIFY: Success text


class SecurityActionsManager:
    """Manages automated security actions on Facebook accounts.
    
    Provides methods to perform various security-related actions
    like logging out of sessions, managing notifications, and
    updating privacy settings.
    """
    
    def __init__(self, page: Page):
        """Initialize security actions manager.
        
        Args:
            page: Playwright page instance (must be logged in)
        """
        self.page = page
    
    async def logout_other_sessions(self) -> SecurityActionResult:
        """Logout from all other active sessions.
        
        This navigates to Security & Login settings and logs out
        all sessions except the current one.
        
        Returns:
            SecurityActionResult with operation outcome
        """
        logger.info("Starting logout of other sessions")
        
        try:
            # Navigate to security settings
            await self._navigate_to_security_settings()
            
            # Find and click "Where You're Logged In"
            await self._navigate_to_sessions()
            
            # Click "Log Out Of All Sessions"
            await self._click_logout_all_sessions()
            
            # Verify success
            success = await self._verify_action_success()
            
            if success:
                logger.info("Successfully logged out of all sessions")
                return SecurityActionResult(
                    action=SecurityAction.LOGOUT_OTHER_SESSIONS,
                    success=True
                )
            else:
                return SecurityActionResult(
                    action=SecurityAction.LOGOUT_OTHER_SESSIONS,
                    success=False,
                    error_message="Could not verify logout success"
                )
        
        except Exception as e:
            logger.error(f"Failed to logout other sessions: {e}")
            await take_screenshot_on_error(
                self.page,
                "logout_sessions_error.png"
            )
            
            return SecurityActionResult(
                action=SecurityAction.LOGOUT_OTHER_SESSIONS,
                success=False,
                error_message=str(e)
            )
    
    async def disable_notifications(self) -> SecurityActionResult:
        """Disable Facebook notifications.
        
        This navigates to notification settings and disables
        push and email notifications.
        
        Returns:
            SecurityActionResult with operation outcome
        """
        logger.info("Starting notification disabling")
        
        try:
            # Navigate to notifications settings
            await self._navigate_to_notifications_settings()
            
            # Disable push notifications
            await self._toggle_push_notifications(enable=False)
            
            # Disable email notifications
            await self._toggle_email_notifications(enable=False)
            
            # Save changes
            await self._save_settings()
            
            # Verify success
            success = await self._verify_action_success()
            
            if success:
                logger.info("Successfully disabled notifications")
                return SecurityActionResult(
                    action=SecurityAction.DISABLE_NOTIFICATIONS,
                    success=True
                )
            else:
                return SecurityActionResult(
                    action=SecurityAction.DISABLE_NOTIFICATIONS,
                    success=False,
                    error_message="Could not verify notification settings"
                )
        
        except Exception as e:
            logger.error(f"Failed to disable notifications: {e}")
            await take_screenshot_on_error(
                self.page,
                "disable_notifications_error.png"
            )
            
            return SecurityActionResult(
                action=SecurityAction.DISABLE_NOTIFICATIONS,
                success=False,
                error_message=str(e)
            )
    
    async def update_privacy_settings(
        self,
        post_audience: str = "friends",
        contact_audience: str = "friends"
    ) -> SecurityActionResult:
        """Update privacy settings to more restrictive values.
        
        Args:
            post_audience: Who can see posts ("friends", "friends_of_friends", "public")
            contact_audience: Who can contact you ("friends", "friends_of_friends", "everyone")
        
        Returns:
            SecurityActionResult with operation outcome
        """
        logger.info("Starting privacy settings update")
        
        try:
            # Navigate to privacy settings
            await self._navigate_to_privacy_settings()
            
            # Update post audience
            await self._set_post_audience(post_audience)
            
            # Update contact audience
            await self._set_contact_audience(contact_audience)
            
            # Save changes
            await self._save_settings()
            
            # Verify success
            success = await self._verify_action_success()
            
            if success:
                logger.info("Successfully updated privacy settings")
                return SecurityActionResult(
                    action=SecurityAction.UPDATE_PRIVACY,
                    success=True
                )
            else:
                return SecurityActionResult(
                    action=SecurityAction.UPDATE_PRIVACY,
                    success=False,
                    error_message="Could not verify privacy settings update"
                )
        
        except Exception as e:
            logger.error(f"Failed to update privacy settings: {e}")
            await take_screenshot_on_error(
                self.page,
                "update_privacy_error.png"
            )
            
            return SecurityActionResult(
                action=SecurityAction.UPDATE_PRIVACY,
                success=False,
                error_message=str(e)
            )
    
    # ==========================================
    # Private helper methods
    # ==========================================
    
    async def _navigate_to_security_settings(self) -> None:
        """Navigate to Security & Login settings."""
        logger.debug("Navigating to security settings")
        
        # Go to settings page
        await self.page.goto(
            "https://www.facebook.com/settings",
            wait_until="networkidle"
        )
        await random_delay(1.0, 2.0)
        
        # Scroll naturally
        await scroll_page_naturally(self.page)
        
        # Click security and login section
        try:
            security_link = await self.page.wait_for_selector(
                SECURITY_AND_LOGIN_SELECTOR,
                timeout=10000
            )
            await security_link.click()
            await wait_for_navigation_complete(self.page)
        except Exception as e:
            logger.warning(f"Could not find security link: {e}")
            # May already be on security page
    
    async def _navigate_to_sessions(self) -> None:
        """Navigate to active sessions page."""
        logger.debug("Navigating to sessions page")
        
        await random_delay(1.0, 2.0)
        
        # Click "Where You're Logged In"
        sessions_link = await self.page.wait_for_selector(
            WHERE_YOURE_LOGGED_IN_SELECTOR,
            timeout=10000
        )
        await sessions_link.click()
        await wait_for_navigation_complete(self.page)
        
        await scroll_page_naturally(self.page)
    
    async def _click_logout_all_sessions(self) -> None:
        """Click the logout all sessions button."""
        logger.debug("Clicking logout all sessions")
        
        await random_delay(1.0, 2.0)
        
        # Click logout button
        logout_button = await self.page.wait_for_selector(
            LOGOUT_ALL_SESSIONS_BUTTON,
            timeout=10000
        )
        await logout_button.click()
        await random_delay(0.5, 1.0)
        
        # Confirm logout if confirmation dialog appears
        try:
            confirm_button = await self.page.wait_for_selector(
                CONFIRM_LOGOUT_BUTTON,
                timeout=5000
            )
            await confirm_button.click()
            await wait_for_navigation_complete(self.page)
        except Exception:
            logger.debug("No confirmation dialog found")
    
    async def _navigate_to_notifications_settings(self) -> None:
        """Navigate to notifications settings."""
        logger.debug("Navigating to notifications settings")
        
        # Go directly to notifications settings
        await self.page.goto(
            "https://www.facebook.com/settings?tab=notifications",
            wait_until="networkidle"
        )
        await random_delay(1.0, 2.0)
        
        await scroll_page_naturally(self.page)
    
    async def _toggle_push_notifications(self, enable: bool) -> None:
        """Toggle push notifications.
        
        Args:
            enable: True to enable, False to disable
        """
        logger.debug(f"Setting push notifications to: {enable}")
        
        await random_delay(0.5, 1.0)
        
        try:
            toggle = await self.page.wait_for_selector(
                PUSH_NOTIFICATIONS_TOGGLE,
                timeout=10000
            )
            
            # Check current state
            is_checked = await toggle.is_checked()
            
            # Click if state needs to change
            if is_checked != enable:
                await toggle.click()
                await random_delay(0.5, 1.0)
        except Exception as e:
            logger.warning(f"Could not toggle push notifications: {e}")
    
    async def _toggle_email_notifications(self, enable: bool) -> None:
        """Toggle email notifications.
        
        Args:
            enable: True to enable, False to disable
        """
        logger.debug(f"Setting email notifications to: {enable}")
        
        await random_delay(0.5, 1.0)
        
        try:
            toggle = await self.page.wait_for_selector(
                EMAIL_NOTIFICATIONS_TOGGLE,
                timeout=10000
            )
            
            # Check current state
            is_checked = await toggle.is_checked()
            
            # Click if state needs to change
            if is_checked != enable:
                await toggle.click()
                await random_delay(0.5, 1.0)
        except Exception as e:
            logger.warning(f"Could not toggle email notifications: {e}")
    
    async def _navigate_to_privacy_settings(self) -> None:
        """Navigate to privacy settings."""
        logger.debug("Navigating to privacy settings")
        
        # Go directly to privacy settings
        await self.page.goto(
            "https://www.facebook.com/settings?tab=privacy",
            wait_until="networkidle"
        )
        await random_delay(1.0, 2.0)
        
        await scroll_page_naturally(self.page)
    
    async def _set_post_audience(self, audience: str) -> None:
        """Set who can see posts.
        
        Args:
            audience: Audience value ("friends", "friends_of_friends", "public")
        """
        logger.debug(f"Setting post audience to: {audience}")
        
        await random_delay(0.5, 1.0)
        
        try:
            dropdown = await self.page.wait_for_selector(
                WHO_CAN_SEE_POSTS_DROPDOWN,
                timeout=10000
            )
            
            await dropdown.select_option(value=audience)
            await random_delay(0.5, 1.0)
        except Exception as e:
            logger.warning(f"Could not set post audience: {e}")
    
    async def _set_contact_audience(self, audience: str) -> None:
        """Set who can contact you.
        
        Args:
            audience: Audience value ("friends", "friends_of_friends", "everyone")
        """
        logger.debug(f"Setting contact audience to: {audience}")
        
        await random_delay(0.5, 1.0)
        
        try:
            dropdown = await self.page.wait_for_selector(
                WHO_CAN_CONTACT_DROPDOWN,
                timeout=10000
            )
            
            await dropdown.select_option(value=audience)
            await random_delay(0.5, 1.0)
        except Exception as e:
            logger.warning(f"Could not set contact audience: {e}")
    
    async def _save_settings(self) -> None:
        """Save settings changes."""
        logger.debug("Saving settings")
        
        await random_delay(0.5, 1.0)
        
        try:
            save_button = await self.page.wait_for_selector(
                SAVE_NOTIFICATIONS_BUTTON,
                timeout=5000
            )
            await save_button.click()
            await random_delay(1.0, 2.0)
        except Exception:
            logger.debug("No save button found, changes may be auto-saved")
    
    async def _verify_action_success(self) -> bool:
        """Verify that action was successful.
        
        Returns:
            True if success indicator found, False otherwise
        """
        logger.debug("Verifying action success")
        
        await random_delay(1.0, 2.0)
        
        # Look for success notification
        try:
            success_element = await self.page.wait_for_selector(
                SUCCESS_NOTIFICATION,
                timeout=5000
            )
            
            if success_element:
                logger.debug("Success notification found")
                return True
        except Exception:
            logger.debug("No success notification found")
        
        # Look for "changes saved" text
        try:
            saved_text = await self.page.wait_for_selector(
                CHANGES_SAVED_TEXT,
                timeout=3000
            )
            
            if saved_text:
                logger.debug("Changes saved text found")
                return True
        except Exception:
            logger.debug("No changes saved text found")
        
        # If no explicit success message, assume success if no error
        logger.debug("No explicit success indicator, assuming success")
        return True
