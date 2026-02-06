"""Custom exceptions for the application."""


class AccountAutomationException(Exception):
    """Base exception for account automation system."""
    pass


class ProxyConnectionError(AccountAutomationException):
    """Raised when proxy connection fails."""
    pass


class EmailLoginFailedError(AccountAutomationException):
    """Raised when email login fails."""
    pass


class TwoFactorCodeNotFoundError(AccountAutomationException):
    """Raised when 2FA code is not found in email."""
    pass


class IMAPConnectionError(AccountAutomationException):
    """Raised when IMAP connection fails."""
    pass


class FacebookAutomationError(AccountAutomationException):
    """Raised when Facebook automation fails."""
    pass


class PasswordResetError(AccountAutomationException):
    """Raised when password reset fails."""
    pass


class EmailProviderError(AccountAutomationException):
    """Raised when email provider operation fails."""
    pass


class ValidationError(AccountAutomationException):
    """Raised when validation fails."""
    pass


class DatabaseError(AccountAutomationException):
    """Raised when database operation fails."""
    pass


class EncryptionError(AccountAutomationException):
    """Raised when encryption/decryption fails."""
    pass
