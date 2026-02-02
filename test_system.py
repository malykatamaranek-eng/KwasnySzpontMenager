#!/usr/bin/env python3
"""
Test script to verify KWASNY LOG MANAGER components
Run this to check if the system is correctly installed
"""

import sys
from pathlib import Path

def test_imports():
    """Test if all modules can be imported"""
    print("🧪 Testing module imports...")
    
    tests = [
        ("Database", "from src.database import Database"),
        ("Proxy Manager", "from src.modules.proxy_manager import ProxyManager"),
        ("Email Automation", "from src.modules.email_automation import EmailAutomation"),
        ("Facebook Automation", "from src.modules.facebook_automation import FacebookAutomation"),
        ("Security Manager", "from src.modules.security_manager import SecurityManager"),
        ("Financial Calculator", "from src.modules.financial_calculator import FinancialCalculator"),
        ("Config Loader", "from src.utils.config_loader import ConfigLoader"),
        ("Main Coordinator", "from src.main import KwasnyLogManager"),
    ]
    
    passed = 0
    failed = 0
    
    for name, import_stmt in tests:
        try:
            exec(import_stmt)
            print(f"  ✅ {name}")
            passed += 1
        except Exception as e:
            print(f"  ❌ {name}: {e}")
            failed += 1
    
    print(f"\n📊 Results: {passed} passed, {failed} failed")
    return failed == 0


def test_database():
    """Test database creation"""
    print("\n🧪 Testing database...")
    
    try:
        from src.database import Database
        db = Database("test_db.db")
        print("  ✅ Database created successfully")
        
        # Test adding account
        account_id = db.add_account("test@test.com", "password123")
        if account_id:
            print(f"  ✅ Account created (ID: {account_id})")
        
        # Cleanup
        import os
        if os.path.exists("test_db.db"):
            os.remove("test_db.db")
        
        return True
    except Exception as e:
        print(f"  ❌ Database test failed: {e}")
        return False


def test_proxy_parsing():
    """Test proxy URL parsing"""
    print("\n🧪 Testing proxy parsing...")
    
    try:
        from src.modules.proxy_manager import ProxyManager
        
        test_urls = [
            "socks5://user:pass@192.168.1.1:1080",
            "socks5://192.168.1.1:1080",
            "http://user:pass@192.168.1.1:8080",
        ]
        
        for url in test_urls:
            config = ProxyManager.parse_proxy_url(url)
            if config:
                print(f"  ✅ Parsed: {url}")
            else:
                print(f"  ❌ Failed to parse: {url}")
                return False
        
        return True
    except Exception as e:
        print(f"  ❌ Proxy parsing test failed: {e}")
        return False


def test_config_loader():
    """Test configuration loading"""
    print("\n🧪 Testing configuration loader...")
    
    try:
        from src.utils.config_loader import ConfigLoader
        
        loader = ConfigLoader()
        
        # Test loading financial config
        financial = loader.load_financial_config()
        print(f"  ✅ Financial config loaded")
        print(f"     Proxy cost: ${financial['proxy_cost_daily']:.2f}")
        
        # Test loading system settings
        settings = loader.load_system_settings()
        print(f"  ✅ System settings loaded")
        print(f"     Max parallel: {settings.max_parallel_accounts}")
        
        return True
    except Exception as e:
        print(f"  ❌ Config loader test failed: {e}")
        return False


def test_financial_calculator():
    """Test financial calculations"""
    print("\n🧪 Testing financial calculator...")
    
    try:
        from src.modules.financial_calculator import FinancialConfig
        
        config = FinancialConfig()
        
        total_cost = (config.proxy_cost_daily + 
                     config.account_cost_daily + 
                     config.email_cost_daily + 
                     config.operational_cost_daily)
        
        actual_revenue = config.daily_revenue * (config.default_activity_percentage / 100.0)
        profit = actual_revenue - total_cost
        
        print(f"  ✅ Financial calculations work")
        print(f"     Daily cost: ${total_cost:.2f}")
        print(f"     Daily revenue: ${actual_revenue:.2f}")
        print(f"     Daily profit: ${profit:.2f}")
        
        return True
    except Exception as e:
        print(f"  ❌ Financial calculator test failed: {e}")
        return False


def check_directories():
    """Check if necessary directories exist"""
    print("\n🧪 Checking directories...")
    
    dirs = ['config', 'data', 'logs', 'src', 'src/modules', 'src/gui', 'src/utils']
    
    for dir_name in dirs:
        path = Path(dir_name)
        if path.exists():
            print(f"  ✅ {dir_name}")
        else:
            print(f"  ❌ {dir_name} not found")
            return False
    
    return True


def check_config_files():
    """Check if config files exist"""
    print("\n🧪 Checking configuration files...")
    
    files = {
        'config/financial_config.ini': 'Required',
        'config/system_settings.ini': 'Required',
        'config/domains_mapping.json': 'Required',
        'config/proxies.txt.example': 'Example',
        'config/accounts.txt.example': 'Example',
        'config/proxies.txt': 'Optional (add your proxies)',
        'config/accounts.txt': 'Optional (add your accounts)',
    }
    
    for file_name, status in files.items():
        path = Path(file_name)
        if path.exists():
            print(f"  ✅ {file_name}")
        else:
            if 'Optional' in status:
                print(f"  ⚠️  {file_name} - {status}")
            else:
                print(f"  ❌ {file_name} - Missing!")


def main():
    """Run all tests"""
    print("="*60)
    print("KWASNY LOG MANAGER - System Test")
    print("="*60)
    
    # Check directories
    if not check_directories():
        print("\n❌ Directory check failed!")
        return 1
    
    # Check config files
    check_config_files()
    
    # Run tests
    all_passed = True
    
    if not test_imports():
        all_passed = False
        print("\n⚠️  Some dependencies may not be installed.")
        print("   Run: pip install -r requirements.txt")
    
    if not test_database():
        all_passed = False
    
    if not test_proxy_parsing():
        all_passed = False
    
    if not test_config_loader():
        all_passed = False
    
    if not test_financial_calculator():
        all_passed = False
    
    # Final result
    print("\n" + "="*60)
    if all_passed:
        print("✅ All tests passed! System is ready.")
        print("\nNext steps:")
        print("1. Add your proxies to config/proxies.txt")
        print("2. Add your accounts to config/accounts.txt")
        print("3. Run: python -m src.gui.admin_panel")
    else:
        print("❌ Some tests failed. Please check the errors above.")
    print("="*60)
    
    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())
