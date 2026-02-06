"""Code extraction and parsing from email messages.

This module provides functionality to extract verification codes from emails
using multiple regex patterns with confidence scoring.
"""

import re
from typing import Optional

from src.core.logging import get_logger
from src.modules.email_processor.models import CodeMatch, EmailMessage

logger = get_logger(__name__)


class CodeParser:
    """Extract verification codes from email messages.
    
    Supports multiple code formats with confidence-based ranking:
    - 6-digit codes
    - 8-digit codes
    - Context-aware patterns (code:, verification:, etc.)
    """
    
    # Pattern definitions with confidence scores
    PATTERNS = [
        (r"(?:verification|confirmation|code)[\s:]+(\d{6,8})", 0.95),
        (r"(?:your code is|code is)[\s:]+(\d{6,8})", 0.90),
        (r"\b(\d{8})\b", 0.75),
        (r"\b(\d{6})\b", 0.70),
        (r"(?:login|access)[\s:]+(\d{6,8})", 0.85),
    ]
    
    def __init__(self) -> None:
        """Initialize code parser with compiled regex patterns."""
        self.compiled_patterns = [
            (re.compile(pattern, re.IGNORECASE), confidence)
            for pattern, confidence in self.PATTERNS
        ]
        logger.debug("CodeParser initialized", pattern_count=len(self.compiled_patterns))
    
    def parse_email(self, email: EmailMessage) -> list[CodeMatch]:
        """Parse email and extract all verification codes.
        
        Args:
            email: Email message to parse.
        
        Returns:
            list[CodeMatch]: All code matches found, sorted by confidence.
        """
        matches = []
        
        # Search subject
        matches.extend(self._search_text(email.subject, "subject"))
        
        # Search plain text body
        matches.extend(self._search_text(email.body_text, "body"))
        
        # Search HTML body if available
        if email.body_html:
            # Strip HTML tags for simpler matching
            html_text = re.sub(r"<[^>]+>", " ", email.body_html)
            matches.extend(self._search_text(html_text, "body"))
        
        # Sort by confidence and remove duplicates
        matches = self._deduplicate_matches(matches)
        matches.sort(key=lambda m: m.confidence, reverse=True)
        
        logger.info(
            "Email parsed for codes",
            email_id=email.id,
            matches_found=len(matches)
        )
        
        return matches
    
    def _search_text(self, text: str, location: str) -> list[CodeMatch]:
        """Search text with all patterns.
        
        Args:
            text: Text to search.
            location: Location identifier (subject/body).
        
        Returns:
            list[CodeMatch]: All matches found in text.
        """
        matches = []
        
        for pattern, confidence in self.compiled_patterns:
            for match in pattern.finditer(text):
                code = match.group(1)
                matches.append(
                    CodeMatch(
                        code=code,
                        confidence=confidence,
                        location=location,
                        pattern_used=pattern.pattern
                    )
                )
        
        return matches
    
    def _deduplicate_matches(self, matches: list[CodeMatch]) -> list[CodeMatch]:
        """Remove duplicate codes, keeping highest confidence.
        
        Args:
            matches: List of code matches.
        
        Returns:
            list[CodeMatch]: Deduplicated matches.
        """
        seen = {}
        for match in matches:
            if match.code not in seen or match.confidence > seen[match.code].confidence:
                seen[match.code] = match
        
        return list(seen.values())
    
    def extract_facebook_code(self, email: EmailMessage) -> Optional[str]:
        """Extract verification code from Facebook email.
        
        Specialized extraction for Facebook verification emails
        with prioritized pattern matching.
        
        Args:
            email: Email message to parse.
        
        Returns:
            Optional[str]: Extracted code or None if not found.
        """
        # Check if email is from Facebook
        if "facebook" not in email.from_addr.lower() and "facebookmail" not in email.from_addr.lower():
            logger.warning(
                "Email not from Facebook",
                from_addr=email.from_addr,
                email_id=email.id
            )
        
        matches = self.parse_email(email)
        
        if not matches:
            logger.warning("No verification codes found", email_id=email.id)
            return None
        
        # Return highest confidence match
        best_match = matches[0]
        logger.info(
            "Facebook code extracted",
            code=best_match.code,
            confidence=best_match.confidence,
            location=best_match.location
        )
        
        return best_match.code
    
    def find_most_recent_code(self, emails: list[EmailMessage]) -> Optional[str]:
        """Find most recent verification code from list of emails.
        
        Args:
            emails: List of email messages to search.
        
        Returns:
            Optional[str]: Most recent code or None if not found.
        """
        if not emails:
            logger.warning("No emails provided for code extraction")
            return None
        
        # Sort by date descending
        sorted_emails = sorted(emails, key=lambda e: e.date, reverse=True)
        
        # Try each email until code found
        for email in sorted_emails:
            matches = self.parse_email(email)
            if matches:
                code = matches[0].code
                logger.info(
                    "Most recent code found",
                    code=code,
                    email_date=email.date,
                    email_id=email.id
                )
                return code
        
        logger.warning("No codes found in any email")
        return None
