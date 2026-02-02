"""
MODUŁ 8: KONFIGURACJA I USTAWIENIA
Loader for configuration files
"""

import json
import configparser
from pathlib import Path
from typing import Dict, List, Optional
from dataclasses import dataclass


@dataclass
class SystemSettings:
    """System-wide settings"""
    max_parallel_accounts: int = 5
    operation_timeout: int = 30
    retry_attempts: int = 2
    security_scan_interval_hours: int = 24
    default_facebook_password: str = "NewSecurePass123!"
    log_directory: str = "logs"
    headless_browser: bool = True
    auto_rotate_proxy_on_failure: bool = True


class ConfigLoader:
    """
    Load configuration from various files
    """
    
    def __init__(self, config_dir: str = "config"):
        self.config_dir = Path(config_dir)
        self.config_dir.mkdir(parents=True, exist_ok=True)
    
    def load_proxies(self, filename: str = "proxies.txt") -> List[str]:
        """
        Load proxies from text file
        Returns list of proxy URLs
        """
        filepath = self.config_dir / filename
        
        if not filepath.exists():
            print(f"Warning: Proxy file not found: {filepath}")
            return []
        
        proxies = []
        with open(filepath, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#'):
                    proxies.append(line)
        
        return proxies
    
    def load_accounts(self, filename: str = "accounts.txt") -> List[Dict[str, str]]:
        """
        Load accounts from text file
        Format: email:password or email:password:facebook_password
        Returns list of account dicts
        """
        filepath = self.config_dir / filename
        
        if not filepath.exists():
            print(f"Warning: Accounts file not found: {filepath}")
            return []
        
        accounts = []
        with open(filepath, 'r') as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith('#'):
                    continue
                
                parts = line.split(':')
                if len(parts) >= 2:
                    account = {
                        'email': parts[0],
                        'email_password': parts[1],
                        'facebook_password': parts[2] if len(parts) >= 3 else None
                    }
                    accounts.append(account)
        
        return accounts
    
    def load_financial_config(self, filename: str = "financial_config.ini") -> Dict:
        """
        Load financial configuration from INI file
        """
        filepath = self.config_dir / filename
        
        # Default values
        defaults = {
            'proxy_cost_daily': 0.15,
            'account_cost_total': 3.00,
            'account_amortization_days': 30,
            'email_cost_total': 0.30,
            'email_amortization_days': 30,
            'operational_cost_daily': 0.05,
            'daily_revenue': 1.50,
            'default_activity_percentage': 85.0
        }
        
        if not filepath.exists():
            print(f"Warning: Financial config not found: {filepath}")
            print("Creating default financial config...")
            self.create_default_financial_config()
            return defaults
        
        config = configparser.ConfigParser()
        config.read(filepath)
        
        if 'Financial' not in config:
            return defaults
        
        financial = config['Financial']
        
        return {
            'proxy_cost_daily': financial.getfloat('proxy_cost_daily', defaults['proxy_cost_daily']),
            'account_cost_total': financial.getfloat('account_cost_total', defaults['account_cost_total']),
            'account_amortization_days': financial.getint('account_amortization_days', defaults['account_amortization_days']),
            'email_cost_total': financial.getfloat('email_cost_total', defaults['email_cost_total']),
            'email_amortization_days': financial.getint('email_amortization_days', defaults['email_amortization_days']),
            'operational_cost_daily': financial.getfloat('operational_cost_daily', defaults['operational_cost_daily']),
            'daily_revenue': financial.getfloat('daily_revenue', defaults['daily_revenue']),
            'default_activity_percentage': financial.getfloat('default_activity_percentage', defaults['default_activity_percentage'])
        }
    
    def load_domain_mapping(self, filename: str = "domains_mapping.json") -> Dict:
        """
        Load domain to URL mapping from JSON file
        """
        filepath = self.config_dir / filename
        
        # Default mapping (from email_automation module)
        defaults = {
            'wp.pl': {
                'login_url': 'https://poczta.wp.pl/login/login.html'
            },
            'onet.pl': {
                'login_url': 'https://konto.onet.pl/signin'
            },
            'o2.pl': {
                'login_url': 'https://1login.wp.pl/zaloguj/'
            },
            'tlen.pl': {
                'login_url': 'https://1login.wp.pl/zaloguj/'
            },
            'interia.pl': {
                'login_url': 'https://konto.interia.pl/logowanie'
            }
        }
        
        if not filepath.exists():
            print(f"Warning: Domain mapping not found: {filepath}")
            print("Creating default domain mapping...")
            self.create_default_domain_mapping()
            return defaults
        
        with open(filepath, 'r') as f:
            return json.load(f)
    
    def load_system_settings(self, filename: str = "system_settings.ini") -> SystemSettings:
        """
        Load system settings from INI file
        """
        filepath = self.config_dir / filename
        
        settings = SystemSettings()
        
        if not filepath.exists():
            print(f"Warning: System settings not found: {filepath}")
            print("Creating default system settings...")
            self.create_default_system_settings()
            return settings
        
        config = configparser.ConfigParser()
        config.read(filepath)
        
        if 'System' in config:
            system = config['System']
            settings.max_parallel_accounts = system.getint('max_parallel_accounts', settings.max_parallel_accounts)
            settings.operation_timeout = system.getint('operation_timeout', settings.operation_timeout)
            settings.retry_attempts = system.getint('retry_attempts', settings.retry_attempts)
            settings.security_scan_interval_hours = system.getint('security_scan_interval_hours', settings.security_scan_interval_hours)
            settings.default_facebook_password = system.get('default_facebook_password', settings.default_facebook_password)
            settings.log_directory = system.get('log_directory', settings.log_directory)
            settings.headless_browser = system.getboolean('headless_browser', settings.headless_browser)
            settings.auto_rotate_proxy_on_failure = system.getboolean('auto_rotate_proxy_on_failure', settings.auto_rotate_proxy_on_failure)
        
        return settings
    
    def create_default_financial_config(self):
        """Create default financial config file"""
        filepath = self.config_dir / "financial_config.ini"
        
        config = configparser.ConfigParser()
        config['Financial'] = {
            'proxy_cost_daily': '0.15',
            'account_cost_total': '3.00',
            'account_amortization_days': '30',
            'email_cost_total': '0.30',
            'email_amortization_days': '30',
            'operational_cost_daily': '0.05',
            'daily_revenue': '1.50',
            'default_activity_percentage': '85.0'
        }
        
        with open(filepath, 'w') as f:
            config.write(f)
    
    def create_default_domain_mapping(self):
        """Create default domain mapping file"""
        filepath = self.config_dir / "domains_mapping.json"
        
        mapping = {
            'wp.pl': {
                'login_url': 'https://poczta.wp.pl/login/login.html'
            },
            'onet.pl': {
                'login_url': 'https://konto.onet.pl/signin'
            },
            'o2.pl': {
                'login_url': 'https://1login.wp.pl/zaloguj/'
            },
            'tlen.pl': {
                'login_url': 'https://1login.wp.pl/zaloguj/'
            },
            'interia.pl': {
                'login_url': 'https://konto.interia.pl/logowanie'
            }
        }
        
        with open(filepath, 'w') as f:
            json.dump(mapping, f, indent=2)
    
    def create_default_system_settings(self):
        """Create default system settings file"""
        filepath = self.config_dir / "system_settings.ini"
        
        config = configparser.ConfigParser()
        config['System'] = {
            'max_parallel_accounts': '5',
            'operation_timeout': '30',
            'retry_attempts': '2',
            'security_scan_interval_hours': '24',
            'default_facebook_password': 'NewSecurePass123!',
            'log_directory': 'logs',
            'headless_browser': 'true',
            'auto_rotate_proxy_on_failure': 'true'
        }
        
        with open(filepath, 'w') as f:
            config.write(f)
    
    def create_example_files(self):
        """Create example configuration files"""
        # Example proxies.txt
        proxies_file = self.config_dir / "proxies.txt.example"
        with open(proxies_file, 'w') as f:
            f.write("# Example proxy list\n")
            f.write("# One proxy per line\n")
            f.write("# Supported formats:\n")
            f.write("#   socks5://user:pass@ip:port\n")
            f.write("#   socks5://ip:port\n")
            f.write("#   http://user:pass@ip:port\n")
            f.write("#   https://ip:port\n")
            f.write("\n")
            f.write("socks5://user1:pass1@192.168.1.1:1080\n")
            f.write("socks5://192.168.1.2:1080\n")
            f.write("http://user2:pass2@192.168.1.3:8080\n")
        
        # Example accounts.txt
        accounts_file = self.config_dir / "accounts.txt.example"
        with open(accounts_file, 'w') as f:
            f.write("# Example accounts list\n")
            f.write("# Format: email:password or email:password:facebook_password\n")
            f.write("# One account per line\n")
            f.write("\n")
            f.write("user1@wp.pl:emailpass123\n")
            f.write("user2@onet.pl:emailpass456:fbpass456\n")
            f.write("user3@interia.pl:emailpass789\n")


if __name__ == "__main__":
    # Test config loader
    loader = ConfigLoader()
    
    # Create default files
    loader.create_default_financial_config()
    loader.create_default_domain_mapping()
    loader.create_default_system_settings()
    loader.create_example_files()
    
    print("Configuration files created!")
    print(f"Location: {loader.config_dir}")
    
    # Load settings
    settings = loader.load_system_settings()
    print(f"\nSystem Settings:")
    print(f"  Max parallel accounts: {settings.max_parallel_accounts}")
    print(f"  Headless browser: {settings.headless_browser}")
    
    financial = loader.load_financial_config()
    print(f"\nFinancial Config:")
    print(f"  Proxy cost daily: ${financial['proxy_cost_daily']:.2f}")
    print(f"  Daily revenue: ${financial['daily_revenue']:.2f}")
