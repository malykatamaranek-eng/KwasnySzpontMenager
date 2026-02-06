"""Structured logging configuration for the Facebook automation system.

This module configures structured logging using structlog, providing
JSON-formatted logs with context and request tracking.
"""

import logging
import sys
from typing import Any, Optional

import structlog
from structlog.types import EventDict, Processor

from src.core.config import settings


def add_app_context(logger: Any, method_name: str, event_dict: EventDict) -> EventDict:
    """Add application context to log entries.
    
    Args:
        logger: The logger instance.
        method_name: The name of the logging method called.
        event_dict: The event dictionary to modify.
    
    Returns:
        EventDict: Modified event dictionary with app context.
    """
    event_dict["app"] = settings.app_name
    event_dict["environment"] = settings.environment
    return event_dict


def add_log_level(logger: Any, method_name: str, event_dict: EventDict) -> EventDict:
    """Add log level to event dictionary.
    
    Args:
        logger: The logger instance.
        method_name: The name of the logging method called.
        event_dict: The event dictionary to modify.
    
    Returns:
        EventDict: Modified event dictionary with log level.
    """
    if method_name == "warn":
        method_name = "warning"
    event_dict["level"] = method_name.upper()
    return event_dict


def censor_sensitive_data(logger: Any, method_name: str, event_dict: EventDict) -> EventDict:
    """Censor sensitive data in log entries.
    
    Replaces sensitive field values with masked strings to prevent
    accidental logging of passwords, tokens, etc.
    
    Args:
        logger: The logger instance.
        method_name: The name of the logging method called.
        event_dict: The event dictionary to modify.
    
    Returns:
        EventDict: Modified event dictionary with censored data.
    """
    sensitive_fields = {
        "password", "token", "secret", "key", "authorization",
        "cookie", "session", "api_key", "access_token", "refresh_token"
    }
    
    for key, value in event_dict.items():
        if any(sensitive in key.lower() for sensitive in sensitive_fields):
            if isinstance(value, str) and len(value) > 0:
                # Completely mask sensitive data
                event_dict[key] = "***REDACTED***"
    
    return event_dict


def configure_logging(
    log_level: Optional[str] = None,
    log_format: Optional[str] = None,
    log_file: Optional[str] = None
) -> None:
    """Configure structured logging for the application.
    
    Sets up structlog with appropriate processors for the specified
    format (JSON or console) and configures standard library logging.
    
    Args:
        log_level: The logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL).
            If not provided, uses value from settings.
        log_format: The log format ('json' or 'console').
            If not provided, uses value from settings.
        log_file: Optional file path to write logs to.
            If not provided, uses value from settings.
    """
    level = log_level or settings.log_level
    format_type = log_format or settings.log_format
    file_path = log_file or settings.log_file
    
    # Convert string level to logging constant
    numeric_level = getattr(logging, level.upper(), logging.INFO)
    
    # Configure standard library logging
    logging.basicConfig(
        format="%(message)s",
        level=numeric_level,
        stream=sys.stdout,
    )
    
    # Configure additional file handler if specified
    if file_path:
        file_handler = logging.FileHandler(file_path)
        file_handler.setLevel(numeric_level)
        logging.root.addHandler(file_handler)
    
    # Define processors for structlog
    shared_processors: list[Processor] = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_logger_name,
        add_log_level,
        add_app_context,
        censor_sensitive_data,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
    ]
    
    if format_type == "json":
        # JSON format for production
        processors = shared_processors + [
            structlog.processors.format_exc_info,
            structlog.processors.JSONRenderer()
        ]
    else:
        # Console format for development
        processors = shared_processors + [
            structlog.processors.ExceptionPrettyPrinter(),
            structlog.dev.ConsoleRenderer(colors=True)
        ]
    
    # Configure structlog
    structlog.configure(
        processors=processors,
        wrapper_class=structlog.stdlib.BoundLogger,
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )


def get_logger(name: Optional[str] = None) -> structlog.stdlib.BoundLogger:
    """Get a structured logger instance.
    
    Args:
        name: Optional name for the logger. If not provided,
            uses the calling module's name.
    
    Returns:
        structlog.stdlib.BoundLogger: A configured logger instance.
    """
    return structlog.get_logger(name)


class RequestLogger:
    """Logger with request context support.
    
    Automatically adds request ID and other request-specific context
    to log entries for better traceability.
    """
    
    def __init__(self, request_id: Optional[str] = None) -> None:
        """Initialize request logger.
        
        Args:
            request_id: Optional request identifier for tracking.
        """
        self.logger = get_logger()
        self.request_id = request_id
        if request_id:
            self.logger = self.logger.bind(request_id=request_id)
    
    def bind(self, **kwargs: Any) -> "RequestLogger":
        """Bind additional context to the logger.
        
        Args:
            **kwargs: Key-value pairs to add to log context.
        
        Returns:
            RequestLogger: A new logger instance with bound context.
        """
        new_logger = RequestLogger(self.request_id)
        new_logger.logger = self.logger.bind(**kwargs)
        return new_logger
    
    def debug(self, event: str, **kwargs: Any) -> None:
        """Log debug message.
        
        Args:
            event: The event message.
            **kwargs: Additional context to log.
        """
        self.logger.debug(event, **kwargs)
    
    def info(self, event: str, **kwargs: Any) -> None:
        """Log info message.
        
        Args:
            event: The event message.
            **kwargs: Additional context to log.
        """
        self.logger.info(event, **kwargs)
    
    def warning(self, event: str, **kwargs: Any) -> None:
        """Log warning message.
        
        Args:
            event: The event message.
            **kwargs: Additional context to log.
        """
        self.logger.warning(event, **kwargs)
    
    def error(self, event: str, **kwargs: Any) -> None:
        """Log error message.
        
        Args:
            event: The event message.
            **kwargs: Additional context to log.
        """
        self.logger.error(event, **kwargs)
    
    def critical(self, event: str, **kwargs: Any) -> None:
        """Log critical message.
        
        Args:
            event: The event message.
            **kwargs: Additional context to log.
        """
        self.logger.critical(event, **kwargs)
    
    def exception(self, event: str, **kwargs: Any) -> None:
        """Log exception with traceback.
        
        Args:
            event: The event message.
            **kwargs: Additional context to log.
        """
        self.logger.exception(event, **kwargs)


# Initialize logging on module import
configure_logging()
