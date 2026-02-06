"""CRUD operations for the Facebook automation system.

This module provides async CRUD operations for all database models
with comprehensive error handling, transaction management, and specialized queries.
"""

from datetime import datetime
from typing import Any, Optional, Sequence

from sqlalchemy import and_, delete, func, or_, select, update
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.core.exceptions import DatabaseException, DuplicateRecordError, RecordNotFoundError
from src.core.logging import get_logger
from src.db.models import (
    EmailAccount,
    EmailAccountStatus,
    EmailProvider,
    FacebookAccount,
    FacebookAccountStatus,
    Proxy,
    SecurityAlert,
    Task,
    TaskStatus,
)

logger = get_logger(__name__)


# ============================================================================
# Proxy CRUD Operations
# ============================================================================

async def create_proxy(
    db: AsyncSession,
    host: str,
    port: int,
    username: Optional[str] = None,
    password_encrypted: Optional[str] = None,
    protocol: str = "socks5",
    is_active: bool = True,
) -> Proxy:
    """Create a new proxy.
    
    Args:
        db: Database session.
        host: Proxy server hostname or IP.
        port: Proxy server port.
        username: Optional proxy authentication username.
        password_encrypted: Optional encrypted proxy password.
        protocol: Proxy protocol (default: socks5).
        is_active: Whether proxy is active (default: True).
    
    Returns:
        Proxy: Created proxy instance.
    
    Raises:
        DuplicateRecordError: If proxy with same host:port exists.
        DatabaseException: If creation fails.
    """
    try:
        proxy = Proxy(
            host=host,
            port=port,
            username=username,
            password_encrypted=password_encrypted,
            protocol=protocol,
            is_active=is_active,
        )
        db.add(proxy)
        await db.commit()
        await db.refresh(proxy)
        logger.info("Proxy created", proxy_id=proxy.id, host=host, port=port)
        return proxy
    except IntegrityError as e:
        await db.rollback()
        logger.error("Duplicate proxy", host=host, port=port)
        raise DuplicateRecordError("Proxy", "host:port", f"{host}:{port}")
    except SQLAlchemyError as e:
        await db.rollback()
        logger.error("Failed to create proxy", error=str(e))
        raise DatabaseException(f"Failed to create proxy: {str(e)}")


async def get_proxy(db: AsyncSession, proxy_id: int) -> Optional[Proxy]:
    """Get proxy by ID.
    
    Args:
        db: Database session.
        proxy_id: Proxy ID.
    
    Returns:
        Optional[Proxy]: Proxy instance or None if not found.
    """
    try:
        result = await db.execute(select(Proxy).where(Proxy.id == proxy_id))
        return result.scalar_one_or_none()
    except SQLAlchemyError as e:
        logger.error("Failed to get proxy", proxy_id=proxy_id, error=str(e))
        raise DatabaseException(f"Failed to get proxy: {str(e)}")


async def get_proxy_by_host_port(db: AsyncSession, host: str, port: int) -> Optional[Proxy]:
    """Get proxy by host and port.
    
    Args:
        db: Database session.
        host: Proxy hostname.
        port: Proxy port.
    
    Returns:
        Optional[Proxy]: Proxy instance or None if not found.
    """
    try:
        result = await db.execute(
            select(Proxy).where(and_(Proxy.host == host, Proxy.port == port))
        )
        return result.scalar_one_or_none()
    except SQLAlchemyError as e:
        logger.error("Failed to get proxy by host:port", host=host, port=port, error=str(e))
        raise DatabaseException(f"Failed to get proxy: {str(e)}")


async def list_proxies(
    db: AsyncSession,
    skip: int = 0,
    limit: int = 100,
    is_active: Optional[bool] = None,
) -> Sequence[Proxy]:
    """List proxies with optional filtering.
    
    Args:
        db: Database session.
        skip: Number of records to skip (pagination).
        limit: Maximum number of records to return.
        is_active: Filter by active status.
    
    Returns:
        Sequence[Proxy]: List of proxy instances.
    """
    try:
        query = select(Proxy)
        if is_active is not None:
            query = query.where(Proxy.is_active == is_active)
        query = query.offset(skip).limit(limit).order_by(Proxy.id)
        result = await db.execute(query)
        return result.scalars().all()
    except SQLAlchemyError as e:
        logger.error("Failed to list proxies", error=str(e))
        raise DatabaseException(f"Failed to list proxies: {str(e)}")


