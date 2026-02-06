"""Main FastAPI application."""
import asyncio
from contextlib import asynccontextmanager
from typing import Dict, Set
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
import structlog
from redis import asyncio as aioredis
from src.core.config import settings
from src.db.database import init_db, close_db
from src.api.v1.router import api_router

logger = structlog.get_logger()

# WebSocket connection manager
class ConnectionManager:
    """Manage WebSocket connections."""
    
    def __init__(self):
        """Initialize connection manager."""
        self.active_connections: Dict[int, Set[WebSocket]] = {}
    
    async def connect(self, websocket: WebSocket, account_id: int):
        """Connect a WebSocket."""
        await websocket.accept()
        if account_id not in self.active_connections:
            self.active_connections[account_id] = set()
        self.active_connections[account_id].add(websocket)
        logger.info("websocket_connected", account_id=account_id)
    
    def disconnect(self, websocket: WebSocket, account_id: int):
        """Disconnect a WebSocket."""
        if account_id in self.active_connections:
            self.active_connections[account_id].discard(websocket)
            if not self.active_connections[account_id]:
                del self.active_connections[account_id]
        logger.info("websocket_disconnected", account_id=account_id)
    
    async def broadcast_to_account(self, account_id: int, message: str):
        """Broadcast message to all connections for an account."""
        if account_id in self.active_connections:
            disconnected = set()
            for connection in self.active_connections[account_id]:
                try:
                    await connection.send_text(message)
                except Exception as e:
                    logger.error("websocket_send_failed", error=str(e))
                    disconnected.add(connection)
            
            # Remove disconnected connections
            for conn in disconnected:
                self.active_connections[account_id].discard(conn)


manager = ConnectionManager()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    # Startup
    logger.info("application_startup")
    
    # Initialize database
    try:
        await init_db()
        logger.info("database_initialized")
    except Exception as e:
        logger.error("database_init_failed", error=str(e))
    
    # Initialize Redis for pub/sub
    try:
        app.state.redis = await aioredis.from_url(
            settings.REDIS_URL,
            encoding="utf-8",
            decode_responses=True
        )
        logger.info("redis_connected")
    except Exception as e:
        logger.error("redis_connection_failed", error=str(e))
    
    # Start Redis listener task
    app.state.listener_task = asyncio.create_task(redis_listener(app.state.redis))
    
    yield
    
    # Shutdown
    logger.info("application_shutdown")
    
    # Cancel listener task
    if hasattr(app.state, 'listener_task'):
        app.state.listener_task.cancel()
        try:
            await app.state.listener_task
        except asyncio.CancelledError:
            pass
    
    # Close Redis
    if hasattr(app.state, 'redis'):
        await app.state.redis.close()
        logger.info("redis_closed")
    
    # Close database
    try:
        await close_db()
        logger.info("database_closed")
    except Exception as e:
        logger.error("database_close_failed", error=str(e))


async def redis_listener(redis_client):
    """Listen for Redis pub/sub messages and broadcast to WebSocket clients."""
    try:
        pubsub = redis_client.pubsub()
        
        # Subscribe to all account log channels with pattern
        await pubsub.psubscribe("account:*:logs")
        
        logger.info("redis_listener_started")
        
        async for message in pubsub.listen():
            if message["type"] == "pmessage":
                channel = message["channel"]
                data = message["data"]
                
                # Extract account_id from channel name (account:{id}:logs)
                try:
                    account_id = int(channel.split(":")[1])
                    await manager.broadcast_to_account(account_id, data)
                except Exception as e:
                    logger.error("redis_message_processing_failed", error=str(e))
    except asyncio.CancelledError:
        logger.info("redis_listener_cancelled")
        await pubsub.unsubscribe()
    except Exception as e:
        logger.error("redis_listener_error", error=str(e))


# Create FastAPI app
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API router
app.include_router(api_router, prefix="/api/v1")


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "name": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "status": "running",
        "docs": "/docs"
    }


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": settings.APP_NAME
    }


@app.websocket("/ws/logs/{account_id}")
async def websocket_logs(websocket: WebSocket, account_id: int):
    """
    WebSocket endpoint for real-time account logs.
    
    Args:
        websocket: WebSocket connection
        account_id: Account ID to subscribe to
    """
    await manager.connect(websocket, account_id)
    
    try:
        # Send initial connection message
        await websocket.send_text(f"Connected to logs for account {account_id}")
        
        # Keep connection alive
        while True:
            # Wait for messages from client (ping/pong)
            try:
                data = await websocket.receive_text()
                if data == "ping":
                    await websocket.send_text("pong")
            except WebSocketDisconnect:
                break
            
    except WebSocketDisconnect:
        logger.info("websocket_disconnect", account_id=account_id)
    except Exception as e:
        logger.error("websocket_error", account_id=account_id, error=str(e))
    finally:
        manager.disconnect(websocket, account_id)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "src.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
