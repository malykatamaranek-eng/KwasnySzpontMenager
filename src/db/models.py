"""SQLAlchemy 2.0 models for the Facebook automation system.

This module defines all database models using modern SQLAlchemy 2.0 syntax
with Mapped types for full type safety and better IDE support.
"""

from datetime import datetime
from enum import Enum as PyEnum
from typing import Optional

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    """Base class for all database models.
    
    Provides common functionality and type annotations for all models.
    """
    pass


class EmailProvider(str, PyEnum):
    """Supported email providers."""
    WP = "wp"
    O2 = "o2"
    ONET = "onet"
    OP = "op"
    INTERIA = "interia"


class EmailAccountStatus(str, PyEnum):
    """Email account validation status."""
    VALIDATED = "validated"
    INVALID = "invalid"
    ERROR = "error"


class FacebookAccountStatus(str, PyEnum):
    """Facebook account status."""
    PENDING = "pending"
    LOGGED_IN = "logged_in"
    SECURED = "secured"
    ERROR = "error"


class TaskStatus(str, PyEnum):
    """Task execution status."""
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"


class Proxy(Base):
    """Proxy server configuration and statistics.
    
    Stores proxy server information including connection details,
    performance metrics, and health status.
    
    Attributes:
        id: Primary key.
        host: Proxy server hostname or IP address.
        port: Proxy server port number.
        username: Optional proxy authentication username.
        password_encrypted: Encrypted proxy authentication password.
        protocol: Proxy protocol (default: socks5).
        is_active: Whether proxy is currently active.
        last_tested: Timestamp of last health check.
        latency_ms: Average latency in milliseconds.
        success_count: Number of successful connections.
        fail_count: Number of failed connections.
        created_at: Record creation timestamp.
        updated_at: Record last update timestamp.
    """
    
    __tablename__ = "proxies"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    host: Mapped[str] = mapped_column(String(255), nullable=False)
    port: Mapped[int] = mapped_column(Integer, nullable=False)
    username: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    password_encrypted: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    protocol: Mapped[str] = mapped_column(String(20), nullable=False, default="socks5")
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    last_tested: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    latency_ms: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    success_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    fail_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        server_default=func.now(),
        onupdate=func.now()
    )
    
    # Relationships
    tasks: Mapped[list["Task"]] = relationship(
        "Task",
        back_populates="proxy",
        lazy="selectin"
    )
    
    # Indexes
    __table_args__ = (
        Index("idx_proxy_active", "is_active"),
        Index("idx_proxy_host_port", "host", "port", unique=True),
    )
    
    def __repr__(self) -> str:
        """String representation of Proxy."""
        return f"<Proxy(id={self.id}, {self.protocol}://{self.host}:{self.port})>"


class EmailAccount(Base):
    """Email account for verification codes.
    
    Stores email account credentials and validation status for
    receiving Facebook verification codes.
    
    Attributes:
        id: Primary key.
        email: Email address (unique).
        password_encrypted: Encrypted email password.
        provider: Email provider (wp, o2, onet, op, interia).
        imap_host: IMAP server hostname.
        imap_port: IMAP server port.
        status: Account validation status.
        last_validated: Timestamp of last validation.
        session_data: JSON storage for session cookies/tokens.
        created_at: Record creation timestamp.
        updated_at: Record last update timestamp.
    """
    
    __tablename__ = "email_accounts"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    email: Mapped[str] = mapped_column(String(255), nullable=False, unique=True, index=True)
    password_encrypted: Mapped[str] = mapped_column(Text, nullable=False)
    provider: Mapped[EmailProvider] = mapped_column(
        Enum(EmailProvider),
        nullable=False
    )
    imap_host: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    imap_port: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    status: Mapped[EmailAccountStatus] = mapped_column(
        Enum(EmailAccountStatus),
        nullable=False,
        default=EmailAccountStatus.VALIDATED
    )
    last_validated: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    session_data: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        server_default=func.now(),
        onupdate=func.now()
    )
    
    # Relationships
    facebook_accounts: Mapped[list["FacebookAccount"]] = relationship(
        "FacebookAccount",
        back_populates="email_account",
        lazy="selectin"
    )
    
    # Indexes
    __table_args__ = (
        Index("idx_email_status", "status"),
        Index("idx_email_provider", "provider"),
    )
    
    def __repr__(self) -> str:
        """String representation of EmailAccount."""
        return f"<EmailAccount(id={self.id}, email={self.email}, provider={self.provider.value})>"