async def get_active_proxies(db: AsyncSession, limit: int = 10) -> Sequence[Proxy]:
    """Get active proxies sorted by performance.
    
    Returns active proxies sorted by success rate and latency.
    
    Args:
        db: Database session.
        limit: Maximum number of proxies to return.
    
    Returns:
        Sequence[Proxy]: List of active proxy instances.
    """
    try:
        query = (
            select(Proxy)
            .where(Proxy.is_active == True)
            .order_by(
                (Proxy.success_count / func.nullif(Proxy.success_count + Proxy.fail_count, 0)).desc(),
                Proxy.latency_ms.asc()
            )
            .limit(limit)
        )
        result = await db.execute(query)
        return result.scalars().all()
    except SQLAlchemyError as e:
        logger.error("Failed to get active proxies", error=str(e))
        raise DatabaseException(f"Failed to get active proxies: {str(e)}")


async def update_proxy(
    db: AsyncSession,
    proxy_id: int,
    **kwargs: Any,
) -> Optional[Proxy]:
    """Update proxy fields.
    
    Args:
        db: Database session.
        proxy_id: Proxy ID.
        **kwargs: Fields to update.
    
    Returns:
        Optional[Proxy]: Updated proxy instance or None if not found.
    
    Raises:
        RecordNotFoundError: If proxy not found.
        DatabaseException: If update fails.
    """
    try:
        proxy = await get_proxy(db, proxy_id)
        if not proxy:
            raise RecordNotFoundError("Proxy", proxy_id)
        
        for key, value in kwargs.items():
            if hasattr(proxy, key):
                setattr(proxy, key, value)
        
        await db.commit()
        await db.refresh(proxy)
        logger.info("Proxy updated", proxy_id=proxy_id)
        return proxy
    except RecordNotFoundError:
        raise
    except SQLAlchemyError as e:
        await db.rollback()
        logger.error("Failed to update proxy", proxy_id=proxy_id, error=str(e))
        raise DatabaseException(f"Failed to update proxy: {str(e)}")


async def update_proxy_stats(
    db: AsyncSession,
    proxy_id: int,
    success: bool,
    latency_ms: Optional[int] = None,
) -> Optional[Proxy]:
    """Update proxy statistics after test.
    
    Args:
        db: Database session.
        proxy_id: Proxy ID.
        success: Whether test was successful.
        latency_ms: Optional latency measurement.
    
    Returns:
        Optional[Proxy]: Updated proxy instance.
    """
    try:
        proxy = await get_proxy(db, proxy_id)
        if not proxy:
            raise RecordNotFoundError("Proxy", proxy_id)
        
        if success:
            proxy.success_count += 1
        else:
            proxy.fail_count += 1
        
        proxy.last_tested = datetime.utcnow()
        if latency_ms is not None:
            proxy.latency_ms = latency_ms
        
        await db.commit()
        await db.refresh(proxy)
        logger.debug("Proxy stats updated", proxy_id=proxy_id, success=success)
        return proxy
    except RecordNotFoundError:
        raise
    except SQLAlchemyError as e:
        await db.rollback()
        logger.error("Failed to update proxy stats", proxy_id=proxy_id, error=str(e))
        raise DatabaseException(f"Failed to update proxy stats: {str(e)}")


async def delete_proxy(db: AsyncSession, proxy_id: int) -> bool:
    """Delete proxy by ID.
    
    Args:
        db: Database session.
        proxy_id: Proxy ID.
    
    Returns:
        bool: True if deleted, False if not found.
    """
    try:
        result = await db.execute(delete(Proxy).where(Proxy.id == proxy_id))
        await db.commit()
        deleted = result.rowcount > 0
        if deleted:
            logger.info("Proxy deleted", proxy_id=proxy_id)
        return deleted
    except SQLAlchemyError as e:
        await db.rollback()
        logger.error("Failed to delete proxy", proxy_id=proxy_id, error=str(e))
        raise DatabaseException(f"Failed to delete proxy: {str(e)}")


# ============================================================================
# EmailAccount CRUD Operations
# ============================================================================

