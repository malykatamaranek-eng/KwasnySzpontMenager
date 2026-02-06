# Email Discovery Module

## Overview

The Email Discovery module provides automatic detection, authentication, and configuration management for Polish email providers. It supports WP.pl, O2.pl, Onet.pl, OP.pl, and Interia.pl.

## Features

- **Automatic Provider Detection**: Identifies email provider from email address
- **HTTP Client with Advanced Features**:
  - Proxy support (SOCKS5, HTTP, HTTPS)
  - Automatic retry with exponential backoff
  - Cookie persistence and management
  - User-Agent rotation
  - Request/response logging
- **IMAP Configuration**: Retrieves correct IMAP settings for each provider
- **Session Management**: Handles authentication state and cookies
- **Extensible Architecture**: Easy to add new providers

## Installation

The module requires the following dependencies (already in requirements/base.txt):

```bash
pip install httpx pydantic structlog
```

## Quick Start

### Basic Usage

```python
import asyncio
from src.modules.email_discovery import (
    EmailProviderDetector,
    EmailCredentials
)

async def authenticate_email():
    # Create credentials
    credentials = EmailCredentials(
        email_address="user@wp.pl",
        password="your_password"
    )
    
    # Detect provider
    detector = EmailProviderDetector()
    provider = detector.get_provider_for_credentials(credentials)
    
    if provider:
        # Authenticate
        result = await provider.authenticate_user(credentials)
        
        if result.success:
            print(f"Authentication successful!")
            print(f"Session ID: {result.session_id}")
            
            # Get IMAP config
            imap_config = await provider.retrieve_imap_config()
            print(f"IMAP: {imap_config.host}:{imap_config.port}")
        else:
            print(f"Authentication failed: {result.error_message}")
        
        # Cleanup
        await provider.cleanup()

asyncio.run(authenticate_email())
```

### Using with Proxy

```python
from src.modules.proxy_manager import ProxyConfig
from src.modules.email_discovery import EmailCredentials, EmailProviderDetector

async def authenticate_with_proxy():
    credentials = EmailCredentials(
        email_address="user@onet.pl",
        password="password"
    )
    
    proxy = ProxyConfig(
        host="proxy.example.com",
        port=1080,
        protocol="socks5",
        username="proxy_user",
        password="proxy_pass"
    )
    
    detector = EmailProviderDetector()
    provider = detector.detect_provider("user@onet.pl")
    
    result = await provider.authenticate_user(credentials, proxy_cfg=proxy)
    
    await provider.cleanup()
```

### Check Supported Domains

```python
from src.modules.email_discovery import get_supported_domains

domains = get_supported_domains()
print(f"Supported domains: {domains}")
# Output: ['interia.eu', 'interia.pl', 'o2.pl', 'onet.eu', 
#          'onet.pl', 'op.pl', 'vp.pl', 'wp.pl']
```

## Architecture

### Module Structure

```
src/modules/email_discovery/
├── __init__.py           # Module exports
├── models.py             # Pydantic data models
├── api_client.py         # HTTP client with retry logic
├── detector.py           # Provider detection and factory
└── providers/
    ├── __init__.py       # Provider exports
    ├── base.py           # Abstract base provider
    ├── wp_pl.py          # WP.pl implementation
    ├── o2_pl.py          # O2.pl implementation
    ├── onet_pl.py        # Onet.pl implementation
    ├── op_pl.py          # OP.pl implementation
    └── interia_pl.py     # Interia.pl implementation
```

### Key Components

#### 1. Models (`models.py`)

**IMAPConfig**: IMAP server connection parameters
```python
IMAPConfig(
    host="imap.wp.pl",
    port=993,
    use_ssl=True,
    use_tls=False,
    timeout_seconds=30
)
```

**LoginResult**: Authentication outcome
```python
LoginResult(
    success=True,
    session_id="abc123",
    cookies={"session": "xyz"},
    provider="wp.pl"
)
```

**EmailCredentials**: User credentials container
```python
EmailCredentials(
    email_address="user@domain.com",
    password="secret"
)
```

#### 2. HTTP Client (`api_client.py`)

**AsyncHTTPClient**: Advanced async HTTP client

Features:
- Automatic retry (3 attempts by default)
- Exponential backoff (2x multiplier)
- Cookie management
- User-Agent rotation
- Proxy support

```python
async with AsyncHTTPClient(timeout_seconds=30) as client:
    response = await client.get("https://example.com")
    response = await client.post(
        "https://api.example.com",
        json_data={"key": "value"}
    )
```

#### 3. Provider Detector (`detector.py`)

**EmailProviderDetector**: Factory for provider instances

```python
detector = EmailProviderDetector()

# Detect from email
provider = detector.detect_provider("user@wp.pl")

# Check if supported
if detector.is_supported_email("user@example.com"):
    provider = detector.detect_provider("user@example.com")

# Get statistics
stats = detector.get_statistics()
print(stats)  # {'registered_providers': 8, 'cached_instances': 2}
```