class FacebookAccount(Base):
    """Facebook account for automation.
    
    Stores Facebook account credentials, session data, and status
    for automated login and security alert handling.
    
    Attributes:
        id: Primary key.
        email_account_id: Foreign key to associated email account.
        fb_email: Facebook login email/username.
        fb_password_encrypted: Encrypted Facebook password.
        status: Account status (pending, logged_in, secured, error).
        cookies: JSON storage for browser cookies.
        last_login: Timestamp of last successful login.
        security_alerts_checked: Timestamp of last security alert check.
        created_at: Record creation timestamp.
        updated_at: Record last update timestamp.
    """
    
    __tablename__ = "facebook_accounts"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    email_account_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("email_accounts.id", ondelete="CASCADE"),
        nullable=False
    )
    fb_email: Mapped[str] = mapped_column(String(255), nullable=False, unique=True, index=True)
    fb_password_encrypted: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[FacebookAccountStatus] = mapped_column(
        Enum(FacebookAccountStatus),
        nullable=False,
        default=FacebookAccountStatus.PENDING
    )
    cookies: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    last_login: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    security_alerts_checked: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        server_default=func.now(),
        onupdate=func.now()
    )
    
    # Relationships
    email_account: Mapped["EmailAccount"] = relationship(
        "EmailAccount",
        back_populates="facebook_accounts",
        lazy="joined"
    )
    tasks: Mapped[list["Task"]] = relationship(
        "Task",
        back_populates="account",
        lazy="selectin"
    )
    security_alerts: Mapped[list["SecurityAlert"]] = relationship(
        "SecurityAlert",
        back_populates="account",
        lazy="selectin"
    )
    
    # Indexes
    __table_args__ = (
        Index("idx_fb_account_status", "status"),
        Index("idx_fb_account_email_account_id", "email_account_id"),
    )
    
    def __repr__(self) -> str:
        """String representation of FacebookAccount."""
        return f"<FacebookAccount(id={self.id}, fb_email={self.fb_email}, status={self.status.value})>"


class Task(Base):
    """Celery task execution tracking.
    
    Tracks the execution of automation tasks including status,
    errors, and execution logs.
    
    Attributes:
        id: Primary key.
        celery_task_id: Celery task identifier (unique).
        account_id: Foreign key to Facebook account.
        proxy_id: Foreign key to proxy (optional).
        status: Task execution status.
        started_at: Task start timestamp.
        completed_at: Task completion timestamp.
        error_message: Error message if task failed.
        logs: JSON list of execution logs.
        created_at: Record creation timestamp.
        updated_at: Record last update timestamp.
    """
    
    __tablename__ = "tasks"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    celery_task_id: Mapped[str] = mapped_column(String(255), nullable=False, unique=True, index=True)
    account_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("facebook_accounts.id", ondelete="CASCADE"),
        nullable=False
    )
    proxy_id: Mapped[Optional[int]] = mapped_column(
        Integer,
        ForeignKey("proxies.id", ondelete="SET NULL"),
        nullable=True
    )
    status: Mapped[TaskStatus] = mapped_column(
        Enum(TaskStatus),
        nullable=False,
        default=TaskStatus.PENDING
    )
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    logs: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        server_default=func.now(),
        onupdate=func.now()
    )
    
    # Relationships
    account: Mapped["FacebookAccount"] = relationship(
        "FacebookAccount",
        back_populates="tasks",
        lazy="joined"
    )
    proxy: Mapped[Optional["Proxy"]] = relationship(
        "Proxy",
        back_populates="tasks",
        lazy="joined"
    )
    
    # Indexes
    __table_args__ = (
        Index("idx_task_status", "status"),
        Index("idx_task_account_id", "account_id"),
        Index("idx_task_proxy_id", "proxy_id"),
        Index("idx_task_created_at", "created_at"),
    )
    
    def __repr__(self) -> str:
        """String representation of Task."""
        return f"<Task(id={self.id}, celery_task_id={self.celery_task_id}, status={self.status.value})>"


class SecurityAlert(Base):
    """Facebook security alert tracking.
    
    Stores detected security alerts from Facebook accounts for
    monitoring and handling.
    
    Attributes:
        id: Primary key.
        account_id: Foreign key to Facebook account.
        alert_type: Type of security alert.
        alert_data: JSON data containing alert details.
        detected_at: Timestamp when alert was detected.
        handled: Whether alert has been handled.
        handled_at: Timestamp when alert was handled.
    """
    
    __tablename__ = "security_alerts"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    account_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("facebook_accounts.id", ondelete="CASCADE"),
        nullable=False
    )
    alert_type: Mapped[str] = mapped_column(String(100), nullable=False)
    alert_data: Mapped[dict] = mapped_column(JSON, nullable=False)
    detected_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        server_default=func.now()
    )
    handled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    handled_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    
    # Relationships
    account: Mapped["FacebookAccount"] = relationship(
        "FacebookAccount",
        back_populates="security_alerts",
        lazy="joined"
    )
    
    # Indexes
    __table_args__ = (
        Index("idx_security_alert_account_id", "account_id"),
        Index("idx_security_alert_handled", "handled"),
        Index("idx_security_alert_type", "alert_type"),
        Index("idx_security_alert_detected_at", "detected_at"),
    )
    
    def __repr__(self) -> str:
        """String representation of SecurityAlert."""
        return f"<SecurityAlert(id={self.id}, account_id={self.account_id}, alert_type={self.alert_type}, handled={self.handled})>"