async def create_email_account(
    db: AsyncSession,
    email: str,
    password_encrypted: str,
    provider: EmailProvider,
    imap_host: Optional[str] = None,
    imap_port: Optional[int] = None,
    status: EmailAccountStatus = EmailAccountStatus.VALIDATED,
) -> EmailAccount:
    """Create a new email account.
    
    Args:
        db: Database session.
        email: Email address.
        password_encrypted: Encrypted password.
        provider: Email provider.
        imap_host: Optional IMAP server hostname.
        imap_port: Optional IMAP server port.
        status: Account status (default: validated).
    
    Returns:
        EmailAccount: Created email account instance.
    
    Raises:
        DuplicateRecordError: If email already exists.
        DatabaseException: If creation fails.
    """
    try:
        email_account = EmailAccount(
            email=email,
            password_encrypted=password_encrypted,
            provider=provider,
            imap_host=imap_host,
            imap_port=imap_port,
            status=status,
        )
        db.add(email_account)
        await db.commit()
        await db.refresh(email_account)
        logger.info("Email account created", email_account_id=email_account.id, email=email)
        return email_account
    except IntegrityError:
        await db.rollback()
        logger.error("Duplicate email account", email=email)
        raise DuplicateRecordError("EmailAccount", "email", email)
    except SQLAlchemyError as e:
        await db.rollback()
        logger.error("Failed to create email account", error=str(e))
        raise DatabaseException(f"Failed to create email account: {str(e)}")


async def get_email_account(db: AsyncSession, email_account_id: int) -> Optional[EmailAccount]:
    """Get email account by ID.
    
    Args:
        db: Database session.
        email_account_id: Email account ID.
    
    Returns:
        Optional[EmailAccount]: Email account instance or None.
    """
    try:
        result = await db.execute(select(EmailAccount).where(EmailAccount.id == email_account_id))
        return result.scalar_one_or_none()
    except SQLAlchemyError as e:
        logger.error("Failed to get email account", email_account_id=email_account_id, error=str(e))
        raise DatabaseException(f"Failed to get email account: {str(e)}")


async def get_email_account_by_email(db: AsyncSession, email: str) -> Optional[EmailAccount]:
    """Get email account by email address.
    
    Args:
        db: Database session.
        email: Email address.
    
    Returns:
        Optional[EmailAccount]: Email account instance or None.
    """
    try:
        result = await db.execute(select(EmailAccount).where(EmailAccount.email == email))
        return result.scalar_one_or_none()
    except SQLAlchemyError as e:
        logger.error("Failed to get email account by email", email=email, error=str(e))
        raise DatabaseException(f"Failed to get email account: {str(e)}")


async def list_email_accounts(
    db: AsyncSession,
    skip: int = 0,
    limit: int = 100,
    provider: Optional[EmailProvider] = None,
    status: Optional[EmailAccountStatus] = None,
) -> Sequence[EmailAccount]:
    """List email accounts with optional filtering.
    
    Args:
        db: Database session.
        skip: Number of records to skip.
        limit: Maximum number of records to return.
        provider: Filter by provider.
        status: Filter by status.
    
    Returns:
        Sequence[EmailAccount]: List of email account instances.
    """
    try:
        query = select(EmailAccount)
        if provider is not None:
            query = query.where(EmailAccount.provider == provider)
        if status is not None:
            query = query.where(EmailAccount.status == status)
        query = query.offset(skip).limit(limit).order_by(EmailAccount.id)
        result = await db.execute(query)
        return result.scalars().all()
    except SQLAlchemyError as e:
        logger.error("Failed to list email accounts", error=str(e))
        raise DatabaseException(f"Failed to list email accounts: {str(e)}")


async def update_email_account(
    db: AsyncSession,
    email_account_id: int,
    **kwargs: Any,
) -> Optional[EmailAccount]:
    """Update email account fields.
    
    Args:
        db: Database session.
        email_account_id: Email account ID.
        **kwargs: Fields to update.
    
    Returns:
        Optional[EmailAccount]: Updated email account instance.
    
    Raises:
        RecordNotFoundError: If email account not found.
        DatabaseException: If update fails.
    """
    try:
        email_account = await get_email_account(db, email_account_id)
        if not email_account:
            raise RecordNotFoundError("EmailAccount", email_account_id)
        
        for key, value in kwargs.items():
            if hasattr(email_account, key):
                setattr(email_account, key, value)
        
        await db.commit()
        await db.refresh(email_account)
        logger.info("Email account updated", email_account_id=email_account_id)
        return email_account
    except RecordNotFoundError:
        raise
    except SQLAlchemyError as e:
        await db.rollback()
        logger.error("Failed to update email account", email_account_id=email_account_id, error=str(e))
        raise DatabaseException(f"Failed to update email account: {str(e)}")


