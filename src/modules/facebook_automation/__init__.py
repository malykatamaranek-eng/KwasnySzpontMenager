"""Facebook automation module using Playwright.

This module provides automated Facebook interactions including:
- Password reset automation
- Login management with 2FA support
- Security actions (logout sessions, privacy settings)
- Messenger management (calls, auto-reply, threads)

All actions simulate human behavior with random delays and mouse movements.
"""

from src.modules.facebook_automation.browser_launcher import BrowserLauncher
from src.modules.facebook_automation.login_manager import LoginManager
from src.modules.facebook_automation.messenger_manager import MessengerManager
from src.modules.facebook_automation.models import (
    BrowserConfig,
    LoginResult,
    ResetPasswordResult,
    SecurityAction,
    SecurityActionResult,
)
from src.modules.facebook_automation.reset_password import PasswordResetter
from src.modules.facebook_automation.security_actions import SecurityActionsManager
from src.modules.facebook_automation.utils import (
    extract_cookies,
    human_type,
    move_mouse_randomly,
    random_delay,
    take_screenshot_on_error,
    wait_for_navigation_complete,
)

__all__ = [
    "BrowserLauncher",
    "BrowserConfig",
    "LoginManager",
    "LoginResult",
    "MessengerManager",
    "PasswordResetter",
    "ResetPasswordResult",
    "SecurityAction",
    "SecurityActionResult",
    "SecurityActionsManager",
    "extract_cookies",
    "human_type",
    "move_mouse_randomly",
    "random_delay",
    "take_screenshot_on_error",
    "wait_for_navigation_complete",
]
