"""Email processor module for verification code extraction.

This module provides functionality for:
- IMAP email client operations
- Email parsing and code extraction
- Email search and filtering
"""

from src.modules.email_processor.imap_client import IMAPClient
from src.modules.email_processor.models import CodeMatch, EmailMessage, SearchCriteria
from src.modules.email_processor.parser import CodeParser

__all__ = [
    "IMAPClient",
    "CodeParser",
    "EmailMessage",
    "CodeMatch",
    "SearchCriteria",
]
