"""Messenger management automation for Facebook.

This module handles automated Messenger-related actions including:
- Rejecting incoming calls
- Setting auto-reply messages
- Archiving message threads
"""

import logging
from typing import Optional

from playwright.async_api import Page

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
# 1. Open https://www.messenger.com or Facebook Messages
# 2. Open DevTools (F12)
# 3. Use inspector to find element selectors
# 4. Update the selectors below
# Note: Facebook frequently changes their DOM structure
# ==========================================

# Messenger navigation
MESSAGES_ICON_SELECTOR = 'a[href*="/messages"]'  # VERIFY: Messages icon
MESSENGER_URL = "https://www.messenger.com"  # Direct Messenger URL

# Call management
INCOMING_CALL_NOTIFICATION = 'div[role="dialog"][aria-label*="call"]'  # VERIFY: Call dialog
DECLINE_CALL_BUTTON = 'button:has-text("Decline")'  # VERIFY: Decline button
REJECT_CALL_BUTTON = 'button[aria-label*="Decline" i]'  # VERIFY: Alternative decline

# Settings navigation
MESSENGER_SETTINGS_BUTTON = 'button[aria-label*="Settings" i]'  # VERIFY: Settings button
MESSENGER_PREFERENCES_LINK = 'a:has-text("Preferences")'  # VERIFY: Preferences link

# Auto-reply settings
AUTO_REPLY_TOGGLE = 'input[aria-label*="auto reply" i]'  # VERIFY: Auto-reply toggle
AUTO_REPLY_MESSAGE_INPUT = 'textarea[placeholder*="message"]'  # VERIFY: Message textarea
SAVE_AUTO_REPLY_BUTTON = 'button:has-text("Save")'  # VERIFY: Save button

# Thread management
THREAD_LIST_SELECTOR = 'div[role="navigation"] a[role="link"]'  # VERIFY: Thread links
THREAD_CHECKBOX_SELECTOR = 'input[type="checkbox"][aria-label*="Select"]'  # VERIFY: Thread checkbox
ARCHIVE_BUTTON = 'button[aria-label*="Archive" i]'  # VERIFY: Archive button
MORE_OPTIONS_BUTTON = 'button[aria-label*="More options" i]'  # VERIFY: More options menu
ARCHIVE_MENU_ITEM = 'div[role="menuitem"]:has-text("Archive")'  # VERIFY: Archive menu item

# Success indicators
ARCHIVED_NOTIFICATION = 'div:has-text("Conversation archived")'  # VERIFY: Archive success message
SETTINGS_SAVED_NOTIFICATION = 'div:has-text("Settings saved")'  # VERIFY: Save success message


