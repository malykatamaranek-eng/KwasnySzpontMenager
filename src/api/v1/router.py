"""API v1 router."""
from fastapi import APIRouter
from src.api.v1.endpoints import accounts, proxies

api_router = APIRouter()

# Include endpoint routers
api_router.include_router(
    accounts.router,
    prefix="/accounts",
    tags=["accounts"]
)

api_router.include_router(
    proxies.router,
    prefix="/proxies",
    tags=["proxies"]
)
