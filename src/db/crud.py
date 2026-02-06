"""CRUD operations for database models."""
from typing import List, Optional
from sqlalchemy import select, update, delete
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from src.db.models import Account, Proxy, Session, AccountLog, AccountStatus
from src.core.security import encrypt_password, decrypt_password
from src.core.exceptions import DatabaseError
import structlog

logger = structlog.get_logger()


# Account CRUD
async def create_account(
    db: AsyncSession,
    email: str,
    password: str,
    provider: str
) -> Account:
    """Create a new account."""
    try:
        encrypted_pwd = encrypt_password(password)
        account = Account(
            email=email,
            encrypted_password=encrypted_pwd,
            provider=provider,
            status=AccountStatus.PENDING
        )
        db.add(account)
        await db.flush()
        await db.refresh(account)
        logger.info("account_created", account_id=account.id, email=email)
        return account
    except Exception as e:
        logger.error("account_creation_failed", email=email, error=str(e))
        raise DatabaseError(f"Failed to create account: {str(e)}")


async def get_account(db: AsyncSession, account_id: int) -> Optional[Account]:
    """Get account by ID."""
    result = await db.execute(
        select(Account)
        .options(selectinload(Account.proxy), selectinload(Account.sessions))
        .where(Account.id == account_id)
    )
    return result.scalar_one_or_none()


async def get_account_by_email(db: AsyncSession, email: str) -> Optional[Account]:
    """Get account by email."""
    result = await db.execute(
        select(Account).where(Account.email == email)
    )
    return result.scalar_one_or_none()


async def list_accounts(
    db: AsyncSession,
    skip: int = 0,
    limit: int = 100,
    status: Optional[AccountStatus] = None
) -> List[Account]:
    """List accounts with pagination."""
    query = select(Account).offset(skip).limit(limit)
    if status:
        query = query.where(Account.status == status)
    result = await db.execute(query)
    return list(result.scalars().all())


async def update_account_status(
    db: AsyncSession,
    account_id: int,
    status: AccountStatus
) -> Optional[Account]:
    """Update account status."""
    await db.execute(
        update(Account)
        .where(Account.id == account_id)
        .values(status=status)
    )
    await db.commit()
    return await get_account(db, account_id)


async def delete_account(db: AsyncSession, account_id: int) -> bool:
    """Delete account."""
    result = await db.execute(
        delete(Account).where(Account.id == account_id)
    )
    await db.commit()
    return result.rowcount > 0


# Proxy CRUD
async def create_proxy(
    db: AsyncSession,
    host: str,
    port: int,
    username: Optional[str] = None,
    password: Optional[str] = None
) -> Proxy:
    """Create a new proxy."""
    proxy = Proxy(
        host=host,
        port=port,
        username=username,
        password=password,
        is_alive=True
    )
    db.add(proxy)
    await db.flush()
    await db.refresh(proxy)
    logger.info("proxy_created", proxy_id=proxy.id, host=host, port=port)
    return proxy


async def get_proxy(db: AsyncSession, proxy_id: int) -> Optional[Proxy]:
    """Get proxy by ID."""
    result = await db.execute(
        select(Proxy).where(Proxy.id == proxy_id)
    )
    return result.scalar_one_or_none()


async def list_proxies(
    db: AsyncSession,
    alive_only: bool = False
) -> List[Proxy]:
    """List proxies."""
    query = select(Proxy)
    if alive_only:
        query = query.where(Proxy.is_alive == True)
    result = await db.execute(query)
    return list(result.scalars().all())


async def update_proxy_health(
    db: AsyncSession,
    proxy_id: int,
    is_alive: bool,
    latency_ms: Optional[float] = None
) -> Optional[Proxy]:
    """Update proxy health status."""
    from datetime import datetime
    await db.execute(
        update(Proxy)
        .where(Proxy.id == proxy_id)
        .values(is_alive=is_alive, latency_ms=latency_ms, last_tested=datetime.utcnow())
    )
    await db.commit()
    return await get_proxy(db, proxy_id)


# Session CRUD
async def create_session(
    db: AsyncSession,
    account_id: int,
    cookies: Optional[dict] = None,
    access_token: Optional[str] = None,
    expires_at: Optional[object] = None
) -> Session:
    """Create a new session."""
    session = Session(
        account_id=account_id,
        cookies=cookies,
        access_token=access_token,
        expires_at=expires_at
    )
    db.add(session)
    await db.flush()
    await db.refresh(session)
    return session


async def get_latest_session(db: AsyncSession, account_id: int) -> Optional[Session]:
    """Get latest session for account."""
    result = await db.execute(
        select(Session)
        .where(Session.account_id == account_id)
        .order_by(Session.created_at.desc())
        .limit(1)
    )
    return result.scalar_one_or_none()


# Account Log CRUD
async def create_log(
    db: AsyncSession,
    account_id: int,
    action: str,
    status: str,
    message: Optional[str] = None
) -> AccountLog:
    """Create a new account log."""
    log = AccountLog(
        account_id=account_id,
        action=action,
        status=status,
        message=message
    )
    db.add(log)
    await db.flush()
    await db.refresh(log)
    return log


async def get_account_logs(
    db: AsyncSession,
    account_id: int,
    limit: int = 100
) -> List[AccountLog]:
    """Get logs for an account."""
    result = await db.execute(
        select(AccountLog)
        .where(AccountLog.account_id == account_id)
        .order_by(AccountLog.timestamp.desc())
        .limit(limit)
    )
    return list(result.scalars().all())
