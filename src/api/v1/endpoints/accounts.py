"""Account endpoints."""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel, EmailStr
import structlog
from src.db.database import get_db
from src.db import crud
from src.db.models import AccountStatus
from src.task_system.tasks import process_account_task, validate_account_task

logger = structlog.get_logger()

router = APIRouter()


# Pydantic models
class AccountCreate(BaseModel):
    """Account creation model."""
    email: EmailStr
    password: str
    provider: str


class AccountResponse(BaseModel):
    """Account response model."""
    id: int
    email: str
    provider: str
    status: str
    proxy_id: Optional[int] = None
    created_at: str
    updated_at: Optional[str] = None
    
    class Config:
        from_attributes = True


class AccountLogResponse(BaseModel):
    """Account log response model."""
    id: int
    account_id: int
    action: str
    status: str
    message: Optional[str] = None
    timestamp: str
    
    class Config:
        from_attributes = True


class ProcessAccountRequest(BaseModel):
    """Process account request model."""
    action: str = "login"  # login, reset_password, verify_2fa


class TaskResponse(BaseModel):
    """Task response model."""
    task_id: str
    account_id: int
    action: str
    status: str = "queued"


@router.post("/accounts", response_model=AccountResponse, status_code=status.HTTP_201_CREATED)
async def create_account(
    account: AccountCreate,
    db: AsyncSession = Depends(get_db)
):
    """
    Create a new account with encrypted password.
    
    Args:
        account: Account creation data
        db: Database session
        
    Returns:
        Created account
    """
    try:
        # Check if account already exists
        existing = await crud.get_account_by_email(db, account.email)
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Account with this email already exists"
            )
        
        # Create account
        new_account = await crud.create_account(
            db,
            email=account.email,
            password=account.password,
            provider=account.provider
        )
        
        await db.commit()
        
        logger.info("account_created_api", account_id=new_account.id, email=account.email)
        
        return AccountResponse(
            id=new_account.id,
            email=new_account.email,
            provider=new_account.provider,
            status=new_account.status.value,
            proxy_id=new_account.proxy_id,
            created_at=str(new_account.created_at),
            updated_at=str(new_account.updated_at) if new_account.updated_at else None
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("account_creation_failed_api", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create account: {str(e)}"
        )


@router.get("/accounts", response_model=List[AccountResponse])
async def list_accounts(
    skip: int = 0,
    limit: int = 100,
    status_filter: Optional[str] = None,
    db: AsyncSession = Depends(get_db)
):
    """
    List accounts with pagination and filtering.
    
    Args:
        skip: Number of records to skip
        limit: Maximum number of records to return
        status_filter: Filter by status
        db: Database session
        
    Returns:
        List of accounts
    """
    try:
        account_status = None
        if status_filter:
            try:
                account_status = AccountStatus(status_filter)
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid status: {status_filter}"
                )
        
        accounts = await crud.list_accounts(db, skip=skip, limit=limit, status=account_status)
        
        return [
            AccountResponse(
                id=acc.id,
                email=acc.email,
                provider=acc.provider,
                status=acc.status.value,
                proxy_id=acc.proxy_id,
                created_at=str(acc.created_at),
                updated_at=str(acc.updated_at) if acc.updated_at else None
            )
            for acc in accounts
        ]
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("account_list_failed_api", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list accounts: {str(e)}"
        )


@router.get("/accounts/{account_id}", response_model=AccountResponse)
async def get_account(
    account_id: int,
    db: AsyncSession = Depends(get_db)
):
    """
    Get account by ID.
    
    Args:
        account_id: Account ID
        db: Database session
        
    Returns:
        Account details
    """
    account = await crud.get_account(db, account_id)
    
    if not account:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Account not found"
        )
    
    return AccountResponse(
        id=account.id,
        email=account.email,
        provider=account.provider,
        status=account.status.value,
        proxy_id=account.proxy_id,
        created_at=str(account.created_at),
        updated_at=str(account.updated_at) if account.updated_at else None
    )


@router.post("/accounts/{account_id}/process", response_model=TaskResponse)
async def process_account(
    account_id: int,
    request: ProcessAccountRequest = ProcessAccountRequest(),
    db: AsyncSession = Depends(get_db)
):
    """
    Queue account for processing.
    
    Args:
        account_id: Account ID
        request: Processing request
        db: Database session
        
    Returns:
        Task information
    """
    # Check account exists
    account = await crud.get_account(db, account_id)
    if not account:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Account not found"
        )
    
    # Queue task
    task = process_account_task.delay(account_id, request.action)
    
    logger.info("account_task_queued", account_id=account_id, task_id=task.id, action=request.action)
    
    return TaskResponse(
        task_id=task.id,
        account_id=account_id,
        action=request.action,
        status="queued"
    )


@router.post("/accounts/{account_id}/validate", response_model=TaskResponse)
async def validate_account(
    account_id: int,
    db: AsyncSession = Depends(get_db)
):
    """
    Validate account credentials.
    
    Args:
        account_id: Account ID
        db: Database session
        
    Returns:
        Task information
    """
    # Check account exists
    account = await crud.get_account(db, account_id)
    if not account:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Account not found"
        )
    
    # Queue validation task
    task = validate_account_task.delay(account_id)
    
    logger.info("account_validation_queued", account_id=account_id, task_id=task.id)
    
    return TaskResponse(
        task_id=task.id,
        account_id=account_id,
        action="validate",
        status="queued"
    )


@router.get("/accounts/{account_id}/logs", response_model=List[AccountLogResponse])
async def get_account_logs(
    account_id: int,
    limit: int = 100,
    db: AsyncSession = Depends(get_db)
):
    """
    Get logs for an account.
    
    Args:
        account_id: Account ID
        limit: Maximum number of logs
        db: Database session
        
    Returns:
        List of logs
    """
    # Check account exists
    account = await crud.get_account(db, account_id)
    if not account:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Account not found"
        )
    
    logs = await crud.get_account_logs(db, account_id, limit=limit)
    
    return [
        AccountLogResponse(
            id=log.id,
            account_id=log.account_id,
            action=log.action,
            status=log.status,
            message=log.message,
            timestamp=str(log.timestamp)
        )
        for log in logs
    ]


@router.delete("/accounts/{account_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_account(
    account_id: int,
    db: AsyncSession = Depends(get_db)
):
    """
    Delete an account.
    
    Args:
        account_id: Account ID
        db: Database session
    """
    success = await crud.delete_account(db, account_id)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Account not found"
        )
    
    logger.info("account_deleted_api", account_id=account_id)
    return None