async def delete_email_account(db: AsyncSession, email_account_id: int) -> bool:
    """Delete email account by ID.
    
    Args:
        db: Database session.
        email_account_id: Email account ID.
    
    Returns:
        bool: True if deleted, False if not found.
    """
    try:
        result = await db.execute(delete(EmailAccount).where(EmailAccount.id == email_account_id))
        await db.commit()
        deleted = result.rowcount > 0
        if deleted:
            logger.info("Email account deleted", email_account_id=email_account_id)
        return deleted
    except SQLAlchemyError as e:
        await db.rollback()
        logger.error("Failed to delete email account", email_account_id=email_account_id, error=str(e))
        raise DatabaseException(f"Failed to delete email account: {str(e)}")


# ============================================================================
# FacebookAccount CRUD Operations
# ============================================================================

async def create_facebook_account(
    db: AsyncSession,
    email_account_id: int,
    fb_email: str,
    fb_password_encrypted: str,
    status: FacebookAccountStatus = FacebookAccountStatus.PENDING,
) -> FacebookAccount:
    """Create a new Facebook account.
    
    Args:
        db: Database session.
        email_account_id: Associated email account ID.
        fb_email: Facebook login email.
        fb_password_encrypted: Encrypted Facebook password.
        status: Account status (default: pending).
    
    Returns:
        FacebookAccount: Created Facebook account instance.
    
    Raises:
        DuplicateRecordError: If Facebook email already exists.
        DatabaseException: If creation fails.
    """
    try:
        fb_account = FacebookAccount(
            email_account_id=email_account_id,
            fb_email=fb_email,
            fb_password_encrypted=fb_password_encrypted,
            status=status,
        )
        db.add(fb_account)
        await db.commit()
        await db.refresh(fb_account)
        logger.info("Facebook account created", fb_account_id=fb_account.id, fb_email=fb_email)
        return fb_account
    except IntegrityError:
        await db.rollback()
        logger.error("Duplicate Facebook account", fb_email=fb_email)
        raise DuplicateRecordError("FacebookAccount", "fb_email", fb_email)
    except SQLAlchemyError as e:
        await db.rollback()
        logger.error("Failed to create Facebook account", error=str(e))
        raise DatabaseException(f"Failed to create Facebook account: {str(e)}")


async def get_facebook_account(db: AsyncSession, fb_account_id: int) -> Optional[FacebookAccount]:
    """Get Facebook account by ID with email account loaded.
    
    Args:
        db: Database session.
        fb_account_id: Facebook account ID.
    
    Returns:
        Optional[FacebookAccount]: Facebook account instance or None.
    """
    try:
        result = await db.execute(
            select(FacebookAccount)
            .options(selectinload(FacebookAccount.email_account))
            .where(FacebookAccount.id == fb_account_id)
        )
        return result.scalar_one_or_none()
    except SQLAlchemyError as e:
        logger.error("Failed to get Facebook account", fb_account_id=fb_account_id, error=str(e))
        raise DatabaseException(f"Failed to get Facebook account: {str(e)}")


async def get_facebook_account_by_email(db: AsyncSession, fb_email: str) -> Optional[FacebookAccount]:
    """Get Facebook account by email with email account loaded.
    
    Args:
        db: Database session.
        fb_email: Facebook email address.
    
    Returns:
        Optional[FacebookAccount]: Facebook account instance or None.
    """
    try:
        result = await db.execute(
            select(FacebookAccount)
            .options(selectinload(FacebookAccount.email_account))
            .where(FacebookAccount.fb_email == fb_email)
        )
        return result.scalar_one_or_none()
    except SQLAlchemyError as e:
        logger.error("Failed to get Facebook account by email", fb_email=fb_email, error=str(e))
        raise DatabaseException(f"Failed to get Facebook account: {str(e)}")


async def list_facebook_accounts(
    db: AsyncSession,
    skip: int = 0,
    limit: int = 100,
    status: Optional[FacebookAccountStatus] = None,
    email_account_id: Optional[int] = None,
) -> Sequence[FacebookAccount]:
    """List Facebook accounts with optional filtering.
    
    Args:
        db: Database session.
        skip: Number of records to skip.
        limit: Maximum number of records to return.
        status: Filter by status.
        email_account_id: Filter by email account ID.
    
    Returns:
        Sequence[FacebookAccount]: List of Facebook account instances.
    """
    try:
        query = select(FacebookAccount).options(selectinload(FacebookAccount.email_account))
        if status is not None:
            query = query.where(FacebookAccount.status == status)
        if email_account_id is not None:
            query = query.where(FacebookAccount.email_account_id == email_account_id)
        query = query.offset(skip).limit(limit).order_by(FacebookAccount.id)
        result = await db.execute(query)
        return result.scalars().all()
    except SQLAlchemyError as e:
        logger.error("Failed to list Facebook accounts", error=str(e))
        raise DatabaseException(f"Failed to list Facebook accounts: {str(e)}")


