"""Custom exception hierarchy for the Facebook automation system.

This module defines all custom exceptions used throughout the application,
organized in a clear hierarchy for better error handling and reporting.
"""

from typing import Any, Optional


class BaseAutomationException(Exception):
    """Base exception for all automation-related errors.
    
    All custom exceptions in the system inherit from this base class
    to allow for consistent error handling and categorization.
    
    Attributes:
        message: Human-readable error message.
        code: Optional error code for categorization.
        details: Optional additional context about the error.
    """
    
    def __init__(
        self,
        message: str,
        code: Optional[str] = None,
        details: Optional[dict[str, Any]] = None
    ) -> None:
        """Initialize base automation exception.
        
        Args:
            message: Human-readable error message.
            code: Optional error code for categorization.
            details: Optional additional context about the error.
        """
        self.message = message
        self.code = code or self.__class__.__name__
        self.details = details or {}
        super().__init__(self.message)
    
    def __str__(self) -> str:
        """Return string representation of the exception."""
        if self.details:
            return f"{self.code}: {self.message} | Details: {self.details}"
        return f"{self.code}: {self.message}"
    
    def to_dict(self) -> dict[str, Any]:
        """Convert exception to dictionary for JSON serialization.
        
        Returns:
            dict: Exception data as dictionary.
        """
        return {
            "error": self.code,
            "message": self.message,
            "details": self.details
        }


# Proxy-related Exceptions
class ProxyException(BaseAutomationException):
    """Base exception for proxy-related errors."""
    pass


class InvalidProxyFormat(ProxyException):
    """Exception raised when proxy format is invalid.
    
    Raised when a proxy string cannot be parsed or is in an
    incorrect format (e.g., missing host, port, or credentials).
    """
    
    def __init__(self, proxy_string: str, reason: Optional[str] = None) -> None:
        """Initialize invalid proxy format exception.
        
        Args:
            proxy_string: The invalid proxy string.
            reason: Optional reason why the format is invalid.
        """
        message = f"Invalid proxy format: {proxy_string}"
        if reason:
            message += f" - {reason}"
        super().__init__(
            message=message,
            code="INVALID_PROXY_FORMAT",
            details={"proxy_string": proxy_string, "reason": reason}
        )


class ProxyConnectionError(ProxyException):
    """Exception raised when unable to connect to proxy server.
    
    Raised when a connection attempt to a proxy server fails,
    indicating the proxy may be offline or unreachable.
    """
    
    def __init__(self, proxy_host: str, proxy_port: int, reason: Optional[str] = None) -> None:
        """Initialize proxy connection error exception.
        
        Args:
            proxy_host: The proxy server hostname or IP.
            proxy_port: The proxy server port.
            reason: Optional reason for connection failure.
        """
        message = f"Failed to connect to proxy {proxy_host}:{proxy_port}"
        if reason:
            message += f" - {reason}"
        super().__init__(
            message=message,
            code="PROXY_CONNECTION_ERROR",
            details={"proxy_host": proxy_host, "proxy_port": proxy_port, "reason": reason}
        )


class ProxyTimeoutError(ProxyException):
    """Exception raised when proxy connection times out.
    
    Raised when a proxy connection or request exceeds the
    configured timeout threshold.
    """
    
    def __init__(self, proxy_host: str, timeout: int) -> None:
        """Initialize proxy timeout error exception.
        
        Args:
            proxy_host: The proxy server hostname or IP.
            timeout: The timeout value in seconds.
        """
        message = f"Proxy connection to {proxy_host} timed out after {timeout}s"
        super().__init__(
            message=message,
            code="PROXY_TIMEOUT_ERROR",
            details={"proxy_host": proxy_host, "timeout_seconds": timeout}
        )


# Email-related Exceptions
class EmailException(BaseAutomationException):
    """Base exception for email-related errors."""
    pass


class EmailProviderError(EmailException):
    """Exception raised when email provider encounters an error.
    
    Raised when there's an issue communicating with the email
    provider (e.g., Gmail, Outlook) or their API.
    """
    
    def __init__(self, provider: str, reason: str) -> None:
        """Initialize email provider error exception.
        
        Args:
            provider: The email provider name.
            reason: The reason for the error.
        """
        message = f"Email provider '{provider}' error: {reason}"
        super().__init__(
            message=message,
            code="EMAIL_PROVIDER_ERROR",
            details={"provider": provider, "reason": reason}
        )


class IMAPConnectionError(EmailException):
    """Exception raised when IMAP connection fails.
    
    Raised when unable to establish or maintain an IMAP
    connection to the email server.
    """
    
    def __init__(self, server: str, port: int, reason: Optional[str] = None) -> None:
        """Initialize IMAP connection error exception.
        
        Args:
            server: The IMAP server hostname.
            port: The IMAP server port.
            reason: Optional reason for connection failure.
        """
        message = f"Failed to connect to IMAP server {server}:{port}"
        if reason:
            message += f" - {reason}"
        super().__init__(
            message=message,
            code="IMAP_CONNECTION_ERROR",
            details={"server": server, "port": port, "reason": reason}
        )


class EmailParseError(EmailException):
    """Exception raised when unable to parse email content.
    
    Raised when email content cannot be parsed or verification
    code cannot be extracted from the email.
    """
    
    def __init__(self, email_id: str, reason: str) -> None:
        """Initialize email parse error exception.
        
        Args:
            email_id: The email identifier or subject.
            reason: The reason for parse failure.
        """
        message = f"Failed to parse email '{email_id}': {reason}"
        super().__init__(
            message=message,
            code="EMAIL_PARSE_ERROR",
            details={"email_id": email_id, "reason": reason}
        )


