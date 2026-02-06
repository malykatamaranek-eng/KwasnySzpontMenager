"""Utility functions for Facebook automation.

This module provides helper functions for simulating human behavior,
handling navigation, and debugging automation workflows.
"""

import asyncio
import logging
import random
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

from playwright.async_api import BrowserContext, Page

logger = logging.getLogger(__name__)


async def random_delay(min_seconds: float = 1.0, max_seconds: float = 3.0) -> None:
    """Add random delay to simulate human behavior.
    
    Args:
        min_seconds: Minimum delay in seconds
        max_seconds: Maximum delay in seconds
    """
    delay = random.uniform(min_seconds, max_seconds)
    logger.debug(f"Random delay: {delay:.2f}s")
    await asyncio.sleep(delay)


async def human_type(
    page: Page,
    selector: str,
    text: str,
    delay_ms: int = 100
) -> None:
    """Type text with human-like delays between characters.
    
    Args:
        page: Playwright page object
        selector: CSS selector for input element
        text: Text to type
        delay_ms: Base delay between keystrokes in milliseconds
        
    Raises:
        Exception: If element not found or typing fails
    """
    logger.debug(f"Human typing into {selector}: {len(text)} characters")
    
    try:
        element = await page.wait_for_selector(selector, timeout=10000)
        await element.click()
        
        for char in text:
            # Add random variation to typing speed
            char_delay = delay_ms + random.randint(-30, 50)
            await element.type(char, delay=char_delay)
            
    except Exception as e:
        logger.error(f"Failed to type into {selector}: {e}")
        raise


async def move_mouse_randomly(page: Page, movements: int = 3) -> None:
    """Perform random mouse movements to simulate human behavior.
    
    Args:
        page: Playwright page object
        movements: Number of random movements to perform
    """
    logger.debug(f"Performing {movements} random mouse movements")
    
    try:
        viewport = page.viewport_size
        if not viewport:
            return
            
        for _ in range(movements):
            x = random.randint(100, viewport["width"] - 100)
            y = random.randint(100, viewport["height"] - 100)
            await page.mouse.move(x, y)
            await asyncio.sleep(random.uniform(0.1, 0.3))
            
    except Exception as e:
        logger.warning(f"Failed to move mouse randomly: {e}")


async def wait_for_navigation_complete(
    page: Page,
    timeout: int = 30000
) -> None:
    """Wait for page navigation and loading to complete.
    
    Args:
        page: Playwright page object
        timeout: Maximum wait time in milliseconds
        
    Raises:
        Exception: If navigation fails or times out
    """
    logger.debug("Waiting for navigation to complete")
    
    try:
        # Wait for network to be idle
        await page.wait_for_load_state("networkidle", timeout=timeout)
        
        # Additional delay to ensure dynamic content loads
        await asyncio.sleep(random.uniform(0.5, 1.5))
        
        logger.debug("Navigation completed successfully")
        
    except Exception as e:
        logger.error(f"Navigation wait failed: {e}")
        raise


async def take_screenshot_on_error(
    page: Page,
    filename: Optional[str] = None,
    directory: str = "screenshots"
) -> Optional[str]:
    """Capture screenshot for debugging errors.
    
    Args:
        page: Playwright page object
        filename: Optional custom filename
        directory: Directory to save screenshots
        
    Returns:
        Path to saved screenshot or None if failed
    """
    try:
        # Create screenshots directory if it doesn't exist
        screenshots_path = Path(directory)
        screenshots_path.mkdir(parents=True, exist_ok=True)
        
        # Generate filename if not provided
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"error_{timestamp}.png"
        
        filepath = screenshots_path / filename
        await page.screenshot(path=str(filepath), full_page=True)
        
        logger.info(f"Screenshot saved: {filepath}")
        return str(filepath)
        
    except Exception as e:
        logger.error(f"Failed to take screenshot: {e}")
        return None


async def extract_cookies(context: BrowserContext) -> list[dict[str, Any]]:
    """Extract cookies from browser context.
    
    Args:
        context: Playwright browser context
        
    Returns:
        List of cookie dictionaries with name, value, domain, path, etc.
    """
    logger.debug("Extracting cookies from browser context")
    
    try:
        cookies = await context.cookies()
        logger.debug(f"Extracted {len(cookies)} cookies")
        return cookies
        
    except Exception as e:
        logger.error(f"Failed to extract cookies: {e}")
        return []


async def scroll_page_naturally(
    page: Page,
    scrolls: int = 3,
    scroll_distance: int = 300
) -> None:
    """Scroll page naturally to simulate human browsing.
    
    Args:
        page: Playwright page object
        scrolls: Number of scroll actions to perform
        scroll_distance: Pixels to scroll each time
    """
    logger.debug(f"Natural scrolling: {scrolls} times")
    
    try:
        for _ in range(scrolls):
            await page.evaluate(f"window.scrollBy(0, {scroll_distance})")
            await asyncio.sleep(random.uniform(0.5, 1.5))
            
    except Exception as e:
        logger.warning(f"Failed to scroll naturally: {e}")


async def check_for_checkpoint(page: Page) -> bool:
    """Check if Facebook checkpoint/security check is present.
    
    Args:
        page: Playwright page object
        
    Returns:
        True if checkpoint detected, False otherwise
    """
    logger.debug("Checking for Facebook checkpoint")
    
    try:
        # Check for common checkpoint indicators
        checkpoint_indicators = [
            'text="Checkpoint"',
            'text="Security Check"',
            'text="Verify Your Identity"',
            'text="Review Recent Login"',
            '[aria-label*="checkpoint" i]',
        ]
        
        for indicator in checkpoint_indicators:
            element = await page.query_selector(indicator)
            if element:
                logger.warning(f"Checkpoint detected: {indicator}")
                return True
                
        return False
        
    except Exception as e:
        logger.error(f"Error checking for checkpoint: {e}")
        return False


async def wait_for_element_with_retry(
    page: Page,
    selector: str,
    timeout: int = 10000,
    retries: int = 3
) -> Optional[Any]:
    """Wait for element with retry logic.
    
    Args:
        page: Playwright page object
        selector: CSS selector to wait for
        timeout: Timeout for each attempt in milliseconds
        retries: Number of retry attempts
        
    Returns:
        Element handle if found, None otherwise
    """
    logger.debug(f"Waiting for element: {selector} (retries: {retries})")
    
    for attempt in range(retries):
        try:
            element = await page.wait_for_selector(selector, timeout=timeout)
            logger.debug(f"Element found on attempt {attempt + 1}")
            return element
            
        except Exception as e:
            if attempt < retries - 1:
                logger.warning(f"Attempt {attempt + 1} failed, retrying...")
                await asyncio.sleep(1)
            else:
                logger.error(f"Failed to find element after {retries} attempts: {e}")
                return None
    
    return None
