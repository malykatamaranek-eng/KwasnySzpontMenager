"""
MODUŁ 2: AUTOMATYZACJA POCZTY EMAIL
Auto-detekcja dostawcy i automatyczne logowanie
"""

import asyncio
from typing import Optional, Dict, Tuple
from enum import Enum
from playwright.async_api import async_playwright, Browser, Page, BrowserContext
from datetime import datetime


class EmailStatus(Enum):
    """Email account status enumeration"""
    NIEZNANY = "NIEZNANY"
    POCZTA_DZIALA = "POCZTA_DZIAŁA"
    BLEDNE_HASLO = "BŁĘDNE_HASŁO"
    KONTO_NIEISTNIEJE = "KONTO_NIEISTNIEJE"
    WYMAGANA_2FA = "WYMAGANA_2FA"
    KONTO_ZABLOKOWANE = "KONTO_ZABLOKOWANE"
    LIMIT_LOGOWAN = "LIMIT_LOGOWAŃ"


class EmailProvider:
    """Email provider configuration"""
    
    PROVIDERS = {
        'wp.pl': {
            'login_url': 'https://poczta.wp.pl/login/login.html',
            'email_selector': 'input[name="login"]',
            'password_selector': 'input[name="password"]',
            'submit_selector': 'button[type="submit"]',
            'success_indicators': ['poczta.wp.pl/k/'],
            'error_indicators': {
                'BLEDNE_HASLO': ['Nieprawidłowy login lub hasło', 'Błędny login'],
                'KONTO_NIEISTNIEJE': ['nie istnieje', 'Konto nie istnieje'],
                'KONTO_ZABLOKOWANE': ['zablokowane', 'zawieszone'],
                'WYMAGANA_2FA': ['weryfikacja', 'kod SMS', 'dwuetapowa'],
                'LIMIT_LOGOWAN': ['zbyt wiele', 'try again', 'spróbuj później']
            }
        },
        'onet.pl': {
            'login_url': 'https://konto.onet.pl/signin',
            'email_selector': 'input[name="login"]',
            'password_selector': 'input[name="password"]',
            'submit_selector': 'button[type="submit"]',
            'success_indicators': ['poczta.onet.pl'],
            'error_indicators': {
                'BLEDNE_HASLO': ['Nieprawidłowy login lub hasło'],
                'KONTO_NIEISTNIEJE': ['nie istnieje'],
                'KONTO_ZABLOKOWANE': ['zablokowane'],
                'WYMAGANA_2FA': ['weryfikacja'],
                'LIMIT_LOGOWAN': ['zbyt wiele prób']
            }
        },
        'o2.pl': {
            'login_url': 'https://1login.wp.pl/zaloguj/',
            'email_selector': 'input[name="login"]',
            'password_selector': 'input[name="password"]',
            'submit_selector': 'button[type="submit"]',
            'success_indicators': ['poczta.o2.pl'],
            'error_indicators': {
                'BLEDNE_HASLO': ['Nieprawidłowy login lub hasło'],
                'KONTO_NIEISTNIEJE': ['nie istnieje'],
                'KONTO_ZABLOKOWANE': ['zablokowane'],
                'WYMAGANA_2FA': ['weryfikacja'],
                'LIMIT_LOGOWAN': ['zbyt wiele']
            }
        },
        'tlen.pl': {
            'login_url': 'https://1login.wp.pl/zaloguj/',
            'email_selector': 'input[name="login"]',
            'password_selector': 'input[name="password"]',
            'submit_selector': 'button[type="submit"]',
            'success_indicators': ['poczta.tlen.pl'],
            'error_indicators': {
                'BLEDNE_HASLO': ['Nieprawidłowy login lub hasło'],
                'KONTO_NIEISTNIEJE': ['nie istnieje'],
                'KONTO_ZABLOKOWANE': ['zablokowane'],
                'WYMAGANA_2FA': ['weryfikacja'],
                'LIMIT_LOGOWAN': ['zbyt wiele']
            }
        },
        'interia.pl': {
            'login_url': 'https://konto.interia.pl/logowanie',
            'email_selector': 'input[name="login"]',
            'password_selector': 'input[name="password"]',
            'submit_selector': 'button[type="submit"]',
            'success_indicators': ['poczta.interia.pl'],
            'error_indicators': {
                'BLEDNE_HASLO': ['Nieprawidłowy login lub hasło'],
                'KONTO_NIEISTNIEJE': ['nie istnieje'],
                'KONTO_ZABLOKOWANE': ['zablokowane'],
                'WYMAGANA_2FA': ['weryfikacja'],
                'LIMIT_LOGOWAN': ['zbyt wiele']
            }
        }
    }
    
    @staticmethod
    def detect_provider(email: str) -> Optional[str]:
        """Detect email provider from email address"""
        if '@' not in email:
            return None
        
        domain = email.split('@')[1].lower()
        return domain if domain in EmailProvider.PROVIDERS else None
    
    @staticmethod
    def get_provider_config(domain: str) -> Optional[Dict]:
        """Get provider configuration"""
        return EmailProvider.PROVIDERS.get(domain)