# Facebook-related Exceptions
class FacebookException(BaseAutomationException):
    """Base exception for Facebook-related errors."""
    pass


class LoginFailedError(FacebookException):
    """Exception raised when Facebook login fails.
    
    Raised when unable to complete Facebook login, which could
    be due to incorrect credentials, account issues, or automation detection.
    """
    
    def __init__(self, email: str, reason: str, attempts: int = 1) -> None:
        """Initialize login failed error exception.
        
        Args:
            email: The email/username used for login.
            reason: The reason for login failure.
            attempts: Number of login attempts made.
        """
        message = f"Facebook login failed for '{email}': {reason}"
        super().__init__(
            message=message,
            code="LOGIN_FAILED_ERROR",
            details={"email": email, "reason": reason, "attempts": attempts}
        )


class SecurityCheckError(FacebookException):
    """Exception raised when Facebook security check is encountered.
    
    Raised when Facebook presents a security checkpoint that
    requires additional verification (e.g., phone number, ID verification).
    """
    
    def __init__(self, checkpoint_type: str, email: str) -> None:
        """Initialize security check error exception.
        
        Args:
            checkpoint_type: Type of security checkpoint encountered.
            email: The email/username that triggered the checkpoint.
        """
        message = f"Facebook security checkpoint '{checkpoint_type}' for '{email}'"
        super().__init__(
            message=message,
            code="SECURITY_CHECK_ERROR",
            details={"checkpoint_type": checkpoint_type, "email": email}
        )


class CaptchaError(FacebookException):
    """Exception raised when CAPTCHA is encountered.
    
    Raised when Facebook presents a CAPTCHA challenge that
    needs to be solved before proceeding.
    """
    
    def __init__(self, captcha_type: str = "unknown") -> None:
        """Initialize CAPTCHA error exception.
        
        Args:
            captcha_type: Type of CAPTCHA encountered (e.g., reCAPTCHA, hCaptcha).
        """
        message = f"CAPTCHA challenge encountered: {captcha_type}"
        super().__init__(
            message=message,
            code="CAPTCHA_ERROR",
            details={"captcha_type": captcha_type}
        )


class AccountBannedError(FacebookException):
    """Exception raised when Facebook account is banned or disabled.
    
    Raised when attempting to use an account that has been
    banned, disabled, or suspended by Facebook.
    """
    
    def __init__(self, email: str, reason: Optional[str] = None) -> None:
        """Initialize account banned error exception.
        
        Args:
            email: The email/username of the banned account.
            reason: Optional reason for the ban if known.
        """
        message = f"Facebook account '{email}' is banned or disabled"
        if reason:
            message += f": {reason}"
        super().__init__(
            message=message,
            code="ACCOUNT_BANNED_ERROR",
            details={"email": email, "reason": reason}
        )


class SessionExpiredError(FacebookException):
    """Exception raised when Facebook session expires.
    
    Raised when a stored Facebook session is no longer valid
    and requires re-authentication.
    """
    
    def __init__(self, session_id: str) -> None:
        """Initialize session expired error exception.
        
        Args:
            session_id: The identifier of the expired session.
        """
        message = f"Facebook session '{session_id}' has expired"
        super().__init__(
            message=message,
            code="SESSION_EXPIRED_ERROR",
            details={"session_id": session_id}
        )


# Validation Exceptions
class ValidationException(BaseAutomationException):
    """Exception raised for validation errors.
    
    Raised when input validation fails or data doesn't meet
    required constraints or formats.
    """
    
    def __init__(self, field: str, message: str, value: Any = None) -> None:
        """Initialize validation exception.
        
        Args:
            field: The field name that failed validation.
            message: Description of the validation error.
            value: Optional invalid value that was provided.
        """
        full_message = f"Validation error for field '{field}': {message}"
        super().__init__(
            message=full_message,
            code="VALIDATION_ERROR",
            details={"field": field, "value": value, "message": message}
        )


# Database Exceptions
class DatabaseException(BaseAutomationException):
    """Base exception for database-related errors."""
    pass


class RecordNotFoundError(DatabaseException):
    """Exception raised when a database record is not found.
    
    Raised when a query for a specific record returns no results.
    """
    
    def __init__(self, model: str, identifier: Any) -> None:
        """Initialize record not found error exception.
        
        Args:
            model: The model/table name being queried.
            identifier: The identifier used in the query.
        """
        message = f"Record not found in '{model}' with identifier: {identifier}"
        super().__init__(
            message=message,
            code="RECORD_NOT_FOUND",
            details={"model": model, "identifier": identifier}
        )


class DuplicateRecordError(DatabaseException):
    """Exception raised when attempting to create a duplicate record.
    
    Raised when a unique constraint violation occurs during insertion.
    """
    
    def __init__(self, model: str, field: str, value: Any) -> None:
        """Initialize duplicate record error exception.
        
        Args:
            model: The model/table name where duplication occurred.
            field: The field with unique constraint.
            value: The duplicate value.
        """
        message = f"Duplicate record in '{model}': {field}='{value}' already exists"
        super().__init__(
            message=message,
            code="DUPLICATE_RECORD",
            details={"model": model, "field": field, "value": value}
        )


class DatabaseConnectionError(DatabaseException):
    """Exception raised when database connection fails.
    
    Raised when unable to establish or maintain a connection
    to the database server.
    """
    
    def __init__(self, reason: str) -> None:
        """Initialize database connection error exception.
        
        Args:
            reason: The reason for connection failure.
        """
        message = f"Database connection error: {reason}"
        super().__init__(
            message=message,
            code="DATABASE_CONNECTION_ERROR",
            details={"reason": reason}
        )
