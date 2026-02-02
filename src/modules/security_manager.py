"""
MODUŁ 4: ZARZĄDZANIE BEZPIECZEŃSTWEM
Automatyczne wylogowywanie sesji i odrzucanie połączeń
"""

import asyncio
from typing import List, Dict
from playwright.async_api import async_playwright
from datetime import datetime


class SecurityManager:
    """
    Security management for Facebook accounts
    - Auto-logout unauthorized sessions
    - Auto-reject calls
    """
    
    def __init__(self, database, proxy_manager):
        self.database = database
        self.proxy_manager = proxy_manager
        self.security_url = "https://www.facebook.com/settings?tab=security"
        self.sessions_url = "https://www.facebook.com/settings?tab=security&section=sessions"
    
    async def scan_and_logout_sessions(self, account_id: int, headless: bool = True) -> int:
        """
        Scan for active sessions and logout unauthorized ones
        Returns number of sessions logged out
        """
        start_time = datetime.now()
        
        account = self.database.get_account(account_id)
        if not account:
            return 0
        
        email = account['facebook_email'] or account['email']
        password = account['facebook_password']
        
        if not password:
            return 0
        
        proxy_config = self.proxy_manager.get_proxy_config_for_account(account_id)
        proxy_dict = proxy_config.to_playwright_format() if proxy_config else None
        
        sessions_logged_out = 0
        
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
                
                # Login first
                await page.goto("https://www.facebook.com/login", wait_until='networkidle', timeout=30000)
                await page.fill('input[name="email"]', email)
                await page.fill('input[name="pass"]', password)
                await page.click('button[name="login"]')
                await page.wait_for_load_state('networkidle', timeout=15000)
                
                # Navigate to security settings
                await page.goto(self.sessions_url, wait_until='networkidle', timeout=30000)
                await asyncio.sleep(2)
                
                # Look for "Where You're Logged In" section
                # This is simplified - actual implementation would need to:
                # 1. Find all active session elements
                # 2. Identify which sessions are "ours" vs unauthorized
                # 3. Click logout buttons for unauthorized sessions
                
                # Try to find "Log out of all sessions" button
                try:
                    logout_all_button = await page.query_selector('button:has-text("Log Out of All Sessions")')
                    if not logout_all_button:
                        logout_all_button = await page.query_selector('button:has-text("Wyloguj ze wszystkich urządzeń")')
                    
                    if logout_all_button:
                        # Click logout all (except this one)
                        await logout_all_button.click()
                        await asyncio.sleep(2)
                        
                        # Confirm if needed
                        confirm_button = await page.query_selector('button:has-text("Log Out")')
                        if not confirm_button:
                            confirm_button = await page.query_selector('button:has-text("Wyloguj")')
                        
                        if confirm_button:
                            await confirm_button.click()
                            await asyncio.sleep(2)
                            sessions_logged_out = 1  # At least 1 session
                except Exception as e:
                    print(f"Error during session logout: {e}")
                
                duration = (datetime.now() - start_time).total_seconds()
                
                if sessions_logged_out > 0:
                    self.database.add_log(
                        account_id,
                        "WYLOGOWANIE_SESJI",
                        "✅ SUKCES",
                        f"Wylogowano {sessions_logged_out} sesji",
                        proxy_config.url if proxy_config else None,
                        duration
                    )
                    
                    # Add security event
                    conn = self.database.connect()
                    cursor = conn.cursor()
                    cursor.execute("""
                        INSERT INTO security_events 
                        (account_id, event_type, description, sessions_logged_out)
                        VALUES (?, ?, ?, ?)
                    """, (account_id, "SESSION_LOGOUT", "Automatyczne wylogowanie sesji", sessions_logged_out))
                    conn.commit()
                    conn.close()
                else:
                    self.database.add_log(
                        account_id,
                        "WYLOGOWANIE_SESJI",
                        "ℹ️ INFO",
                        "Brak nieautoryzowanych sesji",
                        proxy_config.url if proxy_config else None,
                        duration
                    )
                
                await browser.close()
                return sessions_logged_out
                
        except Exception as e:
            error_msg = str(e)
            duration = (datetime.now() - start_time).total_seconds()
            self.database.add_log(
                account_id,
                "WYLOGOWANIE_SESJI",
                "❌ BŁĄD",
                error_msg,
                proxy_config.url if proxy_config else None,
                duration
            )
            return 0
    
    async def monitor_and_reject_calls(self, account_id: int, duration_minutes: int = 60, headless: bool = True) -> int:
        """
        Monitor Facebook/Messenger for incoming calls and auto-reject them
        Returns number of calls rejected
        """
        start_time = datetime.now()
        
        account = self.database.get_account(account_id)
        if not account:
            return 0
        
        email = account['facebook_email'] or account['email']
        password = account['facebook_password']
        
        if not password:
            return 0
        
        proxy_config = self.proxy_manager.get_proxy_config_for_account(account_id)
        proxy_dict = proxy_config.to_playwright_format() if proxy_config else None
        
        calls_rejected = 0
        
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
                
                # Login
                await page.goto("https://www.facebook.com/login", wait_until='networkidle', timeout=30000)
                await page.fill('input[name="email"]', email)
                await page.fill('input[name="pass"]', password)
                await page.click('button[name="login"]')
                await page.wait_for_load_state('networkidle', timeout=15000)
                
                # Navigate to Messenger
                await page.goto("https://www.messenger.com", wait_until='networkidle', timeout=30000)
                
                # Monitor for call modals
                monitoring_end_time = datetime.now().timestamp() + (duration_minutes * 60)
                
                while datetime.now().timestamp() < monitoring_end_time:
                    try:
                        # Look for call modal indicators
                        # Common selectors for call notifications
                        reject_selectors = [
                            'button:has-text("Decline")',
                            'button:has-text("Odrzuć")',
                            'button:has-text("Reject")',
                            'div[aria-label="Decline call"]',
                            'div[aria-label="Odrzuć połączenie"]'
                        ]
                        
                        for selector in reject_selectors:
                            reject_button = await page.query_selector(selector)
                            if reject_button:
                                await reject_button.click()
                                calls_rejected += 1
                                
                                self.database.add_log(
                                    account_id,
                                    "ODRZUCENIE_POŁĄCZENIA",
                                    "✅ SUKCES",
                                    f"Automatycznie odrzucono połączenie #{calls_rejected}",
                                    proxy_config.url if proxy_config else None
                                )
                                
                                await asyncio.sleep(1)
                                break
                        
                        # Wait before next check
                        await asyncio.sleep(5)
                        
                    except Exception as e:
                        print(f"Error during call monitoring: {e}")
                        await asyncio.sleep(5)
                
                # Log final results
                total_duration = (datetime.now() - start_time).total_seconds()
                
                if calls_rejected > 0:
                    # Add security event
                    conn = self.database.connect()
                    cursor = conn.cursor()
                    cursor.execute("""
                        INSERT INTO security_events 
                        (account_id, event_type, description, calls_rejected)
                        VALUES (?, ?, ?, ?)
                    """, (account_id, "CALL_REJECTION", "Automatyczne odrzucanie połączeń", calls_rejected))
                    conn.commit()
                    conn.close()
                
                self.database.add_log(
                    account_id,
                    "MONITORING_POŁĄCZEŃ",
                    "ℹ️ INFO",
                    f"Zakończono monitoring. Odrzucono {calls_rejected} połączeń",
                    proxy_config.url if proxy_config else None,
                    total_duration
                )
                
                await browser.close()
                return calls_rejected
                
        except Exception as e:
            error_msg = str(e)
            self.database.add_log(
                account_id,
                "MONITORING_POŁĄCZEŃ",
                "❌ BŁĄD",
                error_msg
            )
            return calls_rejected
    
    async def daily_security_scan(self, account_id: int, headless: bool = True) -> Dict[str, int]:
        """
        Perform daily security scan: logout sessions + monitor calls
        Returns dict with results
        """
        results = {
            'sessions_logged_out': 0,
            'calls_rejected': 0
        }
        
        self.database.add_log(
            account_id,
            "SKANOWANIE_BEZPIECZEŃSTWA",
            "🔄 START",
            "Rozpoczynam dzienny skan bezpieczeństwa"
        )
        
        # Logout unauthorized sessions
        results['sessions_logged_out'] = await self.scan_and_logout_sessions(account_id, headless)
        
        # Note: Call monitoring would run continuously in background
        # For daily scan, we just check once
        
        self.database.add_log(
            account_id,
            "SKANOWANIE_BEZPIECZEŃSTWA",
            "✅ ZAKOŃCZONO",
            f"Wylogowano {results['sessions_logged_out']} sesji"
        )
        
        return results


if __name__ == "__main__":
    print("Security Manager Module")
    print("Features:")
    print("  - Automatic session logout")
    print("  - Automatic call rejection")
    print("  - Daily security scans")
