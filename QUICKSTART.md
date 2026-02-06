# Quick Start Guide

## Prerequisites

- Docker and Docker Compose installed
- At least 2GB RAM available
- Ports 8000, 5555, 5432, 6379 available

## Start the System

### 1. Copy environment file
```bash
cp .env.example .env
```

### 2. Start all services
```bash
docker-compose up --build
```

This will start:
- PostgreSQL database (port 5432)
- Redis (port 6379)
- Backend API (port 8000)
- Celery worker
- Celery beat
- Flower monitoring (port 5555)

### 3. Wait for services to be ready

Watch for these log messages:
- `postgres     | database system is ready to accept connections`
- `redis        | Ready to accept connections`
- `backend      | Application startup complete`
- `celery-worker | celery@... ready`

This usually takes 30-60 seconds on first run.

### 4. Access the services

- **API Documentation**: http://localhost:8000/docs
- **API Alternative Docs**: http://localhost:8000/redoc
- **Flower Dashboard**: http://localhost:5555
- **Health Check**: http://localhost:8000/health

## First API Call

### Create an account:
```bash
curl -X POST http://localhost:8000/api/v1/accounts \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@wp.pl",
    "password": "testpassword123",
    "provider": "wp.pl"
  }'
```

Expected response:
```json
{
  "id": 1,
  "email": "test@wp.pl",
  "provider": "wp.pl",
  "status": "pending",
  "proxy_id": null,
  "created_at": "2024-01-01T12:00:00"
}
```

### Add a proxy:
```bash
curl -X POST http://localhost:8000/api/v1/proxies \
  -H "Content-Type: application/json" \
  -d '{
    "host": "proxy.example.com",
    "port": 8080,
    "username": "user",
    "password": "pass"
  }'
```

### Process an account:
```bash
curl -X POST http://localhost:8000/api/v1/accounts/1/process \
  -H "Content-Type: application/json" \
  -d '{
    "action": "login"
  }'
```

Response will include a `task_id` that you can use to track the task in Flower.

## Monitoring

### View task status in Flower
Open http://localhost:5555 and navigate to:
- **Tasks** - View all running and completed tasks
- **Workers** - View worker status
- **Monitor** - Real-time monitoring

### View logs
```bash
# Backend API logs
docker-compose logs -f backend

# Celery worker logs
docker-compose logs -f celery-worker

# All logs
docker-compose logs -f
```

## Stopping the System

```bash
# Stop all services
docker-compose down

# Stop and remove volumes (WARNING: deletes all data)
docker-compose down -v
```

## Troubleshooting

### Database connection error
```bash
docker-compose restart postgres
docker-compose exec backend alembic upgrade head
```

### Port already in use
Change ports in `docker-compose.yml`:
```yaml
ports:
  - "8001:8000"  # Change 8000 to 8001
```

### Reset everything
```bash
docker-compose down -v
docker-compose up --build
```

## Next Steps

1. Add real proxy servers to the system
2. Add email accounts to automate
3. Monitor tasks in Flower dashboard
4. Check account logs via API
5. Connect WebSocket for real-time updates

## WebSocket Example

```javascript
const ws = new WebSocket('ws://localhost:8000/ws/logs/1');

ws.onmessage = (event) => {
  console.log('Log update:', event.data);
};

ws.send('ping');  // Keep connection alive
```

## API Documentation

Full interactive API documentation available at:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## Support

For issues, check:
1. Docker logs: `docker-compose logs`
2. Service health: `curl http://localhost:8000/health`
3. Database status: `docker-compose ps postgres`
4. Redis status: `docker-compose ps redis`
