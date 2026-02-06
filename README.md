# Account Automation System

Production-ready automation system for managing and automating account operations with Facebook integration, email processing, and proxy management.

## Features

- **Full Account Automation**: Automated login, 2FA handling, and password reset for Facebook accounts
- **Multi-Provider Email Support**: wp.pl, o2.pl, onet.pl, interia.pl
- **Proxy Management**: Health checking, rotation, and automatic dead proxy removal
- **Async Architecture**: Full asyncio implementation for high performance
- **Task Queue**: Celery-based task processing with Redis backend
- **Real-time Updates**: WebSocket support for live log streaming
- **Production Ready**: Docker containerization, database migrations, security features

## Tech Stack

### Backend
- Python 3.12+ with asyncio
- FastAPI for REST API
- Celery + Redis for task queuing
- PostgreSQL for data storage
- SQLAlchemy 2.0 + Alembic for ORM
- Playwright for browser automation
- Pydantic for validation
- AES-256-GCM encryption for passwords

### Infrastructure
- Docker + Docker Compose
- Redis for caching and pub/sub
- Flower for task monitoring

## Quick Start

### 1. Clone the repository

```bash
git clone <repository-url>
cd KwasnySzpontMenager
```

### 2. Set up environment

```bash
cp .env.example .env
```

Generate encryption key:
```bash
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

Update `.env` with your keys.

### 3. Start the system

```bash
docker-compose up --build
```

### 4. Access services

- **API**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs
- **Flower (Task Monitor)**: http://localhost:5555
- **PostgreSQL**: localhost:5432
- **Redis**: localhost:6379

## API Endpoints

### Accounts

- `POST /api/v1/accounts` - Create new account
- `GET /api/v1/accounts` - List accounts
- `GET /api/v1/accounts/{id}` - Get account details
- `POST /api/v1/accounts/{id}/process` - Queue account processing task
- `POST /api/v1/accounts/{id}/validate` - Validate account credentials
- `GET /api/v1/accounts/{id}/logs` - Get account logs
- `DELETE /api/v1/accounts/{id}` - Delete account

### Proxies

- `POST /api/v1/proxies` - Add new proxy
- `GET /api/v1/proxies` - List proxies
- `GET /api/v1/proxies/{id}` - Get proxy details
- `POST /api/v1/proxies/test` - Test all proxies
- `POST /api/v1/proxies/{id}/test` - Test single proxy
- `DELETE /api/v1/proxies/{id}` - Delete proxy

### WebSocket

- `WS /ws/logs/{account_id}` - Real-time account logs

## Usage Examples

### Create Account

```bash
curl -X POST http://localhost:8000/api/v1/accounts \
  -H "Content-Type: application/json" \
  -d '{
    "email": "user@wp.pl",
    "password": "secretpassword",
    "provider": "wp.pl"
  }'
```

### Add Proxy

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

### Process Account

```bash
curl -X POST http://localhost:8000/api/v1/accounts/1/process \
  -H "Content-Type: application/json" \
  -d '{
    "action": "login"
  }'
```

## Architecture

```
src/
├── core/              # Core configuration and utilities
├── db/                # Database models and CRUD
├── modules/           # Business logic modules
│   ├── proxy_manager/
│   ├── email_discovery/
│   ├── auth_validator/
│   ├── email_processor/
│   └── facebook_automation/
├── task_system/       # Celery tasks
├── api/               # REST API endpoints
└── main.py            # FastAPI application
```

## Modules

### Proxy Manager
- Automatic health testing
- Round-robin rotation
- Connection pooling
- Dead proxy removal

### Email Discovery
- Auto-detection of email providers
- Playwright-based login automation
- Cookie and session management
- IMAP configuration retrieval

### Auth Validator
- Credential verification
- Rate limiting per provider
- Exponential backoff retry
- Session persistence

### IMAP Processor
- Async IMAP operations
- Facebook email filtering
- 6/8-digit code extraction
- Auto-reconnect on timeout

### Facebook Automation
- 2FA handling with code retrieval
- Password reset automation
- OAuth token extraction
- Security prompt handling

## Security Features

- **AES-256-GCM Encryption**: All passwords encrypted at rest
- **Secure Storage**: Sensitive data never logged
- **Anti-Detection**: Browser fingerprint randomization
- **Session Isolation**: Per-proxy session management

## Development

### Run migrations

```bash
docker-compose exec backend alembic upgrade head
```

### Create new migration

```bash
docker-compose exec backend alembic revision --autogenerate -m "description"
```

### View logs

```bash
docker-compose logs -f backend
docker-compose logs -f celery-worker
```

### Access database

```bash
docker-compose exec postgres psql -U admin -d automation
```

## Monitoring

Access Flower dashboard at http://localhost:5555 to monitor:
- Active tasks
- Task history
- Worker status
- Task success/failure rates

## Environment Variables

See `.env.example` for all available configuration options.

Key variables:
- `DATABASE_URL` - PostgreSQL connection string
- `REDIS_URL` - Redis connection string
- `ENCRYPTION_KEY` - AES-256 encryption key
- `JWT_SECRET` - JWT signing secret
- `PLAYWRIGHT_HEADLESS` - Run browser in headless mode
- `CELERY_BROKER_URL` - Celery broker URL
- `CELERY_RESULT_BACKEND` - Celery result backend URL

## Troubleshooting

### Database connection issues
```bash
docker-compose restart postgres
docker-compose exec backend alembic upgrade head
```

### Celery workers not processing
```bash
docker-compose restart celery-worker
docker-compose logs celery-worker
```

### Playwright browser issues
```bash
docker-compose exec backend playwright install chromium
docker-compose exec backend playwright install-deps chromium
```

## License

Proprietary - All rights reserved

## Support

For issues and questions, please open an issue on GitHub.