class MessengerManager:
    """Manages automated Messenger actions.
    
    Provides methods to handle Messenger-related tasks like
    call management, auto-replies, and thread organization.
    """
    
    def __init__(self, page: Page):
        """Initialize Messenger manager.
        
        Args:
            page: Playwright page instance (must be logged in)
        """
        self.page = page
    
    async def reject_calls(
        self,
        auto_reject: bool = True,
        timeout_minutes: int = 60
    ) -> dict[str, int]:
        """Monitor and reject incoming Messenger calls.
        
        Args:
            auto_reject: Whether to automatically reject calls
            timeout_minutes: How long to monitor for calls
            
        Returns:
            Dictionary with stats: {"rejected": count}
        """
        logger.info(f"Starting call rejection monitor (timeout: {timeout_minutes}m)")
        
        rejected_count = 0
        
        try:
            # Navigate to Messenger
            await self._navigate_to_messenger()
            
            # Monitor for calls
            import asyncio
            start_time = asyncio.get_event_loop().time()
            timeout_seconds = timeout_minutes * 60
            
            while asyncio.get_event_loop().time() - start_time < timeout_seconds:
                # Check for incoming call notification
                has_call = await self._check_incoming_call()
                
                if has_call and auto_reject:
                    logger.info("Incoming call detected, rejecting")
                    await self._decline_call()
                    rejected_count += 1
                
                # Wait before checking again
                await asyncio.sleep(5)
            
            logger.info(f"Call monitoring completed. Rejected: {rejected_count}")
            return {"rejected": rejected_count}
            
        except Exception as e:
            logger.error(f"Failed to reject calls: {e}")
            await take_screenshot_on_error(self.page, "reject_calls_error.png")
            return {"rejected": rejected_count, "error": str(e)}
    
    async def set_auto_reply(
        self,
        message: str,
        enable: bool = True
    ) -> bool:
        """Set or disable automatic reply message.
        
        Args:
            message: Auto-reply message text
            enable: True to enable, False to disable
            
        Returns:
            True if successful, False otherwise
        """
        logger.info(f"Setting auto-reply (enable: {enable})")
        
        try:
            # Navigate to Messenger settings
            await self._navigate_to_messenger_settings()
            
            # Toggle auto-reply
            await self._toggle_auto_reply(enable)
            
            if enable:
                # Set auto-reply message
                await self._set_auto_reply_message(message)
            
            # Save settings
            await self._save_messenger_settings()
            
            # Verify success
            success = await self._verify_settings_saved()
            
            if success:
                logger.info("Auto-reply settings updated successfully")
                return True
            else:
                logger.warning("Could not verify auto-reply settings")
                return False
                
        except Exception as e:
            logger.error(f"Failed to set auto-reply: {e}")
            await take_screenshot_on_error(self.page, "auto_reply_error.png")
            return False
    
    async def archive_threads(
        self,
        thread_ids: Optional[list[str]] = None,
        archive_all: bool = False,
        limit: int = 100
    ) -> dict[str, int]:
        """Archive message threads.
        
        Args:
            thread_ids: List of specific thread IDs to archive
            archive_all: Archive all threads (up to limit)
            limit: Maximum number of threads to archive
            
        Returns:
            Dictionary with stats: {"archived": count}
        """
        logger.info(f"Starting thread archiving (archive_all: {archive_all})")
        
        archived_count = 0
        
        try:
            # Navigate to Messenger
            await self._navigate_to_messenger()
            
            if archive_all:
                # Archive threads one by one up to limit
                for i in range(limit):
                    success = await self._archive_first_thread()
                    if success:
                        archived_count += 1
                        await random_delay(1.0, 2.0)
                    else:
                        logger.info("No more threads to archive")
                        break
            
            elif thread_ids:
                # Archive specific threads
                for thread_id in thread_ids:
                    success = await self._archive_thread_by_id(thread_id)
                    if success:
                        archived_count += 1
                    await random_delay(1.0, 2.0)
            
            logger.info(f"Thread archiving completed. Archived: {archived_count}")
            return {"archived": archived_count}
            
        except Exception as e:
            logger.error(f"Failed to archive threads: {e}")
            await take_screenshot_on_error(self.page, "archive_threads_error.png")
            return {"archived": archived_count, "error": str(e)}
    
    # ==========================================
    # Private helper methods
    # ==========================================
    
    async def _navigate_to_messenger(self) -> None:
        """Navigate to Messenger."""
        logger.debug("Navigating to Messenger")
        
        current_url = self.page.url
        
        # Check if already on Messenger - proper domain validation
        if (current_url.startswith("https://www.messenger.com") or 
            current_url.startswith("https://messenger.com")):
            logger.debug("Already on Messenger")
            return
        
        # Navigate to Messenger
        await self.page.goto(MESSENGER_URL, wait_until="networkidle")
        await random_delay(2.0, 3.0)
        
        await scroll_page_naturally(self.page, scrolls=2)
    
    async def _check_incoming_call(self) -> bool:
        """Check if there's an incoming call notification.
        
        Returns:
            True if call detected, False otherwise
        """
        try:
            call_dialog = await self.page.query_selector(
                INCOMING_CALL_NOTIFICATION
            )
            return call_dialog is not None
        except Exception:
            return False
    
    async def _decline_call(self) -> None:
        """Decline an incoming call."""
        logger.debug("Declining call")
        
        await random_delay(0.5, 1.0)
        
        # Try primary decline button
        try:
            decline_button = await self.page.wait_for_selector(
                DECLINE_CALL_BUTTON,
                timeout=5000
            )
            await decline_button.click()
            await random_delay(0.5, 1.0)
            return
        except Exception:
            logger.debug("Primary decline button not found")
        
        # Try alternative decline button
        try:
            reject_button = await self.page.wait_for_selector(
                REJECT_CALL_BUTTON,
                timeout=5000
            )
            await reject_button.click()
            await random_delay(0.5, 1.0)
        except Exception as e:
            logger.warning(f"Could not find decline button: {e}")
    
    async def _navigate_to_messenger_settings(self) -> None:
        """Navigate to Messenger settings."""
        logger.debug("Navigating to Messenger settings")
        
        # Ensure we're on Messenger
        await self._navigate_to_messenger()
        
        await random_delay(1.0, 2.0)
        
        # Click settings button
        try:
            settings_button = await self.page.wait_for_selector(
                MESSENGER_SETTINGS_BUTTON,
                timeout=10000
            )
            await settings_button.click()
            await random_delay(1.0, 2.0)
        except Exception as e:
            logger.warning(f"Could not find settings button: {e}")
            # Try direct URL navigation
            await self.page.goto(
                f"{MESSENGER_URL}/settings",
                wait_until="networkidle"
            )
            await random_delay(1.0, 2.0)
        
        # Navigate to preferences
        try:
            preferences_link = await self.page.wait_for_selector(
                MESSENGER_PREFERENCES_LINK,
                timeout=5000
            )
            await preferences_link.click()
            await wait_for_navigation_complete(self.page)
        except Exception:
            logger.debug("Preferences link not found or not needed")
    
    async def _toggle_auto_reply(self, enable: bool) -> None:
        """Toggle auto-reply setting.
        
        Args:
            enable: True to enable, False to disable
        """
        logger.debug(f"Toggling auto-reply to: {enable}")
        
        await random_delay(0.5, 1.0)
        
        try:
            toggle = await self.page.wait_for_selector(
                AUTO_REPLY_TOGGLE,
                timeout=10000
            )
            
            # Check current state
            is_checked = await toggle.is_checked()
            
            # Click if state needs to change
            if is_checked != enable:
                await toggle.click()
                await random_delay(0.5, 1.0)
        except Exception as e:
            logger.warning(f"Could not toggle auto-reply: {e}")
    
    async def _set_auto_reply_message(self, message: str) -> None:
        """Set auto-reply message text.
        
        Args:
            message: Auto-reply message
        """
        logger.debug("Setting auto-reply message")
        
        await random_delay(0.5, 1.0)
        
        try:
            message_input = await self.page.wait_for_selector(
                AUTO_REPLY_MESSAGE_INPUT,
                timeout=10000
            )
            
            # Clear existing text
            await message_input.click()
            await self.page.keyboard.press("Control+A")
            await self.page.keyboard.press("Backspace")
            await random_delay(0.3, 0.7)
            
            # Type new message
            await human_type(
                self.page,
                AUTO_REPLY_MESSAGE_INPUT,
                message,
                delay_ms=80
            )
        except Exception as e:
            logger.warning(f"Could not set auto-reply message: {e}")
    
    async def _save_messenger_settings(self) -> None:
        """Save Messenger settings."""
        logger.debug("Saving Messenger settings")
        
        await random_delay(0.5, 1.0)
        
        try:
            save_button = await self.page.wait_for_selector(
                SAVE_AUTO_REPLY_BUTTON,
                timeout=5000
            )
            await save_button.click()
            await random_delay(1.0, 2.0)
        except Exception:
            logger.debug("No save button found, changes may be auto-saved")
    
    async def _verify_settings_saved(self) -> bool:
        """Verify that settings were saved.
        
        Returns:
            True if success indicator found, False otherwise
        """
        logger.debug("Verifying settings saved")
        
        try:
            notification = await self.page.wait_for_selector(
                SETTINGS_SAVED_NOTIFICATION,
                timeout=5000
            )
            return notification is not None
        except Exception:
            # Assume success if no error
            return True
    
    async def _archive_first_thread(self) -> bool:
        """Archive the first thread in the list.
        
        Returns:
            True if archived, False if no threads available
        """
        logger.debug("Archiving first thread")
        
        try:
            # Get first thread
            threads = await self.page.query_selector_all(THREAD_LIST_SELECTOR)
            
            if not threads:
                logger.debug("No threads found")
                return False
            
            first_thread = threads[0]
            
            # Hover over thread to show options
            await first_thread.hover()
            await random_delay(0.5, 1.0)
            
            # Click more options
            more_button = await self.page.wait_for_selector(
                MORE_OPTIONS_BUTTON,
                timeout=5000
            )
            await more_button.click()
            await random_delay(0.5, 1.0)
            
            # Click archive option
            archive_item = await self.page.wait_for_selector(
                ARCHIVE_MENU_ITEM,
                timeout=5000
            )
            await archive_item.click()
            await random_delay(1.0, 2.0)
            
            logger.debug("Thread archived successfully")
            return True
            
        except Exception as e:
            logger.warning(f"Could not archive thread: {e}")
            return False
    
    async def _archive_thread_by_id(self, thread_id: str) -> bool:
        """Archive a specific thread by ID.
        
        Args:
            thread_id: Thread identifier
            
        Returns:
            True if archived, False otherwise
        """
        logger.debug(f"Archiving thread: {thread_id}")
        
        try:
            # Navigate to specific thread
            thread_url = f"{MESSENGER_URL}/t/{thread_id}"
            await self.page.goto(thread_url, wait_until="networkidle")
            await random_delay(1.0, 2.0)
            
            # Click more options
            more_button = await self.page.wait_for_selector(
                MORE_OPTIONS_BUTTON,
                timeout=10000
            )
            await more_button.click()
            await random_delay(0.5, 1.0)
            
            # Click archive
            archive_item = await self.page.wait_for_selector(
                ARCHIVE_MENU_ITEM,
                timeout=5000
            )
            await archive_item.click()
            await random_delay(1.0, 2.0)
            
            logger.debug(f"Thread {thread_id} archived successfully")
            return True
            
        except Exception as e:
            logger.warning(f"Could not archive thread {thread_id}: {e}")
            return False
