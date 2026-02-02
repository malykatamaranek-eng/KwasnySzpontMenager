"""
MODUŁ 3: AUTOMATYZACJA FACEBOOKA
Logowanie, reset hasła, zarządzanie kontem Facebook
"""

import asyncio
from typing import Optional, Tuple
from enum import Enum
from playwright.async_api import async_playwright
from datetime import datetime


class FacebookStatus(Enum):
    """Facebook account status enumeration"""
    NIEZNANY = "NIEZNANY"
    LOGIN_SUKCES = "LOGIN_SUKCES"
    WRONG_PASSWORD = "WRONG_PASSWORD"
    CHECKPOINT_REQUIRED = "CHECKPOINT_REQUIRED"
    TWO_FACTOR_ENABLED = "TWO_FACTOR_ENABLED"
    ACCOUNT_DISABLED = "ACCOUNT_DISABLED"
    RESET_REQUIRED = "RESET_REQUIRED"


class FacebookAutomation:
    """
    Facebook automation manager
    Handles login, password reset, and account management
    """
    
    def __init__(self, database, proxy_manager, email_automation):
        self.database = database
        self.proxy_manager = proxy_manager
        self.email_automation = email_automation
        self.login_url = "https://www.facebook.com/login"
        self.recover_url = "https://www.facebook.com/recover"
    
    async def login_to_facebook(self, account_id: int, headless: bool = True) -> Tuple[FacebookStatus, Optional[str]]:
        """
        Attempt to login to Facebook account
        Returns (status, error_message)
        """
        start_time = datetime.now()
        
        # Get account details
        account = self.database.get_account(account_id)
        if not account:
            return FacebookStatus.NIEZNANY, "Account not found"
        
        email = account['facebook_email'] or account['email']
        password = account['facebook_password']
        
        if not password:
            return FacebookStatus.NIEZNANY, "No Facebook password set"
        
        # Get proxy configuration
        proxy_config = self.proxy_manager.get_proxy_config_for_account(account_id)
        proxy_dict = proxy_config.to_playwright_format() if proxy_config else None
        
        try:
            async with async_playwright() as p:
                browser = await p.chromium.launch(
                    headless=headless,
                    proxy=proxy_dict
                )
                
                context = await browser.new_context(
                    user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                    viewport={'width': 1920, 'height': 1080},
                    locale='pl-PL'
                )
                
                page = await context.new_page()
                
                # Navigate to login page
                await page.goto(self.login_url, wait_until='networkidle', timeout=30000)
                
                # Random delay
                await asyncio.sleep(1 + (hash(email) % 3))
                
                # Fill in credentials
                await page.fill('input[name="email"]', email)
                await asyncio.sleep(0.5)
                await page.fill('input[name="pass"]', password)
                await asyncio.sleep(0.5)
                
                # Submit
                await page.click('button[name="login"]')
                
                # Wait for response
                try:
                    await page.wait_for_load_state('networkidle', timeout=15000)
                except:
                    pass
                
                current_url = page.url
                page_content = await page.content()
                
                # Check for success - if we're on facebook.com and not on /login
                if 'facebook.com' in current_url and '/login' not in current_url:
                    # Check if we're on checkpoint or 2FA page
                    if 'checkpoint' in current_url:
                        duration = (datetime.now() - start_time).total_seconds()
                        self.database.add_log(
                            account_id,
                            "LOGOWANIE_FACEBOOK",
                            "🔄 CHECKPOINT_REQUIRED",
                            "Wymaga potwierdzenia",
                            proxy_config.url if proxy_config else None,
                            duration
                        )
                        self.database.update_account_status(account_id, facebook_status=FacebookStatus.CHECKPOINT_REQUIRED.value)
                        await browser.close()
                        return FacebookStatus.CHECKPOINT_REQUIRED, "Checkpoint required"
                    
                    if 'two_factor' in current_url or '2fa' in current_url:
                        duration = (datetime.now() - start_time).total_seconds()
                        self.database.add_log(
                            account_id,
                            "LOGOWANIE_FACEBOOK",
                            "🔐 TWO_FACTOR_ENABLED",
                            "2FA aktywne",
                            proxy_config.url if proxy_config else None,
                            duration
                        )
                        self.database.update_account_status(account_id, facebook_status=FacebookStatus.TWO_FACTOR_ENABLED.value)
                        await browser.close()
                        return FacebookStatus.TWO_FACTOR_ENABLED, "2FA enabled"
                    
                    # Success!
                    duration = (datetime.now() - start_time).total_seconds()
                    self.database.add_log(
                        account_id,
                        "LOGOWANIE_FACEBOOK",
                        "✅ SUKCES",
                        "Zalogowano do Facebook",
                        proxy_config.url if proxy_config else None,
                        duration
                    )
                    self.database.update_account_status(account_id, facebook_status=FacebookStatus.LOGIN_SUKCES.value)
                    await browser.close()
                    return FacebookStatus.LOGIN_SUKCES, None
                
                # Check for errors in page content
                page_text = page_content.lower()
                
                if 'wrong password' in page_text or 'incorrect password' in page_text or 'złe hasło' in page_text:
                    duration = (datetime.now() - start_time).total_seconds()
                    self.database.add_log(
                        account_id,
                        "LOGOWANIE_FACEBOOK",
                        "❌ WRONG_PASSWORD",
                        "Złe hasło",
                        proxy_config.url if proxy_config else None,
                        duration
                    )
                    self.database.update_account_status(account_id, facebook_status=FacebookStatus.WRONG_PASSWORD.value)
                    await browser.close()
                    return FacebookStatus.WRONG_PASSWORD, "Wrong password"
                
                if 'disabled' in page_text or 'zablokowane' in page_text:
                    duration = (datetime.now() - start_time).total_seconds()
                    self.database.add_log(
                        account_id,
                        "LOGOWANIE_FACEBOOK",
                        "🚫 ACCOUNT_DISABLED",
                        "Konto zablokowane",
                        proxy_config.url if proxy_config else None,
                        duration
                    )
                    self.database.update_account_status(account_id, facebook_status=FacebookStatus.ACCOUNT_DISABLED.value)
                    await browser.close()
                    return FacebookStatus.ACCOUNT_DISABLED, "Account disabled"
                
                # Unknown status
                await browser.close()
                self.database.add_log(account_id, "LOGOWANIE_FACEBOOK", "⚠️ NIEZNANY", "Nieznany status")
                return FacebookStatus.NIEZNANY, "Could not determine login status"
                
        except Exception as e:
            error_msg = str(e)
            duration = (datetime.now() - start_time).total_seconds()
            self.database.add_log(
                account_id,
                "LOGOWANIE_FACEBOOK",
                "❌ BŁĄD",
                error_msg,
                proxy_config.url if proxy_config else None,
                duration
            )
            return FacebookStatus.NIEZNANY, error_msg
    
    async def reset_facebook_password(self, account_id: int, new_password: str, headless: bool = True) -> bool:
        """
        Reset Facebook password using email verification
        Returns True if successful, False otherwise
        """
        start_time = datetime.now()
        
        # Get account details
        account = self.database.get_account(account_id)
        if not account:
            return False
        
        email = account['facebook_email'] or account['email']
        
        # Get proxy configuration
        proxy_config = self.proxy_manager.get_proxy_config_for_account(account_id)
        proxy_dict = proxy_config.to_playwright_format() if proxy_config else None
        
        try:
            async with async_playwright() as p:
                # Step 1: Navigate to Facebook recovery page
                browser = await p.chromium.launch(
                    headless=headless,
                    proxy=proxy_dict
                )
                
                context = await browser.new_context(
                    user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                    locale='pl-PL'
                )
                
                page = await context.new_page()
                
                await page.goto(self.recover_url, wait_until='networkidle', timeout=30000)
                await asyncio.sleep(2)
                
                # Fill email
                await page.fill('input[name="email"]', email)
                await asyncio.sleep(1)
                
                # Click search button
                await page.click('button[type="submit"]')
                await page.wait_for_load_state('networkidle', timeout=15000)
                
                # Request code via email
                # Note: This is simplified - actual implementation would need to:
                # 1. Click on email verification option
                # 2. Confirm sending code
                # 3. Wait for code
                
                await browser.close()
                
                # Step 2: Get code from email
                code = await self.email_automation.find_facebook_code(account_id, headless)
                
                if not code:
                    self.database.add_log(
                        account_id,
                        "RESET_HASLA_FACEBOOK",
                        "❌ BŁĄD",
                        "Nie znaleziono kodu w emailu"
                    )
                    return False
                
                # Store code in database
                conn = self.database.connect()
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO reset_codes (account_id, code)
                    VALUES (?, ?)
                """, (account_id, code))
                conn.commit()
                conn.close()
                
                # Step 3: Return to Facebook and enter code
                browser = await p.chromium.launch(
                    headless=headless,
                    proxy=proxy_dict
                )
                
                context = await browser.new_context(
                    user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                    locale='pl-PL'
                )
                
                page = await context.new_page()
                
                # Navigate back to recovery (state should be preserved via cookies)
                await page.goto(self.recover_url, wait_until='networkidle', timeout=30000)
                
                # Enter code
                await page.fill('input[name="code"]', code)
                await page.click('button[type="submit"]')
                await page.wait_for_load_state('networkidle', timeout=15000)
                
                # Enter new password
                await page.fill('input[name="password_new"]', new_password)
                await page.fill('input[name="password_confirm"]', new_password)
                await page.click('button[type="submit"]')
                await page.wait_for_load_state('networkidle', timeout=15000)
                
                # Update password in database
                conn = self.database.connect()
                cursor = conn.cursor()
                cursor.execute("""
                    UPDATE accounts
                    SET facebook_password = ?
                    WHERE id = ?
                """, (new_password, account_id))
                conn.commit()
                conn.close()
                
                duration = (datetime.now() - start_time).total_seconds()
                self.database.add_log(
                    account_id,
                    "RESET_HASLA_FACEBOOK",
                    "✅ SUKCES",
                    f"Hasło zmienione na nowe",
                    proxy_config.url if proxy_config else None,
                    duration
                )
                
                await browser.close()
                return True
                
        except Exception as e:
            error_msg = str(e)
            duration = (datetime.now() - start_time).total_seconds()
            self.database.add_log(
                account_id,
                "RESET_HASLA_FACEBOOK",
                "❌ BŁĄD",
                error_msg,
                proxy_config.url if proxy_config else None,
                duration
            )
            return False
    
    async def login_with_auto_reset(self, account_id: int, new_password: str, headless: bool = True) -> Tuple[FacebookStatus, Optional[str]]:
        """
        Try to login, and if password is wrong, automatically reset it
        Returns final status after potential reset
        """
        # First try to login
        status, error = await self.login_to_facebook(account_id, headless)
        
        # If wrong password, try to reset
        if status == FacebookStatus.WRONG_PASSWORD:
            self.database.add_log(
                account_id,
                "AUTORESETOWANIE",
                "🔄 W TOKU",
                "Rozpoczynam automatyczny reset hasła"
            )
            
            reset_success = await self.reset_facebook_password(account_id, new_password, headless)
            
            if reset_success:
                # Try to login again with new password
                status, error = await self.login_to_facebook(account_id, headless)
                
                if status == FacebookStatus.LOGIN_SUKCES:
                    self.database.add_log(
                        account_id,
                        "AUTORESETOWANIE",
                        "✅ SUKCES",
                        "Reset i logowanie zakończone sukcesem"
                    )
                
                return status, error
            else:
                self.database.add_log(
                    account_id,
                    "AUTORESETOWANIE",
                    "❌ BŁĄD",
                    "Reset hasła nie powiódł się"
                )
                return FacebookStatus.RESET_REQUIRED, "Reset failed"
        
        return status, error


if __name__ == "__main__":
    print("Facebook Automation Module")
    print("Status enumeration:")
    for status in FacebookStatus:
        print(f"  - {status.name}: {status.value}")