#### 4. Base Provider (`providers/base.py`)

**BaseEmailProvider**: Abstract base class

All providers must implement:
- `authenticate_user()`: Perform authentication
- `retrieve_imap_config()`: Get IMAP settings
- `discover_endpoints()`: Return service URLs

```python
class CustomProvider(BaseEmailProvider):
    async def authenticate_user(self, credentials, proxy_cfg=None):
        # Implementation
        pass
    
    async def retrieve_imap_config(self):
        return IMAPConfig(host="imap.custom.com", port=993, use_ssl=True)
    
    async def discover_endpoints(self):
        return ProviderEndpoints(
            login_url="https://login.custom.com",
            imap_host="imap.custom.com",
            imap_port=993
        )
```

## Provider Implementation Status

| Provider | IMAP Config | Endpoints | Authentication |
|----------|-------------|-----------|----------------|
| WP.pl | ✅ Complete | ⚠️ Placeholder | ❌ Needs reverse engineering |
| O2.pl | ✅ Complete | ⚠️ Placeholder | ❌ Needs reverse engineering |
| Onet.pl | ✅ Complete | ⚠️ Placeholder | ❌ Needs reverse engineering |
| OP.pl | ✅ Complete | ⚠️ Placeholder | ❌ Needs reverse engineering |
| Interia.pl | ✅ Complete | ⚠️ Placeholder | ❌ Needs reverse engineering |

### IMAP Configurations

All providers have working IMAP configurations:

```python
# WP.pl
IMAPConfig(host="imap.wp.pl", port=993, use_ssl=True)

# O2.pl
IMAPConfig(host="poczta.o2.pl", port=993, use_ssl=True)

# Onet.pl
IMAPConfig(host="imap.poczta.onet.pl", port=993, use_ssl=True)

# OP.pl (uses Onet infrastructure)
IMAPConfig(host="imap.poczta.onet.pl", port=993, use_ssl=True)

# Interia.pl
IMAPConfig(host="poczta.interia.pl", port=993, use_ssl=True)
```

## Reverse Engineering Guide

Each provider file contains detailed instructions for reverse engineering authentication endpoints. The general process:

### Step 1: Capture Network Traffic

1. Open browser Developer Tools (F12)
2. Navigate to provider login page
3. Open Network tab
4. Filter by XHR/Fetch requests
5. Perform test login
6. Analyze authentication requests

### Step 2: Identify Key Components

**A. Request Details:**
- Endpoint URL
- HTTP method (POST, GET, etc.)
- Content-Type header
- Required custom headers

**B. Payload Structure:**
- Field names for credentials
- CSRF/security tokens
- Additional parameters
- JSON vs form-encoded

**C. Response Handling:**
- Success indicators
- Session cookies
- Error message format
- Redirect handling

### Step 3: Implement Authentication

Update the provider's `authenticate_user()` method with discovered details:

```python
async def authenticate_user(self, credentials, proxy_cfg=None):
    # Step 1: Get CSRF token
    token_response = await self._http_client.get(
        "https://provider.com/token",
        proxy_config=proxy_cfg
    )
    csrf_token = extract_csrf(token_response)
    
    # Step 2: Build payload
    auth_payload = {
        "email": credentials.email_address,
        "password": credentials.password,
        "csrf": csrf_token
    }
    
    # Step 3: Set headers
    headers = {
        "Content-Type": "application/json",
        "X-CSRF-Token": csrf_token,
        "Origin": "https://provider.com"
    }
    
    # Step 4: Execute authentication
    response = await self._http_client.post(
        "https://provider.com/auth",
        json_data=auth_payload,
        headers=headers,
        proxy_config=proxy_cfg
    )
    
    # Step 5: Process response
    if response.status_code == 200:
        data = response.json()
        if data.get("success"):
            return LoginResult(
                success=True,
                session_id=data["session_id"],
                cookies=self._http_client.extract_cookies(),
                provider="provider.com"
            )
    
    return LoginResult(
        success=False,
        error_message="Authentication failed",
        provider="provider.com"
    )
```

## Error Handling

The module defines custom exceptions:

```python
from src.modules.email_discovery.providers import (
    ProviderAuthenticationError,  # Authentication failures
    ProviderConfigurationError,   # Configuration issues
    ProviderNetworkError           # Network problems
)

try:
    result = await provider.authenticate_user(credentials)
except ProviderAuthenticationError as e:
    print(f"Auth error: {e}")
except ProviderNetworkError as e:
    print(f"Network error: {e}")
```

## Adding New Providers

To add a new email provider:

### 1. Create Provider Class

