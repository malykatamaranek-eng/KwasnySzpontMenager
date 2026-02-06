"""Database setup and session management for the Facebook automation system.

This module provides database engine configuration, session management,
and FastAPI dependency injection for async database operations.
"""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from typing import Optional

from sqlalchemy import event, text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import NullPool, QueuePool

from src.core.config import settings
from src.core.exceptions import DatabaseConnectionError
from src.core.logging import get_logger

logger = get_logger(__name__)


class DatabaseManager:
    """Manager for database connections and sessions.
    
    Provides centralized database engine and session management with
    proper connection pooling, event listeners, and health checks.
    """
    
    def __init__(self) -> None:
        """Initialize database manager."""
        self._engine: Optional[AsyncEngine] = None
        self._session_factory: Optional[async_sessionmaker[AsyncSession]] = None
    
    def create_engine(
        self,
        database_url: Optional[str] = None,
        echo: Optional[bool] = None,
        pool_size: Optional[int] = None,
        max_overflow: Optional[int] = None,
        pool_timeout: Optional[int] = None,
    ) -> AsyncEngine:
        """Create async database engine with connection pooling.
        
        Args:
            database_url: Database connection URL. Defaults to settings value.
            echo: Whether to log all SQL statements. Defaults to settings value.
            pool_size: Number of connections to maintain. Defaults to settings value.
            max_overflow: Maximum overflow connections. Defaults to settings value.
            pool_timeout: Timeout for getting connection. Defaults to settings value.
        
        Returns:
            AsyncEngine: Configured async SQLAlchemy engine.
        
        Raises:
            DatabaseConnectionError: If engine creation fails.
        """
        if self._engine is not None:
            logger.warning("Database engine already exists, returning existing engine")
            return self._engine
        
        url = database_url or str(settings.database_url)
        echo_sql = echo if echo is not None else settings.database_echo
        
        try:
            # Configure connection pool based on environment
            if settings.is_development():
                # Development: smaller pool, no overflow
                poolclass = QueuePool
                pool_config = {
                    "poolclass": poolclass,
                    "pool_size": 5,
                    "max_overflow": 0,
                    "pool_timeout": 30,
                    "pool_pre_ping": True,
                    "pool_recycle": 3600,
                }
            else:
                # Production: larger pool with overflow
                poolclass = QueuePool
                pool_config = {
                    "poolclass": poolclass,
                    "pool_size": pool_size or settings.database_pool_size,
                    "max_overflow": max_overflow or settings.database_max_overflow,
                    "pool_timeout": pool_timeout or settings.database_pool_timeout,
                    "pool_pre_ping": True,
                    "pool_recycle": 3600,
                }
            
            self._engine = create_async_engine(
                url,
                echo=echo_sql,
                **pool_config,
                connect_args={
                    "server_settings": {
                        "application_name": settings.app_name,
                    },
                },
            )
            
            # Register event listeners
            self._register_engine_events(self._engine.sync_engine)
            
            logger.info(
                "Database engine created",
                pool_size=pool_config.get("pool_size"),
                max_overflow=pool_config.get("max_overflow"),
            )
            
            return self._engine
            
        except Exception as e:
            logger.error("Failed to create database engine", error=str(e))
            raise DatabaseConnectionError(f"Failed to create database engine: {str(e)}")
    
    def create_session_factory(
        self,
        engine: Optional[AsyncEngine] = None,
    ) -> async_sessionmaker[AsyncSession]:
        """Create async session factory.
        
        Args:
            engine: Database engine. If not provided, uses existing engine.
        
        Returns:
            async_sessionmaker: Session factory for creating database sessions.
        
        Raises:
            DatabaseConnectionError: If no engine is available.
        """
        if self._session_factory is not None:
            logger.warning("Session factory already exists, returning existing factory")
            return self._session_factory
        
        engine_to_use = engine or self._engine
        if engine_to_use is None:
            raise DatabaseConnectionError("No database engine available")
        
        self._session_factory = async_sessionmaker(
            bind=engine_to_use,
            class_=AsyncSession,
            expire_on_commit=False,
            autocommit=False,
            autoflush=False,
        )
        
        logger.info("Session factory created")
        return self._session_factory
    
    @staticmethod
    def _register_engine_events(sync_engine) -> None:
        """Register SQLAlchemy engine event listeners.
        
        Args:
            sync_engine: Synchronous engine for event registration.
        """
        @event.listens_for(sync_engine, "connect")
        def receive_connect(dbapi_conn, connection_record):
            """Event listener for new database connections."""
            logger.debug("New database connection established")
        
        @event.listens_for(sync_engine, "close")
        def receive_close(dbapi_conn, connection_record):
            """Event listener for closed database connections."""
            logger.debug("Database connection closed")
    
    @property
    def engine(self) -> AsyncEngine:
        """Get database engine.
        
        Returns:
            AsyncEngine: Database engine instance.
        
        Raises:
            DatabaseConnectionError: If engine not initialized.
        """
        if self._engine is None:
            raise DatabaseConnectionError("Database engine not initialized")
        return self._engine
    
    @property
    def session_factory(self) -> async_sessionmaker[AsyncSession]:
        """Get session factory.
        
        Returns:
            async_sessionmaker: Session factory instance.
        
        Raises:
            DatabaseConnectionError: If session factory not initialized.
        """
        if self._session_factory is None:
            raise DatabaseConnectionError("Session factory not initialized")
        return self._session_factory
    
    @asynccontextmanager
    async def get_session(self) -> AsyncGenerator[AsyncSession, None]:
        """Get database session context manager.
        
        Yields:
            AsyncSession: Database session with automatic commit/rollback.
        
        Raises:
            DatabaseConnectionError: If session creation fails.
        """
        if self._session_factory is None:
            raise DatabaseConnectionError("Session factory not initialized")
        
        session = self._session_factory()
        try:
            yield session
            await session.commit()
        except Exception as e:
            await session.rollback()
            logger.error("Database session error, rolled back", error=str(e))
            raise
        finally:
            await session.close()
    
    async def dispose(self) -> None:
        """Dispose database engine and close all connections."""
        if self._engine is not None:
            await self._engine.dispose()
            logger.info("Database engine disposed")
            self._engine = None
            self._session_factory = None
    
    async def health_check(self) -> bool:
        """Check database connectivity and health.
        
        Returns:
            bool: True if database is healthy, False otherwise.
        """
        try:
            async with self.get_session() as session:
                result = await session.execute(text("SELECT 1"))
                result.scalar()
                logger.debug("Database health check passed")
                return True
        except Exception as e:
            logger.error("Database health check failed", error=str(e))
            return False


