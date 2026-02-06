"""Proxy endpoints."""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel
import structlog
from src.db.database import get_db
from src.db import crud
from src.modules.proxy_manager.manager import ProductionProxyManager
from src.task_system.tasks import test_all_proxies_task

logger = structlog.get_logger()

router = APIRouter()


# Pydantic models
class ProxyCreate(BaseModel):
    """Proxy creation model."""
    host: str
    port: int
    username: Optional[str] = None
    password: Optional[str] = None


class ProxyResponse(BaseModel):
    """Proxy response model."""
    id: int
    host: str
    port: int
    username: Optional[str] = None
    is_alive: bool
    last_tested: Optional[str] = None
    latency_ms: Optional[float] = None
    
    class Config:
        from_attributes = True


class ProxyTestResult(BaseModel):
    """Proxy test result model."""
    proxy_id: int
    host: str
    port: int
    success: bool
    latency_ms: Optional[float] = None
    error: Optional[str] = None


@router.post("/proxies", response_model=ProxyResponse, status_code=status.HTTP_201_CREATED)
async def add_proxy(
    proxy: ProxyCreate,
    db: AsyncSession = Depends(get_db)
):
    """
    Add a new proxy.
    
    Args:
        proxy: Proxy creation data
        db: Database session
        
    Returns:
        Created proxy
    """
    try:
        new_proxy = await crud.create_proxy(
            db,
            host=proxy.host,
            port=proxy.port,
            username=proxy.username,
            password=proxy.password
        )
        
        await db.commit()
        
        logger.info("proxy_added_api", proxy_id=new_proxy.id, host=proxy.host)
        
        return ProxyResponse(
            id=new_proxy.id,
            host=new_proxy.host,
            port=new_proxy.port,
            username=new_proxy.username,
            is_alive=new_proxy.is_alive,
            last_tested=str(new_proxy.last_tested) if new_proxy.last_tested else None,
            latency_ms=new_proxy.latency_ms
        )
        
    except Exception as e:
        logger.error("proxy_add_failed_api", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to add proxy: {str(e)}"
        )


@router.get("/proxies", response_model=List[ProxyResponse])
async def list_proxies(
    alive_only: bool = False,
    db: AsyncSession = Depends(get_db)
):
    """
    List proxies.
    
    Args:
        alive_only: Filter to only alive proxies
        db: Database session
        
    Returns:
        List of proxies
    """
    try:
        proxies = await crud.list_proxies(db, alive_only=alive_only)
        
        return [
            ProxyResponse(
                id=p.id,
                host=p.host,
                port=p.port,
                username=p.username,
                is_alive=p.is_alive,
                last_tested=str(p.last_tested) if p.last_tested else None,
                latency_ms=p.latency_ms
            )
            for p in proxies
        ]
        
    except Exception as e:
        logger.error("proxy_list_failed_api", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list proxies: {str(e)}"
        )


@router.get("/proxies/{proxy_id}", response_model=ProxyResponse)
async def get_proxy(
    proxy_id: int,
    db: AsyncSession = Depends(get_db)
):
    """
    Get proxy by ID.
    
    Args:
        proxy_id: Proxy ID
        db: Database session
        
    Returns:
        Proxy details
    """
    proxy = await crud.get_proxy(db, proxy_id)
    
    if not proxy:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Proxy not found"
        )
    
    return ProxyResponse(
        id=proxy.id,
        host=proxy.host,
        port=proxy.port,
        username=proxy.username,
        is_alive=proxy.is_alive,
        last_tested=str(proxy.last_tested) if proxy.last_tested else None,
        latency_ms=proxy.latency_ms
    )


@router.post("/proxies/test")
async def test_proxies(db: AsyncSession = Depends(get_db)):
    """
    Test all proxies.
    
    Args:
        db: Database session
        
    Returns:
        Task information
    """
    # Queue test task
    task = test_all_proxies_task.delay()
    
    logger.info("proxy_test_queued", task_id=task.id)
    
    return {
        "task_id": task.id,
        "status": "queued",
        "message": "Proxy testing started"
    }


@router.post("/proxies/{proxy_id}/test", response_model=ProxyTestResult)
async def test_single_proxy(
    proxy_id: int,
    db: AsyncSession = Depends(get_db)
):
    """
    Test a single proxy.
    
    Args:
        proxy_id: Proxy ID
        db: Database session
        
    Returns:
        Test result
    """
    proxy = await crud.get_proxy(db, proxy_id)
    
    if not proxy:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Proxy not found"
        )
    
    # Test proxy
    proxy_manager = ProductionProxyManager(db)
    result = await proxy_manager.test_proxy(proxy)
    
    # Update proxy status
    await crud.update_proxy_health(
        db,
        proxy_id,
        is_alive=result["success"],
        latency_ms=result.get("latency_ms")
    )
    
    await db.commit()
    
    return ProxyTestResult(
        proxy_id=proxy_id,
        host=proxy.host,
        port=proxy.port,
        success=result["success"],
        latency_ms=result.get("latency_ms"),
        error=result.get("error")
    )


@router.delete("/proxies/{proxy_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_proxy(
    proxy_id: int,
    db: AsyncSession = Depends(get_db)
):
    """
    Delete a proxy.
    
    Args:
        proxy_id: Proxy ID
        db: Database session
    """
    from sqlalchemy import delete
    from src.db.models import Proxy
    
    result = await db.execute(
        delete(Proxy).where(Proxy.id == proxy_id)
    )
    await db.commit()
    
    if result.rowcount == 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Proxy not found"
        )
    
    logger.info("proxy_deleted_api", proxy_id=proxy_id)
    return None