async def update_facebook_account(
    db: AsyncSession,
    fb_account_id: int,
    **kwargs: Any,
) -> Optional[FacebookAccount]:
    """Update Facebook account fields.
    
    Args:
        db: Database session.
        fb_account_id: Facebook account ID.
        **kwargs: Fields to update.
    
    Returns:
        Optional[FacebookAccount]: Updated Facebook account instance.
    
    Raises:
        RecordNotFoundError: If Facebook account not found.
        DatabaseException: If update fails.
    """
    try:
        fb_account = await get_facebook_account(db, fb_account_id)
        if not fb_account:
            raise RecordNotFoundError("FacebookAccount", fb_account_id)
        
        for key, value in kwargs.items():
            if hasattr(fb_account, key):
                setattr(fb_account, key, value)
        
        await db.commit()
        await db.refresh(fb_account)
        logger.info("Facebook account updated", fb_account_id=fb_account_id)
        return fb_account
    except RecordNotFoundError:
        raise
    except SQLAlchemyError as e:
        await db.rollback()
        logger.error("Failed to update Facebook account", fb_account_id=fb_account_id, error=str(e))
        raise DatabaseException(f"Failed to update Facebook account: {str(e)}")


async def delete_facebook_account(db: AsyncSession, fb_account_id: int) -> bool:
    """Delete Facebook account by ID.
    
    Args:
        db: Database session.
        fb_account_id: Facebook account ID.
    
    Returns:
        bool: True if deleted, False if not found.
    """
    try:
        result = await db.execute(delete(FacebookAccount).where(FacebookAccount.id == fb_account_id))
        await db.commit()
        deleted = result.rowcount > 0
        if deleted:
            logger.info("Facebook account deleted", fb_account_id=fb_account_id)
        return deleted
    except SQLAlchemyError as e:
        await db.rollback()
        logger.error("Failed to delete Facebook account", fb_account_id=fb_account_id, error=str(e))
        raise DatabaseException(f"Failed to delete Facebook account: {str(e)}")


# ============================================================================
# Task CRUD Operations
# ============================================================================

async def create_task(
    db: AsyncSession,
    celery_task_id: str,
    account_id: int,
    proxy_id: Optional[int] = None,
    status: TaskStatus = TaskStatus.PENDING,
) -> Task:
    """Create a new task.
    
    Args:
        db: Database session.
        celery_task_id: Celery task identifier.
        account_id: Facebook account ID.
        proxy_id: Optional proxy ID.
        status: Task status (default: pending).
    
    Returns:
        Task: Created task instance.
    
    Raises:
        DuplicateRecordError: If celery_task_id already exists.
        DatabaseException: If creation fails.
    """
    try:
        task = Task(
            celery_task_id=celery_task_id,
            account_id=account_id,
            proxy_id=proxy_id,
            status=status,
            logs=[],
        )
        db.add(task)
        await db.commit()
        await db.refresh(task)
        logger.info("Task created", task_id=task.id, celery_task_id=celery_task_id)
        return task
    except IntegrityError:
        await db.rollback()
        logger.error("Duplicate task", celery_task_id=celery_task_id)
        raise DuplicateRecordError("Task", "celery_task_id", celery_task_id)
    except SQLAlchemyError as e:
        await db.rollback()
        logger.error("Failed to create task", error=str(e))
        raise DatabaseException(f"Failed to create task: {str(e)}")


async def get_task(db: AsyncSession, task_id: int) -> Optional[Task]:
    """Get task by ID with relationships loaded.
    
    Args:
        db: Database session.
        task_id: Task ID.
    
    Returns:
        Optional[Task]: Task instance or None.
    """
    try:
        result = await db.execute(
            select(Task)
            .options(
                selectinload(Task.account),
                selectinload(Task.proxy)
            )
            .where(Task.id == task_id)
        )
        return result.scalar_one_or_none()
    except SQLAlchemyError as e:
        logger.error("Failed to get task", task_id=task_id, error=str(e))
        raise DatabaseException(f"Failed to get task: {str(e)}")


