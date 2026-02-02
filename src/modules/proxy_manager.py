"""
MODUŁ 1: SYSTEM PROXY
Zarządzanie proxy dla każdego konta
"""

import re
import asyncio
import aiohttp
from typing import Optional, Dict, List
from dataclasses import dataclass
from enum import Enum


class ProxyType(Enum):
    """Proxy type enumeration"""
    SOCKS5 = "socks5"
    HTTP = "http"
    HTTPS = "https"


@dataclass
class ProxyConfig:
    """Proxy configuration data class"""
    url: str
    proxy_type: ProxyType
    host: str
    port: int
    username: Optional[str] = None
    password: Optional[str] = None
    
    def to_playwright_format(self) -> Dict:
        """Convert to Playwright proxy format"""
        proxy_config = {
            "server": f"{self.proxy_type.value}://{self.host}:{self.port}"
        }
        
        if self.username and self.password:
            proxy_config["username"] = self.username
            proxy_config["password"] = self.password
        
        return proxy_config
    
    def to_aiohttp_format(self) -> str:
        """Convert to aiohttp proxy format"""
        if self.username and self.password:
            return f"{self.proxy_type.value}://{self.username}:{self.password}@{self.host}:{self.port}"
        return f"{self.proxy_type.value}://{self.host}:{self.port}"


class ProxyManager:
    """
    Zarządzanie proxy dla systemu
    - Parsowanie formatów proxy
    - Testowanie proxy
    - Rotacja przy błędach
    - Blacklisting uszkodzonych proxy
    """
    
    def __init__(self, database):
        self.database = database
        self.test_url = "https://www.google.com"
        self.test_timeout = 10
    
    @staticmethod
    def parse_proxy_url(proxy_url: str) -> Optional[ProxyConfig]:
        """
        Parse proxy URL into ProxyConfig
        Supported formats:
        - socks5://user:pass@ip:port
        - socks5://ip:port
        - http://user:pass@ip:port
        - https://ip:port
        """
        # Pattern for proxy with authentication
        pattern_auth = r"^(socks5|http|https)://([^:]+):([^@]+)@([^:]+):(\d+)$"
        # Pattern for proxy without authentication
        pattern_no_auth = r"^(socks5|http|https)://([^:]+):(\d+)$"
        
        match_auth = re.match(pattern_auth, proxy_url)
        if match_auth:
            proxy_type, username, password, host, port = match_auth.groups()
            return ProxyConfig(
                url=proxy_url,
                proxy_type=ProxyType(proxy_type),
                host=host,
                port=int(port),
                username=username,
                password=password
            )
        
        match_no_auth = re.match(pattern_no_auth, proxy_url)
        if match_no_auth:
            proxy_type, host, port = match_no_auth.groups()
            return ProxyConfig(
                url=proxy_url,
                proxy_type=ProxyType(proxy_type),
                host=host,
                port=int(port)
            )
        
        return None
    
    async def test_proxy(self, proxy_config: ProxyConfig) -> bool:
        """
        Test if proxy is working
        Returns True if proxy works, False otherwise
        """
        try:
            timeout = aiohttp.ClientTimeout(total=self.test_timeout)
            
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.get(
                    self.test_url,
                    proxy=proxy_config.to_aiohttp_format()
                ) as response:
                    return response.status == 200
        except Exception as e:
            print(f"Proxy test failed for {proxy_config.url}: {e}")
            return False
    
    async def test_proxy_by_id(self, proxy_id: int) -> bool:
        """Test proxy by database ID"""
        proxy_data = self.database.get_proxy_for_account(proxy_id)
        if not proxy_data:
            return False
        
        proxy_config = self.parse_proxy_url(proxy_data['proxy_url'])
        if not proxy_config:
            return False
        
        is_working = await self.test_proxy(proxy_config)
        
        # Update proxy status in database
        conn = self.database.connect()
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE proxies 
            SET is_working = ?, last_test = CURRENT_TIMESTAMP
            WHERE id = ?
        """, (is_working, proxy_id))
        conn.commit()
        conn.close()
        
        return is_working
    
    def load_proxies_from_file(self, filepath: str) -> int:
        """
        Load proxies from a text file (one proxy per line)
        Returns number of proxies loaded
        """
        count = 0
        try:
            with open(filepath, 'r') as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith('#'):
                        continue
                    
                    proxy_config = self.parse_proxy_url(line)
                    if proxy_config:
                        proxy_id = self.database.add_proxy(
                            line, 
                            proxy_config.proxy_type.value
                        )
                        if proxy_id:
                            count += 1
        except FileNotFoundError:
            print(f"Proxy file not found: {filepath}")
        
        return count
    
    def assign_proxy_to_account(self, account_id: int) -> Optional[int]:
        """
        Assign an available proxy to an account
        Returns proxy_id if successful, None otherwise
        """
        proxy = self.database.get_available_proxy()
        if not proxy:
            return None
        
        conn = self.database.connect()
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE accounts 
            SET proxy_id = ?
            WHERE id = ?
        """, (proxy['id'], account_id))
        conn.commit()
        conn.close()
        
        return proxy['id']
    
    async def rotate_proxy_for_account(self, account_id: int, blacklist_current: bool = False) -> Optional[int]:
        """
        Rotate proxy for an account
        If blacklist_current is True, blacklist the current proxy
        Returns new proxy_id if successful
        """
        if blacklist_current:
            current_proxy = self.database.get_proxy_for_account(account_id)
            if current_proxy:
                self.database.blacklist_proxy(current_proxy['id'])
        
        return self.assign_proxy_to_account(account_id)
    
    def get_proxy_config_for_account(self, account_id: int) -> Optional[ProxyConfig]:
        """Get ProxyConfig for an account"""
        proxy_data = self.database.get_proxy_for_account(account_id)
        if not proxy_data:
            return None
        
        return self.parse_proxy_url(proxy_data['proxy_url'])


if __name__ == "__main__":
    # Test proxy parsing
    test_urls = [
        "socks5://user:pass@192.168.1.1:1080",
        "socks5://192.168.1.1:1080",
        "http://user:pass@192.168.1.1:8080",
        "https://192.168.1.1:8080"
    ]
    
    for url in test_urls:
        config = ProxyManager.parse_proxy_url(url)
        print(f"URL: {url}")
        print(f"Config: {config}")
        if config:
            print(f"Playwright format: {config.to_playwright_format()}")
            print(f"Aiohttp format: {config.to_aiohttp_format()}")
        print()