# Global database manager instance
db_manager = DatabaseManager()


async def init_database(
    database_url: Optional[str] = None,
    echo: Optional[bool] = None,
) -> None:
    """Initialize database engine and session factory.
    
    This should be called during application startup to set up
    the database connection pool and session management.
    
    Args:
        database_url: Database connection URL. Defaults to settings value.
        echo: Whether to log all SQL statements. Defaults to settings value.
    
    Raises:
        DatabaseConnectionError: If initialization fails.
    """
    try:
        logger.info("Initializing database")
        db_manager.create_engine(database_url=database_url, echo=echo)
        db_manager.create_session_factory()
        
        # Verify connectivity
        if await db_manager.health_check():
            logger.info("Database initialized successfully")
        else:
            raise DatabaseConnectionError("Database health check failed after initialization")
            
    except Exception as e:
        logger.error("Failed to initialize database", error=str(e))
        raise DatabaseConnectionError(f"Database initialization failed: {str(e)}")


async def close_database() -> None:
    """Close database connections and dispose engine.
    
    This should be called during application shutdown to properly
    close all database connections.
    """
    try:
        logger.info("Closing database connections")
        await db_manager.dispose()
        logger.info("Database connections closed")
    except Exception as e:
        logger.error("Error closing database connections", error=str(e))


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency for database session injection.
    
    Provides an async database session with automatic transaction
    management. The session commits on success and rolls back on error.
    
    Yields:
        AsyncSession: Database session for request handling.
    
    Example:
        ```python
        @app.get("/users/{user_id}")
        async def get_user(
            user_id: int,
            db: AsyncSession = Depends(get_db)
        ):
            result = await db.execute(select(User).where(User.id == user_id))
            user = result.scalar_one_or_none()
            return user
        ```
    """
    async with db_manager.get_session() as session:
        yield session


async def health_check() -> dict[str, str]:
    """Perform database health check.
    
    Returns:
        dict: Health check result with status and message.
    """
    try:
        is_healthy = await db_manager.health_check()
        return {
            "status": "healthy" if is_healthy else "unhealthy",
            "message": "Database is responsive" if is_healthy else "Database is not responsive"
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "message": f"Database health check error: {str(e)}"
        }
