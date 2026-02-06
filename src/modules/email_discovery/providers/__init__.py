"""Email provider modules export.

This module exports all email provider implementations for easy importing.
"""

from .base import (
    BaseEmailProvider,
    ProviderAuthenticationError,
    ProviderConfigurationError,
    ProviderNetworkError
)
from .wp_pl import WPEmailProvider
from .o2_pl import O2EmailProvider
from .onet_pl import OnetEmailProvider
from .op_pl import OPEmailProvider
from .interia_pl import InteriaEmailProvider


__all__ = [
    "BaseEmailProvider",
    "ProviderAuthenticationError",
    "ProviderConfigurationError",
    "ProviderNetworkError",
    "WPEmailProvider",
    "O2EmailProvider",
    "OnetEmailProvider",
    "OPEmailProvider",
    "InteriaEmailProvider",
]
