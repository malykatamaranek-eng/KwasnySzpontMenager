"""Abstract foundation for email provider implementations.

This module defines the base interface that all email provider
implementations must follow, ensuring consistent behavior.
"""

from abc import ABC, abstractmethod
from typing import Optional, Dict, Any
import structlog

from ..models import (
    IMAPConfig,
    LoginResult,
    ProviderEndpoints,
    EmailCredentials,
    AuthenticationState
)
from ...proxy_manager.models import ProxyConfig
from ..api_client import AsyncHTTPClient


logger = structlog.get_logger(__name__)


class BaseEmailProvider(ABC):
    """Abstract base class defining email provider interface.
    
    All provider implementations must inherit from this class and
    implement the required abstract methods for authentication,
    endpoint discovery, and IMAP configuration.
    
    Args:
        http_client: HTTP client instance for API calls
        
    Example:
        >>> class CustomProvider(BaseEmailProvider):
        ...     async def authenticate_user(self, credentials, proxy_cfg):
        ...         # Implementation here
        ...         pass
    """
    
    def __init__(self, http_client: Optional[AsyncHTTPClient] = None):
        """Initialize provider with optional HTTP client."""
        self._http_client = http_client or AsyncHTTPClient()
        self._auth_state: Optional[AuthenticationState] = None
        self._provider_name = self.__class__.__name__
        
        logger.debug(
            "provider_initialized",
            provider=self._provider_name
        )
    
    @property
    def provider_identifier(self) -> str:
        """Get unique provider identifier.
        
        Returns:
            str: Provider name
        """
        return self._provider_name
    
    @property
    def is_authenticated(self) -> bool:
        """Check if provider has active authentication.
        
        Returns:
            bool: Authentication status
        """
        return self._auth_state is not None
    
    @abstractmethod
    async def authenticate_user(
        self,
        credentials: EmailCredentials,
        proxy_cfg: Optional[ProxyConfig] = None
    ) -> LoginResult:
        """Perform user authentication with provider.
        
        Args:
            credentials: User email and password
            proxy_cfg: Optional proxy configuration
            
        Returns:
            LoginResult: Authentication outcome with session details
            
        Raises:
            NotImplementedError: Must be implemented by subclass
        """
        raise NotImplementedError("Subclass must implement authenticate_user")
    
    @abstractmethod
    async def retrieve_imap_config(self) -> IMAPConfig:
        """Get IMAP server configuration for this provider.
        
        Returns:
            IMAPConfig: IMAP connection parameters
            
        Raises:
            NotImplementedError: Must be implemented by subclass
        """
        raise NotImplementedError("Subclass must implement retrieve_imap_config")
    
    @abstractmethod
    async def discover_endpoints(self) -> ProviderEndpoints:
        """Discover or return provider service endpoints.
        
        Returns:
            ProviderEndpoints: Collection of service URLs
            
        Raises:
            NotImplementedError: Must be implemented by subclass
        """
        raise NotImplementedError("Subclass must implement discover_endpoints")
    
    async def validate_credentials(
        self,
        credentials: EmailCredentials,
        proxy_cfg: Optional[ProxyConfig] = None
    ) -> bool:
        """Test if credentials are valid without full authentication.
        
        Args:
            credentials: Credentials to validate
            proxy_cfg: Optional proxy configuration
            
        Returns:
            bool: True if credentials appear valid
        """
        try:
            result = await self.authenticate_user(credentials, proxy_cfg)
            return result.success
        except Exception as error:
            logger.warning(
                "credential_validation_failed",
                provider=self._provider_name,
                error=str(error)
            )
            return False
    
    async def terminate_session(self) -> bool:
        """End current authentication session.
        
        Returns:
            bool: True if session terminated successfully
        """
        if not self._auth_state:
            logger.debug("no_active_session", provider=self._provider_name)
            return True
        
        try:
            endpoints = await self.discover_endpoints()
            
            if endpoints.logout_url and self._http_client:
                response = await self._http_client.get(endpoints.logout_url)
                
                if response.status_code < 400:
                    self._auth_state = None
                    self._http_client.purge_cookies()
                    
                    logger.info(
                        "session_terminated",
                        provider=self._provider_name
                    )
                    return True
            
            self._auth_state = None
            return True
            
        except Exception as error:
            logger.error(
                "session_termination_failed",
                provider=self._provider_name,
                error=str(error)
            )
            return False
    
    def extract_domain_from_email(self, email_address: str) -> str:
        """Extract domain portion from email address.
        
        Args:
            email_address: Full email address
            
        Returns:
            str: Domain part (after @)
            
        Raises:
            ValueError: If email format is invalid
        """
        if "@" not in email_address:
            raise ValueError(f"Invalid email format: {email_address}")
        
        _, domain = email_address.rsplit("@", 1)
        return domain.lower()
    
    def validate_email_format(self, email_address: str) -> bool:
        """Check if email address has valid format.
        
        Args:
            email_address: Email to validate
            
        Returns:
            bool: True if format is valid
        """
        if not email_address or "@" not in email_address:
            return False
        
        local, domain = email_address.rsplit("@", 1)
        
        if not local or not domain:
            return False
        
        if "." not in domain:
            return False
        
        return True
    
    async def cleanup(self):
        """Cleanup provider resources."""
        await self.terminate_session()
        
        if self._http_client:
            await self._http_client.shutdown()
        
        logger.debug("provider_cleanup_complete", provider=self._provider_name)
    
    def get_provider_metadata(self) -> Dict[str, Any]:
        """Get metadata about this provider.
        
        Returns:
            Dict: Provider information
        """
        return {
            "provider_name": self._provider_name,
            "authenticated": self.is_authenticated,
            "has_session": self._auth_state is not None
        }


class ProviderAuthenticationError(Exception):
    """Raised when provider authentication fails."""
    pass


class ProviderConfigurationError(Exception):
    """Raised when provider configuration is invalid."""
    pass


class ProviderNetworkError(Exception):
    """Raised when network communication fails."""
    pass