class EmailAutomation:
    """
    Email automation manager
    Handles automated login to various email providers
    """
    
    def __init__(self, database, proxy_manager):
        self.database = database
        self.proxy_manager = proxy_manager
        self.browser = None
        self.context = None
    
    async def login_to_email(self, account_id: int, headless: bool = True) -> Tuple[EmailStatus, Optional[str]]:
        """
        Attempt to login to email account
        Returns (status, error_message)
        """
        start_time = datetime.now()
        
        # Get account details
        account = self.database.get_account(account_id)
        if not account:
            return EmailStatus.NIEZNANY, "Account not found"
        
        email = account['email']
        password = account['email_password']
        
        # Detect provider
        domain = EmailProvider.detect_provider(email)
        if not domain:
            error_msg = f"Unsupported email provider: {email}"
            self.database.add_log(account_id, "LOGOWANIE_POCZTA", "BŁĄD", error_msg)
            return EmailStatus.KONTO_NIEISTNIEJE, error_msg
        
        provider_config = EmailProvider.get_provider_config(domain)
        if not provider_config:
            return EmailStatus.NIEZNANY, "Provider config not found"
        
        # Get proxy configuration
        proxy_config = self.proxy_manager.get_proxy_config_for_account(account_id)
        proxy_dict = proxy_config.to_playwright_format() if proxy_config else None
        
        try:
            async with async_playwright() as p:
                # Launch browser with proxy
                browser_args = {
                    'headless': headless,
                    'proxy': proxy_dict
                }
                
                browser = await p.chromium.launch(**browser_args)
                
                # Create context with anti-detection measures
                context = await browser.new_context(
                    user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                    viewport={'width': 1920, 'height': 1080},
                    locale='pl-PL'
                )
                
                page = await context.new_page()
                
                # Navigate to login page
                await page.goto(provider_config['login_url'], wait_until='networkidle', timeout=30000)
                
                # Random delay (human-like behavior)
                await asyncio.sleep(1 + (hash(email) % 3))
                
                # Fill in credentials
                await page.fill(provider_config['email_selector'], email)
                await asyncio.sleep(0.5)
                await page.fill(provider_config['password_selector'], password)
                await asyncio.sleep(0.5)
                
                # Submit form
                await page.click(provider_config['submit_selector'])
                
                # Wait for navigation
                try:
                    await page.wait_for_load_state('networkidle', timeout=15000)
                except:
                    pass
                
                # Check current URL and page content
                current_url = page.url
                page_content = await page.content()
                
                # Check for success
                for indicator in provider_config['success_indicators']:
                    if indicator in current_url:
                        duration = (datetime.now() - start_time).total_seconds()
                        self.database.add_log(
                            account_id, 
                            "LOGOWANIE_POCZTA", 
                            "✅ SUKCES",
                            f"Zalogowano do {domain}",
                            proxy_config.url if proxy_config else None,
                            duration
                        )
                        self.database.update_account_status(account_id, email_status=EmailStatus.POCZTA_DZIALA.value)
                        
                        await browser.close()
                        return EmailStatus.POCZTA_DZIALA, None
                
                # Check for errors
                for status, indicators in provider_config['error_indicators'].items():
                    for indicator in indicators:
                        if indicator.lower() in page_content.lower():
                            duration = (datetime.now() - start_time).total_seconds()
                            self.database.add_log(
                                account_id,
                                "LOGOWANIE_POCZTA",
                                f"❌ {status}",
                                indicator,
                                proxy_config.url if proxy_config else None,
                                duration
                            )
                            
                            email_status = EmailStatus[status]
                            self.database.update_account_status(account_id, email_status=email_status.value)
                            
                            await browser.close()
                            return email_status, indicator
                
                # Unknown status
                await browser.close()
                self.database.add_log(account_id, "LOGOWANIE_POCZTA", "⚠️ NIEZNANY", "Nieznany status")
                return EmailStatus.NIEZNANY, "Could not determine login status"
                
        except Exception as e:
            error_msg = str(e)
            duration = (datetime.now() - start_time).total_seconds()
            self.database.add_log(
                account_id,
                "LOGOWANIE_POCZTA",
                "❌ BŁĄD",
                error_msg,
                proxy_config.url if proxy_config else None,
                duration
            )
            return EmailStatus.NIEZNANY, error_msg
    
    async def find_facebook_code(self, account_id: int, headless: bool = True) -> Optional[str]:
        """
        Login to email and find Facebook reset code
        Returns code if found, None otherwise
        """
        # First, ensure we're logged in
        status, _ = await self.login_to_email(account_id, headless)
        if status != EmailStatus.POCZTA_DZIALA:
            return None
        
        # Get account details
        account = self.database.get_account(account_id)
        if not account:
            return None
        
        email = account['email']
        domain = EmailProvider.detect_provider(email)
        provider_config = EmailProvider.get_provider_config(domain)
        proxy_config = self.proxy_manager.get_proxy_config_for_account(account_id)
        proxy_dict = proxy_config.to_playwright_format() if proxy_config else None
        
        try:
            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=headless, proxy=proxy_dict)
                context = await browser.new_context(
                    user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                    locale='pl-PL'
                )
                page = await context.new_page()
                
                # Navigate to inbox
                await page.goto(provider_config['login_url'], wait_until='networkidle', timeout=30000)
                
                # Login again
                await page.fill(provider_config['email_selector'], email)
                await page.fill(provider_config['password_selector'], account['email_password'])
                await page.click(provider_config['submit_selector'])
                await page.wait_for_load_state('networkidle', timeout=15000)
                
                # Look for Facebook email - this is provider-specific
                # For now, return None - full implementation would parse inbox
                
                await browser.close()
                return None
                
        except Exception as e:
            print(f"Error finding Facebook code: {e}")
            return None


if __name__ == "__main__":
    # Test email provider detection
    test_emails = [
        "test@wp.pl",
        "user@onet.pl",
        "someone@o2.pl",
        "account@interia.pl",
        "invalid@gmail.com"
    ]
    
    for email in test_emails:
        domain = EmailProvider.detect_provider(email)
        config = EmailProvider.get_provider_config(domain) if domain else None
        print(f"Email: {email}")
        print(f"Domain: {domain}")
        print(f"Config: {'Found' if config else 'Not found'}")
        print()
