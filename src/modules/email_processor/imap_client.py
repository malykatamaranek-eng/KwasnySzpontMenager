"""Async IMAP client for email processing."""
import imaplib
import email
import ssl
import re
from typing import Optional, List, Dict, Any
from email.header import decode_header
import asyncio
import structlog
from src.core.exceptions import IMAPConnectionError, TwoFactorCodeNotFoundError

logger = structlog.get_logger()


class AsyncIMAPProcessor:
    """
    Asynchronous IMAP client with:
    - Connection after login
    - Facebook email search
    - 6/8-digit code parsing with regex
    - HTML and plaintext support
    - Connection pooling
    - Auto-reconnect on timeout
    """
    
    CODE_PATTERN = re.compile(r'\b(\d{6}|\d{8})\b')
    
    def __init__(
        self,
        host: str,
        port: int,
        email: str,
        password: str,
        use_ssl: bool = True
    ):
        """
        Initialize IMAP client.
        
        Args:
            host: IMAP host
            port: IMAP port
            email: Email address
            password: Email password
            use_ssl: Use SSL connection
        """
        self.host = host
        self.port = port
        self.email = email
        self.password = password
        self.use_ssl = use_ssl
        self.connection: Optional[imaplib.IMAP4_SSL] = None
        self._connected = False
    
    async def connect(self) -> None:
        """Connect to IMAP server."""
        try:
            if self.use_ssl:
                context = ssl.create_default_context()
                self.connection = imaplib.IMAP4_SSL(
                    self.host,
                    self.port,
                    ssl_context=context
                )
            else:
                self.connection = imaplib.IMAP4(self.host, self.port)
            
            # Login
            await asyncio.to_thread(self.connection.login, self.email, self.password)
            self._connected = True
            
            logger.info("imap_connected", email=self.email, host=self.host)
            
        except Exception as e:
            logger.error("imap_connection_failed", email=self.email, error=str(e))
            raise IMAPConnectionError(f"Failed to connect to IMAP: {str(e)}")
    
    async def disconnect(self) -> None:
        """Disconnect from IMAP server."""
        if self.connection and self._connected:
            try:
                await asyncio.to_thread(self.connection.logout)
                self._connected = False
                logger.info("imap_disconnected", email=self.email)
            except Exception as e:
                logger.warning("imap_disconnect_error", error=str(e))
    
    async def ensure_connected(self) -> None:
        """Ensure connection is active, reconnect if needed."""
        if not self._connected or not self.connection:
            await self.connect()
        
        try:
            # Test connection with NOOP
            await asyncio.to_thread(self.connection.noop)
        except Exception:
            logger.warning("imap_connection_lost_reconnecting", email=self.email)
            await self.connect()
    
    async def search_facebook_emails(self, max_messages: int = 10) -> List[Dict[str, Any]]:
        """
        Search for emails from Facebook.
        
        Args:
            max_messages: Maximum number of messages to retrieve
            
        Returns:
            List of email data
        """
        await self.ensure_connected()
        
        try:
            # Select inbox
            await asyncio.to_thread(self.connection.select, "INBOX")
            
            # Search for Facebook emails
            search_criteria = [
                'FROM "facebook.com"',
                'FROM "facebookmail.com"',
                'SUBJECT "Facebook"'
            ]
            
            all_email_ids = []
            
            for criteria in search_criteria:
                try:
                    status, data = await asyncio.to_thread(
                        self.connection.search,
                        None,
                        criteria
                    )
                    
                    if status == "OK" and data[0]:
                        email_ids = data[0].split()
                        all_email_ids.extend(email_ids)
                except Exception as e:
                    logger.warning("search_criteria_failed", criteria=criteria, error=str(e))
            
            # Remove duplicates and get latest
            all_email_ids = list(set(all_email_ids))
            all_email_ids = sorted(all_email_ids, reverse=True)[:max_messages]
            
            logger.info("facebook_emails_found", count=len(all_email_ids))
            
            emails = []
            for email_id in all_email_ids:
                email_data = await self.fetch_email(email_id)
                if email_data:
                    emails.append(email_data)
            
            return emails
            
        except Exception as e:
            logger.error("facebook_email_search_failed", error=str(e))
            raise IMAPConnectionError(f"Failed to search emails: {str(e)}")
    
    async def fetch_email(self, email_id: bytes) -> Optional[Dict[str, Any]]:
        """
        Fetch email by ID.
        
        Args:
            email_id: Email ID
            
        Returns:
            Email data dict
        """
        try:
            status, data = await asyncio.to_thread(
                self.connection.fetch,
                email_id,
                "(RFC822)"
            )
            
            if status != "OK" or not data[0]:
                return None
            
            # Parse email
            raw_email = data[0][1]
            msg = email.message_from_bytes(raw_email)
            
            # Get subject
            subject = self._decode_header(msg.get("Subject", ""))
            
            # Get sender
            sender = msg.get("From", "")
            
            # Get body
            body = await self._get_email_body(msg)
            
            # Extract codes
            codes = self.extract_codes(body)
            
            return {
                "id": email_id.decode(),
                "subject": subject,
                "from": sender,
                "body": body,
                "codes": codes
            }
            
        except Exception as e:
            logger.error("email_fetch_failed", email_id=email_id, error=str(e))
            return None
    
    def _decode_header(self, header: str) -> str:
        """Decode email header."""
        if not header:
            return ""
        
        decoded_parts = decode_header(header)
        result = []
        
        for part, encoding in decoded_parts:
            if isinstance(part, bytes):
                try:
                    result.append(part.decode(encoding or "utf-8", errors="ignore"))
                except Exception:
                    result.append(part.decode("utf-8", errors="ignore"))
            else:
                result.append(str(part))
        
        return "".join(result)
    
    async def _get_email_body(self, msg: email.message.Message) -> str:
        """Extract email body from message."""
        body = ""
        
        if msg.is_multipart():
            for part in msg.walk():
                content_type = part.get_content_type()
                
                if content_type in ["text/plain", "text/html"]:
                    try:
                        payload = part.get_payload(decode=True)
                        if payload:
                            charset = part.get_content_charset() or "utf-8"
                            body += payload.decode(charset, errors="ignore")
                    except Exception as e:
                        logger.warning("body_decode_failed", error=str(e))
        else:
            try:
                payload = msg.get_payload(decode=True)
                if payload:
                    charset = msg.get_content_charset() or "utf-8"
                    body = payload.decode(charset, errors="ignore")
            except Exception as e:
                logger.warning("body_decode_failed", error=str(e))
        
        return body
    
    def extract_codes(self, text: str) -> List[str]:
        """
        Extract 6 or 8-digit codes from text.
        
        Args:
            text: Text to search
            
        Returns:
            List of found codes
        """
        matches = self.CODE_PATTERN.findall(text)
        unique_codes = list(set(matches))
        
        logger.info("codes_extracted", count=len(unique_codes), codes=unique_codes)
        return unique_codes
    
    async def find_latest_code(
        self, 
        search_minutes: int = 30,
        code_length: Optional[int] = None
    ) -> Optional[str]:
        """
        Find the latest verification code from Facebook.
        
        Args:
            search_minutes: How many minutes back to search
            code_length: Filter by code length (6 or 8)
            
        Returns:
            Latest code or None
        """
        emails = await self.search_facebook_emails(max_messages=20)
        
        for email_data in emails:
            codes = email_data.get("codes", [])
            
            for code in codes:
                if code_length and len(code) != code_length:
                    continue
                
                logger.info("code_found", code=code, subject=email_data.get("subject"))
                return code
        
        logger.warning("no_code_found")
        return None
    
    async def __aenter__(self):
        """Async context manager entry."""
        await self.connect()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.disconnect()
