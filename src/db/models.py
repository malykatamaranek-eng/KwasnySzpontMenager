"""Database models using SQLAlchemy 2.0."""
from datetime import datetime
from typing import Optional, List
from sqlalchemy import Column, Integer, String, Boolean, Float, DateTime, ForeignKey, Text, LargeBinary, Enum as SQLEnum
from sqlalchemy.orm import DeclarativeBase, relationship, Mapped, mapped_column
from sqlalchemy.dialects.postgresql import JSON
import enum


class Base(DeclarativeBase):
    """Base class for all models."""
    pass


class AccountStatus(str, enum.Enum):
    """Account status enum."""
    PENDING = "pending"
    VALIDATING = "validating"
    VALID = "valid"
    INVALID = "invalid"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    ERROR = "error"


class Account(Base):
    """Account model for email accounts."""
    __tablename__ = "accounts"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    email: Mapped[str] = mapped_column(String, unique=True, nullable=False, index=True)
    encrypted_password: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    provider: Mapped[str] = mapped_column(String, nullable=False)
    status: Mapped[AccountStatus] = mapped_column(
        SQLEnum(AccountStatus), 
        default=AccountStatus.PENDING, 
        nullable=False,
        index=True
    )
    
    # Relationships
    proxy_id: Mapped[Optional[int]] = mapped_column(ForeignKey("proxies.id"), nullable=True)
    proxy: Mapped[Optional["Proxy"]] = relationship("Proxy", back_populates="accounts")
    sessions: Mapped[List["Session"]] = relationship("Session", back_populates="account", cascade="all, delete-orphan")
    logs: Mapped[List["AccountLog"]] = relationship("AccountLog", back_populates="account", cascade="all, delete-orphan")
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[Optional[datetime]] = mapped_column(DateTime, onupdate=datetime.utcnow, nullable=True)
    
    def __repr__(self) -> str:
        return f"<Account(id={self.id}, email={self.email}, status={self.status})>"


class Proxy(Base):
    """Proxy model for proxy servers."""
    __tablename__ = "proxies"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    host: Mapped[str] = mapped_column(String, nullable=False)
    port: Mapped[int] = mapped_column(Integer, nullable=False)
    username: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    password: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    is_alive: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    last_tested: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    latency_ms: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    
    # Relationships
    accounts: Mapped[List["Account"]] = relationship("Account", back_populates="proxy")
    
    def __repr__(self) -> str:
        return f"<Proxy(id={self.id}, host={self.host}:{self.port}, is_alive={self.is_alive})>"
    
    @property
    def url(self) -> str:
        """Get proxy URL."""
        if self.username and self.password:
            return f"http://{self.username}:{self.password}@{self.host}:{self.port}"
        return f"http://{self.host}:{self.port}"


class Session(Base):
    """Session model for storing account sessions."""
    __tablename__ = "sessions"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    account_id: Mapped[int] = mapped_column(ForeignKey("accounts.id"), nullable=False)
    cookies: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    access_token: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Relationships
    account: Mapped["Account"] = relationship("Account", back_populates="sessions")
    
    def __repr__(self) -> str:
        return f"<Session(id={self.id}, account_id={self.account_id})>"


class AccountLog(Base):
    """Account log model for storing operation logs."""
    __tablename__ = "account_logs"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    account_id: Mapped[int] = mapped_column(ForeignKey("accounts.id"), nullable=False, index=True)
    action: Mapped[str] = mapped_column(String, nullable=False)
    status: Mapped[str] = mapped_column(String, nullable=False)
    message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    
    # Relationships
    account: Mapped["Account"] = relationship("Account", back_populates="logs")
    
    def __repr__(self) -> str:
        return f"<AccountLog(id={self.id}, account_id={self.account_id}, action={self.action}, status={self.status})>"