async def get_task_by_celery_id(db: AsyncSession, celery_task_id: str) -> Optional[Task]:
    """Get task by Celery task ID.
    
    Args:
        db: Database session.
        celery_task_id: Celery task identifier.
    
    Returns:
        Optional[Task]: Task instance or None.
    """
    try:
        result = await db.execute(
            select(Task)
            .options(
                selectinload(Task.account),
                selectinload(Task.proxy)
            )
            .where(Task.celery_task_id == celery_task_id)
        )
        return result.scalar_one_or_none()
    except SQLAlchemyError as e:
        logger.error("Failed to get task by celery_task_id", celery_task_id=celery_task_id, error=str(e))
        raise DatabaseException(f"Failed to get task: {str(e)}")


async def list_tasks(
    db: AsyncSession,
    skip: int = 0,
    limit: int = 100,
    status: Optional[TaskStatus] = None,
    account_id: Optional[int] = None,
    proxy_id: Optional[int] = None,
) -> Sequence[Task]:
    """List tasks with optional filtering.
    
    Args:
        db: Database session.
        skip: Number of records to skip.
        limit: Maximum number of records to return.
        status: Filter by status.
        account_id: Filter by account ID.
        proxy_id: Filter by proxy ID.
    
    Returns:
        Sequence[Task]: List of task instances.
    """
    try:
        query = select(Task).options(
            selectinload(Task.account),
            selectinload(Task.proxy)
        )
        if status is not None:
            query = query.where(Task.status == status)
        if account_id is not None:
            query = query.where(Task.account_id == account_id)
        if proxy_id is not None:
            query = query.where(Task.proxy_id == proxy_id)
        query = query.offset(skip).limit(limit).order_by(Task.created_at.desc())
        result = await db.execute(query)
        return result.scalars().all()
    except SQLAlchemyError as e:
        logger.error("Failed to list tasks", error=str(e))
        raise DatabaseException(f"Failed to list tasks: {str(e)}")


async def get_pending_tasks(db: AsyncSession, limit: int = 10) -> Sequence[Task]:
    """Get pending tasks.
    
    Args:
        db: Database session.
        limit: Maximum number of tasks to return.
    
    Returns:
        Sequence[Task]: List of pending task instances.
    """
    try:
        query = (
            select(Task)
            .options(
                selectinload(Task.account),
                selectinload(Task.proxy)
            )
            .where(Task.status == TaskStatus.PENDING)
            .order_by(Task.created_at.asc())
            .limit(limit)
        )
        result = await db.execute(query)
        return result.scalars().all()
    except SQLAlchemyError as e:
        logger.error("Failed to get pending tasks", error=str(e))
        raise DatabaseException(f"Failed to get pending tasks: {str(e)}")


async def update_task(
    db: AsyncSession,
    task_id: int,
    **kwargs: Any,
) -> Optional[Task]:
    """Update task fields.
    
    Args:
        db: Database session.
        task_id: Task ID.
        **kwargs: Fields to update.
    
    Returns:
        Optional[Task]: Updated task instance.
    
    Raises:
        RecordNotFoundError: If task not found.
        DatabaseException: If update fails.
    """
    try:
        task = await get_task(db, task_id)
        if not task:
            raise RecordNotFoundError("Task", task_id)
        
        for key, value in kwargs.items():
            if hasattr(task, key):
                setattr(task, key, value)
        
        await db.commit()
        await db.refresh(task)
        logger.info("Task updated", task_id=task_id)
        return task
    except RecordNotFoundError:
        raise
    except SQLAlchemyError as e:
        await db.rollback()
        logger.error("Failed to update task", task_id=task_id, error=str(e))
        raise DatabaseException(f"Failed to update task: {str(e)}")


async def add_task_log(
    db: AsyncSession,
    task_id: int,
    log_entry: dict[str, Any],
) -> Optional[Task]:
    """Add log entry to task.
    
    Args:
        db: Database session.
        task_id: Task ID.
        log_entry: Log entry to add.
    
    Returns:
        Optional[Task]: Updated task instance.
    """
    try:
        task = await get_task(db, task_id)
        if not task:
            raise RecordNotFoundError("Task", task_id)
        
        if task.logs is None:
            task.logs = []
        
        task.logs.append({
            "timestamp": datetime.utcnow().isoformat(),
            **log_entry
        })
        
        # Mark logs as modified for SQLAlchemy to detect change
        from sqlalchemy.orm.attributes import flag_modified
        flag_modified(task, "logs")
        
        await db.commit()
        await db.refresh(task)
        return task
    except RecordNotFoundError:
        raise
    except SQLAlchemyError as e:
        await db.rollback()
        logger.error("Failed to add task log", task_id=task_id, error=str(e))
        raise DatabaseException(f"Failed to add task log: {str(e)}")


