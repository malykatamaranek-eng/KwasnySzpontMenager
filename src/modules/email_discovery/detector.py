"""Email provider auto-detection and factory system.

This module provides automatic detection of email providers based on
email addresses and creates appropriate provider instances.
"""

from typing import Dict, Type, Optional
import structlog

from .providers import (
    BaseEmailProvider,
    WPEmailProvider,
    O2EmailProvider,
    OnetEmailProvider,
    OPEmailProvider,
    InteriaEmailProvider
)
from .models import EmailCredentials


logger = structlog.get_logger(__name__)


class EmailProviderDetector:
    """Automatic email provider detection and instantiation.
    
    This class implements a factory pattern to detect which email
    provider should handle a given email address and creates
    the appropriate provider instance.
    
    Example:
        >>> detector = EmailProviderDetector()
        >>> provider = detector.detect_provider("user@wp.pl")
        >>> print(provider.provider_identifier)
        'WPEmailProvider'
    """
    
    _PROVIDER_REGISTRY: Dict[str, Type[BaseEmailProvider]] = {
        "wp.pl": WPEmailProvider,
        "o2.pl": O2EmailProvider,
        "onet.pl": OnetEmailProvider,
        "onet.eu": OnetEmailProvider,
        "vp.pl": OnetEmailProvider,
        "op.pl": OPEmailProvider,
        "interia.pl": InteriaEmailProvider,
        "interia.eu": InteriaEmailProvider,
    }
    
    def __init__(self):
        """Initialize provider detector."""
        self._cache: Dict[str, BaseEmailProvider] = {}
        logger.debug(
            "detector_initialized",
            registered_providers=len(self._PROVIDER_REGISTRY)
        )
    
    def detect_provider(self, email_address: str) -> Optional[BaseEmailProvider]:
        """Detect and instantiate appropriate provider for email address.
        
        Args:
            email_address: Email address to analyze
            
        Returns:
            Optional[BaseEmailProvider]: Provider instance or None if unsupported
            
        Example:
            >>> detector = EmailProviderDetector()
            >>> provider = detector.detect_provider("test@onet.pl")
            >>> isinstance(provider, OnetEmailProvider)
            True
        """
        if not email_address or "@" not in email_address:
            logger.warning(
                "invalid_email_format",
                email=email_address
            )
            return None
        
        domain = self._extract_domain(email_address)
        
        if domain in self._cache:
            logger.debug(
                "provider_from_cache",
                domain=domain
            )
            return self._cache[domain]
        
        provider_class = self._PROVIDER_REGISTRY.get(domain)
        
        if provider_class is None:
            logger.warning(
                "unsupported_provider",
                domain=domain,
                email=email_address
            )
            return None
        
        provider_instance = provider_class()
        self._cache[domain] = provider_instance
        
        logger.info(
            "provider_detected",
            domain=domain,
            provider=provider_instance.provider_identifier
        )
        
        return provider_instance
    
    def get_provider_for_credentials(
        self,
        credentials: EmailCredentials
    ) -> Optional[BaseEmailProvider]:
        """Get provider instance for given credentials.
        
        Args:
            credentials: Email credentials object
            
        Returns:
            Optional[BaseEmailProvider]: Provider instance or None
        """
        if credentials.provider_hint:
            provider_class = self._PROVIDER_REGISTRY.get(credentials.provider_hint)
            if provider_class:
                logger.debug(
                    "provider_from_hint",
                    hint=credentials.provider_hint
                )
                return provider_class()
        
        return self.detect_provider(credentials.email_address)
    
    def is_supported_domain(self, domain: str) -> bool:
        """Check if domain is supported.
        
        Args:
            domain: Email domain to check
            
        Returns:
            bool: True if domain has registered provider
        """
        return domain.lower() in self._PROVIDER_REGISTRY
    
    def is_supported_email(self, email_address: str) -> bool:
        """Check if email address is supported.
        
        Args:
            email_address: Email to check
            
        Returns:
            bool: True if provider available for this email
        """
        if not email_address or "@" not in email_address:
            return False
        
        domain = self._extract_domain(email_address)
        return self.is_supported_domain(domain)
    
    def list_supported_domains(self) -> list[str]:
        """Get list of all supported email domains.
        
        Returns:
            list[str]: List of supported domains
        """
        return sorted(self._PROVIDER_REGISTRY.keys())
    
    def register_provider(
        self,
        domain: str,
        provider_class: Type[BaseEmailProvider]
    ):
        """Register a new provider for a domain.
        
        Args:
            domain: Email domain to register
            provider_class: Provider class to handle domain
            
        Example:
            >>> class CustomProvider(BaseEmailProvider):
            ...     pass
            >>> detector = EmailProviderDetector()
            >>> detector.register_provider("custom.com", CustomProvider)
        """
        if not issubclass(provider_class, BaseEmailProvider):
            raise TypeError(
                f"{provider_class} must inherit from BaseEmailProvider"
            )
        
        self._PROVIDER_REGISTRY[domain.lower()] = provider_class
        
        if domain in self._cache:
            del self._cache[domain]
        
        logger.info(
            "provider_registered",
            domain=domain,
            provider=provider_class.__name__
        )
    
    def unregister_provider(self, domain: str) -> bool:
        """Remove provider registration for domain.
        
        Args:
            domain: Domain to unregister
            
        Returns:
            bool: True if provider was registered and removed
        """
        domain_lower = domain.lower()
        
        if domain_lower in self._PROVIDER_REGISTRY:
            del self._PROVIDER_REGISTRY[domain_lower]
            
            if domain_lower in self._cache:
                del self._cache[domain_lower]
            
            logger.info("provider_unregistered", domain=domain)
            return True
        
        return False
    
    def clear_cache(self):
        """Clear provider instance cache."""
        self._cache.clear()
        logger.debug("provider_cache_cleared")
    
    def _extract_domain(self, email_address: str) -> str:
        """Extract domain from email address.
        
        Args:
            email_address: Email address
            
        Returns:
            str: Domain part in lowercase
        """
        _, domain = email_address.rsplit("@", 1)
        return domain.lower().strip()
    
    def get_statistics(self) -> Dict[str, int]:
        """Get detector statistics.
        
        Returns:
            Dict: Statistics including counts
        """
        return {
            "registered_providers": len(self._PROVIDER_REGISTRY),
            "cached_instances": len(self._cache),
            "supported_domains": len(self._PROVIDER_REGISTRY)
        }


def create_provider_for_email(email_address: str) -> Optional[BaseEmailProvider]:
    """Convenience function to create provider for email address.
    
    Args:
        email_address: Email address
        
    Returns:
        Optional[BaseEmailProvider]: Provider instance or None
        
    Example:
        >>> provider = create_provider_for_email("user@wp.pl")
        >>> if provider:
        ...     result = await provider.authenticate_user(credentials)
    """
    detector = EmailProviderDetector()
    return detector.detect_provider(email_address)


def get_supported_domains() -> list[str]:
    """Get list of all supported email domains.
    
    Returns:
        list[str]: Sorted list of supported domains
    """
    detector = EmailProviderDetector()
    return detector.list_supported_domains()
