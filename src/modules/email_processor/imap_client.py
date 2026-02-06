"""IMAP client for email retrieval and management.

This module provides an async IMAP client for connecting to email servers,
searching messages, fetching content, and managing read/unread status.
"""

import asyncio
import email
import imaplib
import socket
from datetime import datetime, timezone
from email.header import decode_header
from email.utils import parsedate_to_datetime
from typing import Optional

from src.core.config import settings
from src.core.exceptions import IMAPConnectionError, EmailParseError
from src.core.logging import get_logger
from src.modules.email_discovery.models import IMAPConfig
from src.modules.email_processor.models import EmailMessage, SearchCriteria

logger = get_logger(__name__)


class IMAPClient:
    """IMAP client for email operations.
    
    Provides async interface for IMAP operations with SSL/TLS support,
    connection management, and comprehensive error handling.
    """
    
    def __init__(self, config: IMAPConfig, email_address: str, password: str) -> None:
        """Initialize IMAP client.
        
        Args:
            config: IMAP server configuration.
            email_address: Email account address.
            password: Email account password.
        """
        self.config = config
        self.email_address = email_address
        self.password = password
        self.connection: Optional[imaplib.IMAP4_SSL] = None
        self._connected = False
        logger.debug(
            "IMAPClient initialized",
            host=config.host,
            port=config.port,
            email=email_address
        )
    
    async def connect(self) -> None:
        """Connect to IMAP server with SSL/TLS.
        
        Raises:
            IMAPConnectionError: If connection fails.
        """
        if self._connected:
            logger.debug("Already connected to IMAP server")
            return
        
        try:
            logger.info(
                "Connecting to IMAP server",
                host=self.config.host,
                port=self.config.port
            )
            
            # Run in thread pool to avoid blocking
            loop = asyncio.get_event_loop()
            self.connection = await loop.run_in_executor(
                None,
                self._create_connection
            )
            
            self._connected = True
            logger.info("IMAP connection established", email=self.email_address)
            
        except (socket.gaierror, socket.timeout) as e:
            logger.error(
                "IMAP connection failed",
                host=self.config.host,
                error=str(e)
            )
            raise IMAPConnectionError(
                server=self.config.host,
                port=self.config.port,
                reason=str(e)
            )
        except imaplib.IMAP4.error as e:
            logger.error("IMAP authentication failed", error=str(e))
            raise IMAPConnectionError(
                server=self.config.host,
                port=self.config.port,
                reason=f"Authentication failed: {str(e)}"
            )
    
    def _create_connection(self) -> imaplib.IMAP4_SSL:
        """Create IMAP SSL connection (blocking).
        
        Returns:
            imaplib.IMAP4_SSL: Connected IMAP client.
        """
        if self.config.use_ssl:
            conn = imaplib.IMAP4_SSL(
                self.config.host,
                self.config.port,
                timeout=self.config.timeout_seconds
            )
        else:
            conn = imaplib.IMAP4(
                self.config.host,
                self.config.port,
                timeout=self.config.timeout_seconds
            )
        
        conn.login(self.email_address, self.password)
        conn.select("INBOX")
        
        return conn
    
    async def search_messages(
        self,
        criteria: Optional[SearchCriteria] = None
    ) -> list[str]:
        """Search for messages matching criteria.
        
        Args:
            criteria: Search criteria (optional).
        
        Returns:
            list[str]: List of message IDs matching criteria.
        
        Raises:
            IMAPConnectionError: If not connected or search fails.
        """
        if not self._connected or not self.connection:
            raise IMAPConnectionError(
                server=self.config.host,
                port=self.config.port,
                reason="Not connected"
            )
        
        # Build IMAP search query
        search_parts = []
        
        if criteria:
            if criteria.unread_only:
                search_parts.append("UNSEEN")
            
            if criteria.from_address:
                search_parts.append(f'FROM "{criteria.from_address}"')
            
            if criteria.since_date:
                date_str = criteria.since_date.strftime("%d-%b-%Y")
                search_parts.append(f"SINCE {date_str}")
            
            if criteria.subject_contains:
                search_parts.append(f'SUBJECT "{criteria.subject_contains}"')
        
        # Default to all messages if no criteria
        search_query = " ".join(search_parts) if search_parts else "ALL"
        
        try:
            logger.debug("Searching messages", query=search_query)
            
            loop = asyncio.get_event_loop()
            status, data = await loop.run_in_executor(
                None,
                self.connection.search,
                None,
                search_query
            )
            
            if status != "OK":
                raise IMAPConnectionError(
                    server=self.config.host,
                    port=self.config.port,
                    reason=f"Search failed: {status}"
                )
            
            message_ids = data[0].split()
            logger.info("Messages found", count=len(message_ids))
            
            return [msg_id.decode() for msg_id in message_ids]
            
        except imaplib.IMAP4.error as e:
            logger.error("IMAP search failed", error=str(e))
            raise IMAPConnectionError(
                server=self.config.host,
                port=self.config.port,
                reason=f"Search failed: {str(e)}"
            )
    
    async def fetch_message(self, message_id: str) -> EmailMessage:
        """Fetch and parse email message.
        
        Args:
            message_id: Message ID to fetch.
        
        Returns:
            EmailMessage: Parsed email message.
        
        Raises:
            IMAPConnectionError: If fetch fails.
            EmailParseError: If parsing fails.
        """
        if not self._connected or not self.connection:
            raise IMAPConnectionError(
                server=self.config.host,
                port=self.config.port,
                reason="Not connected"
            )
        
        try:
            logger.debug("Fetching message", message_id=message_id)
            
            loop = asyncio.get_event_loop()
            status, data = await loop.run_in_executor(
                None,
                self.connection.fetch,
                message_id,
                "(RFC822)"
            )
            
            if status != "OK":
                raise IMAPConnectionError(
                    server=self.config.host,
                    port=self.config.port,
                    reason=f"Fetch failed: {status}"
                )
            
            raw_email = data[0][1]
            msg = email.message_from_bytes(raw_email)
            
            return self._parse_message(message_id, msg)
            
        except imaplib.IMAP4.error as e:
            logger.error("IMAP fetch failed", error=str(e))
            raise IMAPConnectionError(
                server=self.config.host,
                port=self.config.port,
                reason=f"Fetch failed: {str(e)}"
            )
    
    def _parse_message(self, message_id: str, msg: email.message.Message) -> EmailMessage:
        """Parse email message object.
        
        Args:
            message_id: Message ID.
            msg: Email message object.
        
        Returns:
            EmailMessage: Parsed email message.
        
        Raises:
            EmailParseError: If parsing fails.
        """
        try:
            # Decode headers
            from_addr = self._decode_header(msg.get("From", ""))
            to_addr = self._decode_header(msg.get("To", ""))
            subject = self._decode_header(msg.get("Subject", ""))
            
            # Parse date
            date_str = msg.get("Date")
            if date_str:
                email_date = parsedate_to_datetime(date_str)
            else:
                email_date = datetime.now(timezone.utc)
            
            # Extract body
            body_text = ""
            body_html = None
            
            if msg.is_multipart():
                for part in msg.walk():
                    content_type = part.get_content_type()
                    
                    if content_type == "text/plain":
                        charset = part.get_content_charset() or "utf-8"
                        body_text = part.get_payload(decode=True).decode(charset, errors="ignore")
                    elif content_type == "text/html":
                        charset = part.get_content_charset() or "utf-8"
                        body_html = part.get_payload(decode=True).decode(charset, errors="ignore")
            else:
                charset = msg.get_content_charset() or "utf-8"
                body_text = msg.get_payload(decode=True).decode(charset, errors="ignore")
            
            # Extract headers
            headers = {key: self._decode_header(value) for key, value in msg.items()}
            
            return EmailMessage(
                id=message_id,
                from_addr=from_addr,
                to_addr=to_addr,
                subject=subject,
                body_text=body_text,
                body_html=body_html,
                date=email_date,
                headers=headers
            )
            
        except Exception as e:
            logger.error("Failed to parse email", message_id=message_id, error=str(e))
            raise EmailParseError(
                email_id=message_id,
                reason=str(e)
            )
    
    def _decode_header(self, header: str) -> str:
        """Decode email header with charset handling.
        
        Args:
            header: Raw header string.
        
        Returns:
            str: Decoded header.
        """
        decoded_parts = []
        for part, encoding in decode_header(header):
            if isinstance(part, bytes):
                decoded_parts.append(
                    part.decode(encoding or "utf-8", errors="ignore")
                )
            else:
                decoded_parts.append(part)
        
        return "".join(decoded_parts)
    
    async def mark_as_read(self, message_id: str) -> None:
        """Mark message as read.
        
        Args:
            message_id: Message ID to mark.
        
        Raises:
            IMAPConnectionError: If operation fails.
        """
        if not self._connected or not self.connection:
            raise IMAPConnectionError(
                server=self.config.host,
                port=self.config.port,
                reason="Not connected"
            )
        
        try:
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(
                None,
                self.connection.store,
                message_id,
                "+FLAGS",
                "\\Seen"
            )
            logger.debug("Message marked as read", message_id=message_id)
            
        except imaplib.IMAP4.error as e:
            logger.error("Failed to mark message as read", error=str(e))
            raise IMAPConnectionError(
                server=self.config.host,
                port=self.config.port,
                reason=f"Mark as read failed: {str(e)}"
            )
    
    async def mark_as_unread(self, message_id: str) -> None:
        """Mark message as unread.
        
        Args:
            message_id: Message ID to mark.
        
        Raises:
            IMAPConnectionError: If operation fails.
        """
        if not self._connected or not self.connection:
            raise IMAPConnectionError(
                server=self.config.host,
                port=self.config.port,
                reason="Not connected"
            )
        
        try:
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(
                None,
                self.connection.store,
                message_id,
                "-FLAGS",
                "\\Seen"
            )
            logger.debug("Message marked as unread", message_id=message_id)
            
        except imaplib.IMAP4.error as e:
            logger.error("Failed to mark message as unread", error=str(e))
            raise IMAPConnectionError(
                server=self.config.host,
                port=self.config.port,
                reason=f"Mark as unread failed: {str(e)}"
            )
    
    async def close(self) -> None:
        """Close IMAP connection."""
        if self._connected and self.connection:
            try:
                loop = asyncio.get_event_loop()
                await loop.run_in_executor(None, self.connection.close)
                await loop.run_in_executor(None, self.connection.logout)
                logger.info("IMAP connection closed", email=self.email_address)
            except Exception as e:
                logger.warning("Error closing IMAP connection", error=str(e))
            finally:
                self._connected = False
                self.connection = None
    
    async def __aenter__(self) -> "IMAPClient":
        """Async context manager entry."""
        await self.connect()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Async context manager exit."""
        await self.close()