async def delete_task(db: AsyncSession, task_id: int) -> bool:
    """Delete task by ID.
    
    Args:
        db: Database session.
        task_id: Task ID.
    
    Returns:
        bool: True if deleted, False if not found.
    """
    try:
        result = await db.execute(delete(Task).where(Task.id == task_id))
        await db.commit()
        deleted = result.rowcount > 0
        if deleted:
            logger.info("Task deleted", task_id=task_id)
        return deleted
    except SQLAlchemyError as e:
        await db.rollback()
        logger.error("Failed to delete task", task_id=task_id, error=str(e))
        raise DatabaseException(f"Failed to delete task: {str(e)}")


# ============================================================================
# SecurityAlert CRUD Operations
# ============================================================================

async def create_security_alert(
    db: AsyncSession,
    account_id: int,
    alert_type: str,
    alert_data: dict[str, Any],
) -> SecurityAlert:
    """Create a new security alert.
    
    Args:
        db: Database session.
        account_id: Facebook account ID.
        alert_type: Type of security alert.
        alert_data: Alert data dictionary.
    
    Returns:
        SecurityAlert: Created security alert instance.
    
    Raises:
        DatabaseException: If creation fails.
    """
    try:
        alert = SecurityAlert(
            account_id=account_id,
            alert_type=alert_type,
            alert_data=alert_data,
        )
        db.add(alert)
        await db.commit()
        await db.refresh(alert)
        logger.info("Security alert created", alert_id=alert.id, account_id=account_id, alert_type=alert_type)
        return alert
    except SQLAlchemyError as e:
        await db.rollback()
        logger.error("Failed to create security alert", error=str(e))
        raise DatabaseException(f"Failed to create security alert: {str(e)}")


async def get_security_alert(db: AsyncSession, alert_id: int) -> Optional[SecurityAlert]:
    """Get security alert by ID.
    
    Args:
        db: Database session.
        alert_id: Security alert ID.
    
    Returns:
        Optional[SecurityAlert]: Security alert instance or None.
    """
    try:
        result = await db.execute(
            select(SecurityAlert)
            .options(selectinload(SecurityAlert.account))
            .where(SecurityAlert.id == alert_id)
        )
        return result.scalar_one_or_none()
    except SQLAlchemyError as e:
        logger.error("Failed to get security alert", alert_id=alert_id, error=str(e))
        raise DatabaseException(f"Failed to get security alert: {str(e)}")


async def list_security_alerts(
    db: AsyncSession,
    skip: int = 0,
    limit: int = 100,
    account_id: Optional[int] = None,
    alert_type: Optional[str] = None,
    handled: Optional[bool] = None,
) -> Sequence[SecurityAlert]:
    """List security alerts with optional filtering.
    
    Args:
        db: Database session.
        skip: Number of records to skip.
        limit: Maximum number of records to return.
        account_id: Filter by account ID.
        alert_type: Filter by alert type.
        handled: Filter by handled status.
    
    Returns:
        Sequence[SecurityAlert]: List of security alert instances.
    """
    try:
        query = select(SecurityAlert).options(selectinload(SecurityAlert.account))
        if account_id is not None:
            query = query.where(SecurityAlert.account_id == account_id)
        if alert_type is not None:
            query = query.where(SecurityAlert.alert_type == alert_type)
        if handled is not None:
            query = query.where(SecurityAlert.handled == handled)
        query = query.offset(skip).limit(limit).order_by(SecurityAlert.detected_at.desc())
        result = await db.execute(query)
        return result.scalars().all()
    except SQLAlchemyError as e:
        logger.error("Failed to list security alerts", error=str(e))
        raise DatabaseException(f"Failed to list security alerts: {str(e)}")


async def get_unhandled_alerts(db: AsyncSession, account_id: int) -> Sequence[SecurityAlert]:
    """Get unhandled security alerts for an account.
    
    Args:
        db: Database session.
        account_id: Facebook account ID.
    
    Returns:
        Sequence[SecurityAlert]: List of unhandled security alert instances.
    """
    try:
        query = (
            select(SecurityAlert)
            .where(
                and_(
                    SecurityAlert.account_id == account_id,
                    SecurityAlert.handled == False
                )
            )
            .order_by(SecurityAlert.detected_at.asc())
        )
        result = await db.execute(query)
        return result.scalars().all()
    except SQLAlchemyError as e:
        logger.error("Failed to get unhandled alerts", account_id=account_id, error=str(e))
        raise DatabaseException(f"Failed to get unhandled alerts: {str(e)}")


