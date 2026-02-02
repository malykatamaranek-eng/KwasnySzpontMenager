"""
KWASNY LOG MANAGER - Main Application Coordinator
Orchestrates all modules and manages account workflows
"""

import asyncio
from pathlib import Path
from typing import List, Dict, Optional
from datetime import datetime

from src.database import Database
from src.modules.proxy_manager import ProxyManager
from src.modules.email_automation import EmailAutomation, EmailStatus
from src.modules.facebook_automation import FacebookAutomation, FacebookStatus
from src.modules.security_manager import SecurityManager
from src.modules.financial_calculator import FinancialCalculator, FinancialConfig
from src.utils.config_loader import ConfigLoader, SystemSettings


class KwasnyLogManager:
    """
    Main application coordinator
    Manages the complete workflow for all accounts
    """
    
    def __init__(self, config_dir: str = "config", db_path: str = "data/kwasny.db"):
        # Initialize database
        self.database = Database(db_path)
        
        # Load configuration
        self.config_loader = ConfigLoader(config_dir)
        self.system_settings = self.config_loader.load_system_settings()
        
        # Initialize modules
        self.proxy_manager = ProxyManager(self.database)
        self.email_automation = EmailAutomation(self.database, self.proxy_manager)
        self.facebook_automation = FacebookAutomation(
            self.database, 
            self.proxy_manager, 
            self.email_automation
        )
        self.security_manager = SecurityManager(self.database, self.proxy_manager)
        
        # Load financial config and create calculator
        financial_config_dict = self.config_loader.load_financial_config()
        self.financial_config = FinancialConfig(**financial_config_dict)
        self.financial_calculator = FinancialCalculator(self.database, self.financial_config)
        
        print("✅ KWASNY LOG MANAGER initialized")
    
    def initialize_system(self):
        """
        Initialize system with proxies and accounts from config files
        """
        print("\n🔄 Initializing system...")
        
        # Load and add proxies
        proxies = self.config_loader.load_proxies()
        print(f"📋 Found {len(proxies)} proxies in config")
        
        for proxy_url in proxies:
            proxy_config = self.proxy_manager.parse_proxy_url(proxy_url)
            if proxy_config:
                self.database.add_proxy(proxy_url, proxy_config.proxy_type.value)
        
        print(f"✅ Loaded {len(proxies)} proxies")
        
        # Load and add accounts
        accounts = self.config_loader.load_accounts()
        print(f"📋 Found {len(accounts)} accounts in config")
        
        for account_data in accounts:
            account_id = self.database.add_account(
                email=account_data['email'],
                email_password=account_data['email_password'],
                facebook_password=account_data.get('facebook_password')
            )
            
            if account_id:
                # Assign proxy to account
                proxy_id = self.proxy_manager.assign_proxy_to_account(account_id)
                if proxy_id:
                    print(f"  ✅ {account_data['email']} → Proxy assigned")
                else:
                    print(f"  ⚠️  {account_data['email']} → No proxy available")
        
        print(f"✅ Loaded {len(accounts)} accounts\n")
    
    async def process_single_account(self, account_id: int) -> Dict:
        """
        Process a single account through the complete workflow:
        1. Login to email
        2. Login to Facebook (with auto-reset if needed)
        3. Security scan
        4. Update financial data
        """
        account = self.database.get_account(account_id)
        if not account:
            return {'success': False, 'error': 'Account not found'}
        
        email = account['email']
        print(f"\n{'='*60}")
        print(f"🔄 Processing account: {email}")
        print(f"{'='*60}")
        
        results = {
            'account_id': account_id,
            'email': email,
            'email_status': None,
            'facebook_status': None,
            'security_scan': None,
            'financial_update': False,
            'success': True,
            'errors': []
        }
        
        # Step 1: Login to email
        print(f"📧 Step 1: Email login...")
        try:
            email_status, email_error = await self.email_automation.login_to_email(
                account_id, 
                headless=self.system_settings.headless_browser
            )
            results['email_status'] = email_status.value
            
            if email_status == EmailStatus.POCZTA_DZIALA:
                print(f"  ✅ Email login successful")
            else:
                print(f"  ❌ Email login failed: {email_status.value}")
                results['errors'].append(f"Email: {email_error}")
        except Exception as e:
            print(f"  ❌ Email login error: {e}")
            results['errors'].append(f"Email exception: {e}")
        
        # Step 2: Login to Facebook (with auto-reset)
        print(f"📱 Step 2: Facebook login...")
        try:
            facebook_status, fb_error = await self.facebook_automation.login_with_auto_reset(
                account_id,
                new_password=self.system_settings.default_facebook_password,
                headless=self.system_settings.headless_browser
            )
            results['facebook_status'] = facebook_status.value
            
            if facebook_status == FacebookStatus.LOGIN_SUKCES:
                print(f"  ✅ Facebook login successful")
            else:
                print(f"  ⚠️  Facebook status: {facebook_status.value}")
                if fb_error:
                    results['errors'].append(f"Facebook: {fb_error}")
        except Exception as e:
            print(f"  ❌ Facebook login error: {e}")
            results['errors'].append(f"Facebook exception: {e}")
        
        # Step 3: Security scan (only if Facebook login successful)
        if results['facebook_status'] == FacebookStatus.LOGIN_SUKCES.value:
            print(f"🔒 Step 3: Security scan...")
            try:
                security_results = await self.security_manager.daily_security_scan(
                    account_id,
                    headless=self.system_settings.headless_browser
                )
                results['security_scan'] = security_results
                print(f"  ✅ Security scan complete")
                print(f"     Sessions logged out: {security_results['sessions_logged_out']}")
            except Exception as e:
                print(f"  ❌ Security scan error: {e}")
                results['errors'].append(f"Security: {e}")
        else:
            print(f"🔒 Step 3: Security scan skipped (not logged in)")
        
        # Step 4: Update financial data
        print(f"💰 Step 4: Financial update...")
        try:
            profit = self.financial_calculator.calculate_daily_profit(account_id)
            results['financial_update'] = True
            results['daily_profit'] = profit
            print(f"  ✅ Financial data updated (Daily profit: ${profit:.2f})")
        except Exception as e:
            print(f"  ❌ Financial update error: {e}")
            results['errors'].append(f"Financial: {e}")
        
        # Summary
        print(f"\n📊 Summary for {email}:")
        print(f"  Email: {results['email_status']}")
        print(f"  Facebook: {results['facebook_status']}")
        if results['errors']:
            print(f"  ⚠️  Errors: {len(results['errors'])}")
            results['success'] = False
        else:
            print(f"  ✅ All operations completed successfully")
        
        return results
    
    async def process_all_accounts(self, parallel: bool = False):
        """
        Process all active accounts
        """
        accounts = self.database.get_all_accounts(active_only=True)
        
        if not accounts:
            print("⚠️  No active accounts found")
            return []
        
        print(f"\n{'='*60}")
        print(f"🚀 Processing {len(accounts)} accounts...")
        print(f"{'='*60}")
        
        results = []
        
        if parallel:
            # Process accounts in parallel (limited by max_parallel_accounts)
            max_parallel = self.system_settings.max_parallel_accounts
            
            for i in range(0, len(accounts), max_parallel):
                batch = accounts[i:i + max_parallel]
                tasks = [self.process_single_account(acc['id']) for acc in batch]
                batch_results = await asyncio.gather(*tasks, return_exceptions=True)
                results.extend(batch_results)
        else:
            # Process accounts sequentially
            for account in accounts:
                result = await self.process_single_account(account['id'])
                results.append(result)
        
        # Print final summary
        print(f"\n{'='*60}")
        print(f"📊 FINAL SUMMARY")
        print(f"{'='*60}")
        
        successful = sum(1 for r in results if isinstance(r, dict) and r.get('success', False))
        failed = len(results) - successful
        
        print(f"Total accounts processed: {len(results)}")
        print(f"  ✅ Successful: {successful}")
        print(f"  ❌ Failed: {failed}")
        
        # Show global financial statistics
        global_stats = self.financial_calculator.get_global_statistics()
        print(f"\n💰 Financial Statistics:")
        print(f"  Total accounts: {global_stats['total_accounts']}")
        print(f"  Total profit: ${global_stats['total_profit']:.2f}")
        print(f"  Avg profit/account: ${global_stats['avg_profit_per_account']:.2f}")
        print(f"  ROI: {global_stats['roi_percentage']:.1f}%")
        print(f"  Losing accounts: {global_stats['losing_accounts_count']}")
        
        return results
    
    def display_account_details(self, account_id: int):
        """
        Display detailed information about a specific account
        """
        account = self.database.get_account(account_id)
        if not account:
            print(f"❌ Account {account_id} not found")
            return
        
        # Financial summary
        print(self.financial_calculator.format_account_summary(account_id))
        
        # Recent logs
        print(f"\n📋 Recent Activity:")
        logs = self.database.get_account_logs(account_id, limit=10)
        for log in logs:
            print(f"  [{log['timestamp']}] {log['action']}: {log['status']}")
            if log['details']:
                print(f"    ↳ {log['details']}")
    
    def list_all_accounts(self):
        """
        List all accounts with their current status
        """
        accounts = self.database.get_all_accounts(active_only=False)
        
        print(f"\n{'='*80}")
        print(f"📋 ALL ACCOUNTS ({len(accounts)} total)")
        print(f"{'='*80}")
        print(f"{'ID':<5} {'Email':<30} {'Email Status':<20} {'FB Status':<20}")
        print(f"{'-'*80}")
        
        for account in accounts:
            status_icon = "✅" if account['active'] else "❌"
            print(f"{account['id']:<5} {account['email']:<30} {account['email_status']:<20} {account['facebook_status']:<20}")


async def main():
    """Main entry point"""
    # Initialize manager
    manager = KwasnyLogManager()
    
    # Check if system needs initialization
    accounts = manager.database.get_all_accounts(active_only=False)
    if not accounts:
        print("🔄 First run detected - initializing system...")
        manager.initialize_system()
    
    # Process all accounts
    await manager.process_all_accounts(parallel=False)
    
    # List all accounts
    manager.list_all_accounts()


if __name__ == "__main__":
    asyncio.run(main())