```python
# src/modules/email_discovery/providers/custom_pl.py
from .base import BaseEmailProvider
from ..models import IMAPConfig, LoginResult, ProviderEndpoints, EmailCredentials

class CustomEmailProvider(BaseEmailProvider):
    _IMAP_HOSTNAME = "imap.custom.pl"
    _IMAP_PORT = 993
    _IMAP_USE_SSL = True
    
    async def authenticate_user(self, credentials, proxy_cfg=None):
        # Implementation
        pass
    
    async def retrieve_imap_config(self):
        return IMAPConfig(
            host=self._IMAP_HOSTNAME,
            port=self._IMAP_PORT,
            use_ssl=self._IMAP_USE_SSL
        )
    
    async def discover_endpoints(self):
        return ProviderEndpoints(
            login_url="https://login.custom.pl",
            imap_host=self._IMAP_HOSTNAME,
            imap_port=self._IMAP_PORT
        )
```

### 2. Register in Detector

```python
# src/modules/email_discovery/detector.py
from .providers import CustomEmailProvider

_PROVIDER_REGISTRY = {
    # ... existing providers
    "custom.pl": CustomEmailProvider,
}
```

### 3. Export from Module

```python
# src/modules/email_discovery/providers/__init__.py
from .custom_pl import CustomEmailProvider

__all__ = [
    # ... existing exports
    "CustomEmailProvider",
]
```

## Testing

### Unit Tests

```python
import pytest
from src.modules.email_discovery import EmailProviderDetector, EmailCredentials

def test_provider_detection():
    detector = EmailProviderDetector()
    
    # Test detection
    provider = detector.detect_provider("user@wp.pl")
    assert provider is not None
    assert provider.provider_identifier == "WPEmailProvider"

@pytest.mark.asyncio
async def test_imap_config():
    detector = EmailProviderDetector()
    provider = detector.detect_provider("user@onet.pl")
    
    config = await provider.retrieve_imap_config()
    assert config.host == "imap.poczta.onet.pl"
    assert config.port == 993
    assert config.use_ssl is True
```

### Integration Tests

```python
@pytest.mark.asyncio
async def test_full_authentication_flow():
    credentials = EmailCredentials(
        email_address="test@wp.pl",
        password="test123"
    )
    
    detector = EmailProviderDetector()
    provider = detector.get_provider_for_credentials(credentials)
    
    result = await provider.authenticate_user(credentials)
    # Note: Will fail until reverse engineering is complete
    
    await provider.cleanup()
```

## Logging

The module uses structured logging (structlog):

```python
import structlog

logger = structlog.get_logger(__name__)

# Logs are automatically generated:
# - HTTP requests/responses
# - Provider detection
# - Authentication attempts
# - Errors and warnings
```

Log format:
```json
{
    "event": "provider_detected",
    "domain": "wp.pl",
    "provider": "WPEmailProvider",
    "logger": "src.modules.email_discovery.detector",
    "level": "INFO",
    "timestamp": "2024-01-01T12:00:00Z"
}
```

## Performance Considerations

### Connection Pooling

The AsyncHTTPClient reuses connections automatically via httpx.

### Caching

EmailProviderDetector caches provider instances by domain:

```python
detector = EmailProviderDetector()

# First call creates instance
provider1 = detector.detect_provider("user@wp.pl")

# Second call returns cached instance
provider2 = detector.detect_provider("another@wp.pl")

assert provider1 is provider2  # Same instance

# Clear cache if needed
detector.clear_cache()
```

### Timeouts

Configure appropriate timeouts:

```python
# Client-level timeout
client = AsyncHTTPClient(timeout_seconds=30)

# IMAP timeout
imap_config = IMAPConfig(
    host="imap.example.com",
    port=993,
    timeout_seconds=60
)
```

## Security Considerations

1. **Credentials**: Never log or expose passwords
2. **SSL/TLS**: Always use SSL for IMAP (all providers configured)
3. **Proxies**: Support authenticated proxies for anonymity
4. **Session Management**: Proper cleanup to prevent session leaks
5. **Rate Limiting**: Retry logic includes exponential backoff

## Troubleshooting

### Common Issues

**Issue**: `ModuleNotFoundError: No module named 'httpx'`
```bash
pip install httpx
```

**Issue**: Provider always returns authentication failure
- Authentication endpoints need reverse engineering
- See detailed comments in provider files
- Follow the reverse engineering guide

**Issue**: Timeout errors
```python
# Increase timeout
client = AsyncHTTPClient(timeout_seconds=60)
```

**Issue**: Proxy connection fails
```python
# Verify proxy configuration
proxy = ProxyConfig(
    host="proxy.example.com",
    port=1080,
    protocol="socks5",  # Ensure correct protocol
    username="user",
    password="pass"
)
```

## Future Enhancements

- [ ] Complete authentication for all providers
- [ ] Add OAuth2 support for modern providers
- [ ] Implement session refresh mechanisms
- [ ] Add rate limiting protection
- [ ] Support for two-factor authentication
- [ ] Add more Polish email providers (Gmail.pl, etc.)
- [ ] Implement connection pooling optimizations
- [ ] Add provider health monitoring

## Contributing

When adding or updating providers:

1. Follow the existing code structure
2. Include comprehensive docstrings
3. Add detailed reverse engineering instructions
4. Update this README
5. Add tests for new functionality

## License

Part of the Facebook Automation System.