async def mark_alert_handled(
    db: AsyncSession,
    alert_id: int,
) -> Optional[SecurityAlert]:
    """Mark security alert as handled.
    
    Args:
        db: Database session.
        alert_id: Security alert ID.
    
    Returns:
        Optional[SecurityAlert]: Updated security alert instance.
    
    Raises:
        RecordNotFoundError: If alert not found.
        DatabaseException: If update fails.
    """
    try:
        alert = await get_security_alert(db, alert_id)
        if not alert:
            raise RecordNotFoundError("SecurityAlert", alert_id)
        
        alert.handled = True
        alert.handled_at = datetime.utcnow()
        
        await db.commit()
        await db.refresh(alert)
        logger.info("Security alert marked as handled", alert_id=alert_id)
        return alert
    except RecordNotFoundError:
        raise
    except SQLAlchemyError as e:
        await db.rollback()
        logger.error("Failed to mark alert as handled", alert_id=alert_id, error=str(e))
        raise DatabaseException(f"Failed to mark alert as handled: {str(e)}")


async def delete_security_alert(db: AsyncSession, alert_id: int) -> bool:
    """Delete security alert by ID.
    
    Args:
        db: Database session.
        alert_id: Security alert ID.
    
    Returns:
        bool: True if deleted, False if not found.
    """
    try:
        result = await db.execute(delete(SecurityAlert).where(SecurityAlert.id == alert_id))
        await db.commit()
        deleted = result.rowcount > 0
        if deleted:
            logger.info("Security alert deleted", alert_id=alert_id)
        return deleted
    except SQLAlchemyError as e:
        await db.rollback()
        logger.error("Failed to delete security alert", alert_id=alert_id, error=str(e))
        raise DatabaseException(f"Failed to delete security alert: {str(e)}")


# ============================================================================
# Batch Operations
# ============================================================================

async def batch_create_proxies(
    db: AsyncSession,
    proxies: list[dict[str, Any]],
) -> list[Proxy]:
    """Batch create multiple proxies.
    
    Args:
        db: Database session.
        proxies: List of proxy data dictionaries.
    
    Returns:
        list[Proxy]: List of created proxy instances.
    
    Raises:
        DatabaseException: If batch creation fails.
    """
    try:
        proxy_objects = [Proxy(**proxy_data) for proxy_data in proxies]
        db.add_all(proxy_objects)
        await db.commit()
        
        for proxy in proxy_objects:
            await db.refresh(proxy)
        
        logger.info("Batch created proxies", count=len(proxy_objects))
        return proxy_objects
    except SQLAlchemyError as e:
        await db.rollback()
        logger.error("Failed to batch create proxies", error=str(e))
        raise DatabaseException(f"Failed to batch create proxies: {str(e)}")


async def batch_update_task_status(
    db: AsyncSession,
    task_ids: list[int],
    status: TaskStatus,
) -> int:
    """Batch update task statuses.
    
    Args:
        db: Database session.
        task_ids: List of task IDs to update.
        status: New status for all tasks.
    
    Returns:
        int: Number of tasks updated.
    
    Raises:
        DatabaseException: If batch update fails.
    """
    try:
        result = await db.execute(
            update(Task)
            .where(Task.id.in_(task_ids))
            .values(status=status)
        )
        await db.commit()
        count = result.rowcount
        logger.info("Batch updated task statuses", count=count, status=status.value)
        return count
    except SQLAlchemyError as e:
        await db.rollback()
        logger.error("Failed to batch update task statuses", error=str(e))
        raise DatabaseException(f"Failed to batch update task statuses: {str(e)}")


async def cleanup_old_tasks(
    db: AsyncSession,
    days_old: int = 30,
) -> int:
    """Delete tasks older than specified days.
    
    Args:
        db: Database session.
        days_old: Number of days (default: 30).
    
    Returns:
        int: Number of tasks deleted.
    
    Raises:
        DatabaseException: If cleanup fails.
    """
    try:
        cutoff_date = datetime.utcnow() - timedelta(days=days_old)
        result = await db.execute(
            delete(Task).where(Task.created_at < cutoff_date)
        )
        await db.commit()
        count = result.rowcount
        logger.info("Cleaned up old tasks", count=count, days_old=days_old)
        return count
    except SQLAlchemyError as e:
        await db.rollback()
        logger.error("Failed to cleanup old tasks", error=str(e))
        raise DatabaseException(f"Failed to cleanup old tasks: {str(e)}")


# Import for timedelta
from datetime import timedelta
