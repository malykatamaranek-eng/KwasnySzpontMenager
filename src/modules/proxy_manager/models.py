"""Pydantic models for the Proxy Manager module.

This module defines data models for proxy configuration, testing results,
and statistics tracking using Pydantic for validation and serialization.
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field, field_validator


class ProxyConfig(BaseModel):
    """Proxy configuration with connection details.
    
    Attributes:
        id: Optional proxy ID (None for new proxies).
        host: Proxy server hostname or IP address.
        port: Proxy server port number.
        username: Optional proxy authentication username.
        password: Optional proxy authentication password (plaintext).
        protocol: Proxy protocol (http, https, socks4, socks5).
        latency_ms: Optional average latency in milliseconds.
        is_active: Whether proxy is currently active.
    """
    
    id: Optional[int] = Field(default=None, description="Proxy database ID")
    host: str = Field(..., min_length=1, max_length=255, description="Proxy hostname or IP")
    port: int = Field(..., ge=1, le=65535, description="Proxy port number")
    username: Optional[str] = Field(default=None, max_length=255, description="Proxy username")
    password: Optional[str] = Field(default=None, description="Proxy password")
    protocol: str = Field(default="socks5", description="Proxy protocol")
    latency_ms: Optional[int] = Field(default=None, ge=0, description="Average latency in ms")
    is_active: bool = Field(default=True, description="Whether proxy is active")
    
    @field_validator("protocol")
    @classmethod
    def validate_protocol(cls, v: str) -> str:
        """Validate proxy protocol is supported.
        
        Args:
            v: Protocol string to validate.
        
        Returns:
            str: Validated protocol in lowercase.
        
        Raises:
            ValueError: If protocol is not supported.
        """
        valid_protocols = {"http", "https", "socks4", "socks5"}
        v_lower = v.lower()
        if v_lower not in valid_protocols:
            raise ValueError(f"Protocol must be one of {valid_protocols}")
        return v_lower
    
    class Config:
        """Pydantic model configuration."""
        from_attributes = True


class ProxyTestResult(BaseModel):
    """Result of a proxy connectivity test.
    
    Attributes:
        proxy_id: ID of the tested proxy.
        success: Whether the test was successful.
        latency_ms: Measured latency in milliseconds (None if failed).
        error_message: Error message if test failed.
        timestamp: When the test was performed.
        endpoint: Test endpoint that was used.
    """
    
    proxy_id: int = Field(..., description="Proxy database ID")
    success: bool = Field(..., description="Whether test succeeded")
    latency_ms: Optional[int] = Field(default=None, ge=0, description="Latency in ms")
    error_message: Optional[str] = Field(default=None, description="Error message if failed")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Test timestamp")
    endpoint: str = Field(default="", description="Test endpoint used")
    
    class Config:
        """Pydantic model configuration."""
        from_attributes = True


class ProxyStats(BaseModel):
    """Statistical information about proxy performance.
    
    Attributes:
        proxy_id: ID of the proxy.
        success_count: Total number of successful connections.
        fail_count: Total number of failed connections.
        avg_latency_ms: Average latency in milliseconds.
        last_tested: Timestamp of last health check.
        success_rate: Calculated success rate (0.0-1.0).
        is_active: Whether proxy is currently active.
    """
    
    proxy_id: int = Field(..., description="Proxy database ID")
    success_count: int = Field(default=0, ge=0, description="Successful connection count")
    fail_count: int = Field(default=0, ge=0, description="Failed connection count")
    avg_latency_ms: Optional[int] = Field(default=None, ge=0, description="Average latency in ms")
    last_tested: Optional[datetime] = Field(default=None, description="Last test timestamp")
    success_rate: float = Field(default=0.0, ge=0.0, le=1.0, description="Success rate")
    is_active: bool = Field(default=True, description="Whether proxy is active")
    
    @classmethod
    def from_db_proxy(cls, proxy: "Proxy") -> "ProxyStats":
        """Create ProxyStats from database Proxy model.
        
        Args:
            proxy: Database Proxy instance.
        
        Returns:
            ProxyStats: Proxy statistics.
        """
        total = proxy.success_count + proxy.fail_count
        success_rate = proxy.success_count / total if total > 0 else 0.0
        
        return cls(
            proxy_id=proxy.id,
            success_count=proxy.success_count,
            fail_count=proxy.fail_count,
            avg_latency_ms=proxy.latency_ms,
            last_tested=proxy.last_tested,
            success_rate=success_rate,
            is_active=proxy.is_active,
        )
    
    class Config:
        """Pydantic model configuration."""
        from_attributes = True
