"""Email Discovery module for Facebook automation system.

This module provides automatic detection and authentication for Polish
email providers, including WP.pl, O2.pl, Onet.pl, OP.pl, and Interia.pl.

Features:
    - Automatic provider detection from email addresses
    - HTTP client with proxy support and retry logic
    - IMAP configuration retrieval
    - Session management
    - Cookie persistence

Example:
    >>> from src.modules.email_discovery import (
    ...     EmailProviderDetector,
    ...     EmailCredentials
    ... )
    >>> 
    >>> detector = EmailProviderDetector()
    >>> credentials = EmailCredentials(
    ...     email_address="user@wp.pl",
    ...     password="secret"
    ... )
    >>> 
    >>> provider = detector.get_provider_for_credentials(credentials)
    >>> if provider:
    ...     result = await provider.authenticate_user(credentials)
    ...     if result.success:
    ...         imap_config = await provider.retrieve_imap_config()
"""

from .models import (
    IMAPConfig,
    LoginResult,
    ProviderEndpoints,
    EmailCredentials,
    AuthenticationState
)

from .api_client import AsyncHTTPClient

from .providers import (
    BaseEmailProvider,
    ProviderAuthenticationError,
    ProviderConfigurationError,
    ProviderNetworkError,
    WPEmailProvider,
    O2EmailProvider,
    OnetEmailProvider,
    OPEmailProvider,
    InteriaEmailProvider
)

from .detector import (
    EmailProviderDetector,
    create_provider_for_email,
    get_supported_domains
)


__version__ = "1.0.0"

__all__ = [
    # Models
    "IMAPConfig",
    "LoginResult",
    "ProviderEndpoints",
    "EmailCredentials",
    "AuthenticationState",
    
    # HTTP Client
    "AsyncHTTPClient",
    
    # Base Classes and Exceptions
    "BaseEmailProvider",
    "ProviderAuthenticationError",
    "ProviderConfigurationError",
    "ProviderNetworkError",
    
    # Provider Implementations
    "WPEmailProvider",
    "O2EmailProvider",
    "OnetEmailProvider",
    "OPEmailProvider",
    "InteriaEmailProvider",
    
    # Detection and Factory
    "EmailProviderDetector",
    "create_provider_for_email",
    "get_supported_domains",
]
