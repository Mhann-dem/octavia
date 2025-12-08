# Octavia Backend

Video and audio translation service with Go API Gateway and Python AI Worker.

## Stack

- **API Gateway**: Go 1.25.4, Fiber v2, GORM, PostgreSQL, Redis
- **AI Worker**: Python 3.10, Celery, RabbitMQ
- **Database**: PostgreSQL 15
- **Cache**: Redis 7
- **Message Queue**: RabbitMQ 3

## Prerequisites

### Required

- Docker & Docker Compose
- Go 1.25.4+
- Python 3.10+
- Make
- Git

### Verify Installation

```bash
go version          # Should output go1.25.4 or higher
python --version    # Should output Python 3.10.x or higher
docker --version    # Should output Docker version 24.x or higher
make --version      # Should output GNU Make 4.x or higher
```

## Project Structure

```
backend/
├── api-gateway/                 # Go API server
│   ├── cmd/main.go             # Entry point
│   ├── config/                 # Configuration
│   ├── internal/
│   │   ├── handlers/           # HTTP handlers
│   │   ├── models/             # Database models
│   │   ├── db/                 # Database setup
│   │   └── server/             # Server setup
│   ├── Dockerfile
│   ├── go.mod
│   └── go.sum
├── ai-worker/                   # Python worker
│   ├── app/
│   │   ├── main.py             # Entry point
│   │   ├── worker.py           # Task processor
│   │   ├── config.py           # Configuration
│   │   └── tasks/              # Task modules
│   ├── Dockerfile
│   ├── requirements.txt
│   └── config.py
├── docker-compose.yml
├── docker-compose.prod.yml
├── .env.example
├── Makefile
└── README.md
```

## Quick Start

### 1. Clone & Setup

```bash
cd octavia
cp backend/.env.example backend/.env
cd backend
```

### 2. Start All Services

```bash
# Start database, Redis, RabbitMQ in Docker
make dev

# In separate terminals, start API Gateway and Worker
make api
make worker

# View logs
make logs-api
make logs-worker
```

Access:

- **API**: http://localhost:8080
- **RabbitMQ**: http://localhost:15672 (guest/guest)

### 3. Test the System

```bash
# Run comprehensive API tests
./scritps/test_api.sh

# Or manually test key endpoints
curl -X POST http://localhost:8080/api/v1/auth/signup \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com",
    "password": "testpass123",
    "name": "Test User"
  }'
```

---

## Development Workflow

### Environment Variables

Edit `backend/.env`:

```env
# Database
DATABASE_URL=postgres://octavia:octavia@localhost:5432/octavia?sslmode=disable

# Redis
REDIS_URL=localhost:6379

# RabbitMQ
RABBITMQ_URL=amqp://guest:guest@localhost:5672/
RABBITMQ_QUEUE=jobs.queue
RABBITMQ_DLQ=jobs.dlq

# API
PORT=8080
SESSION_SECRET=dev_secret_change_in_production
SESSION_COOKIE_NAME=octavia_session
SESSION_TTL_SECONDS=86400

# Billing & Auth
SERVICE_API_KEY=dev_key_change_in_production

# Storage
STORAGE_PATH=./storage
UPLOAD_PATH=./storage/uploads
RESULTS_PATH=./storage/results

# Cost Configuration
COST_PER_MINUTE=0.10
```

### Available Make Commands

```bash
make dev            # Start database services (docker compose up)
make api            # Run API gateway (go run)
make worker         # Run AI worker (python app/main.py)
make build          # Build Docker images
make up             # Start all services (docker compose up -d)
make down           # Stop all services (docker compose down)
make test-api       # Run API tests
make test-worker    # Run worker tests (pytest)
make logs-api       # View API logs (docker compose logs -f)
make logs-worker    # View worker logs (docker compose logs -f)
make help           # Display all available commands
```

---

## Database Setup & Migrations

### Initial Setup

```bash
# Start services
make dev

# The database is automatically created with initial schema
# Verify connection
docker exec octavia-postgres-1 psql -U octavia -d octavia -c "\dt"
```

### Running Migrations

Migrations are handled by GORM in the `internal/db/` package.

```bash
# View current database tables
docker exec octavia-postgres-1 psql -U octavia -d octavia -c "\dt"

# Check users table
docker exec octavia-postgres-1 psql -U octavia -d octavia -c "SELECT * FROM users;"

# Check jobs table
docker exec octavia-postgres-1 psql -U octavia -d octavia -c "SELECT * FROM jobs;"
```

### Manual Database Operations

```bash
# Connect to database
docker exec -it octavia-postgres-1 psql -U octavia -d octavia

# Inside psql:
\dt                 # List all tables
\d users            # Describe users table
SELECT * FROM jobs; # Query jobs
\q                  # Exit
```

---

## API Gateway (Go)

### Directory Structure

```
api-gateway/
├── cmd/main.go                  # Application entry point
├── config/config.go             # Configuration management
├── internal/
│   ├── db/
│   │   ├── db.go               # Database initialization
│   │   ├── redis.go            # Redis setup
│   │   └── rabbitmq.go         # RabbitMQ setup
│   ├── handlers/
│   │   ├── auth.go             # Authentication endpoints
│   │   ├── jobs.go             # Job management endpoints
│   │   ├── billing.go          # Billing endpoints
│   │   └── sessions.go         # Session & middleware
│   ├── models/
│   │   ├── user.go             # User model
│   │   ├── job.go              # Job model
│   │   └── transaction.go      # Transaction model
│   └── server/server.go        # Server setup & routing
├── Dockerfile
├── go.mod
└── go.sum
```

### Build & Run

```bash
# Development
make api

# Production build
make build

# Test
make test-api
```

### Key Endpoints

| Method | Endpoint                 | Description            |
| ------ | ------------------------ | ---------------------- |
| POST   | `/api/v1/auth/signup`    | Register new user      |
| POST   | `/api/v1/auth/login`     | User login             |
| POST   | `/api/v1/auth/logout`    | User logout            |
| POST   | `/api/v1/jobs`           | Create translation job |
| GET    | `/api/v1/jobs/:id`       | Get job status         |
| POST   | `/api/v1/billing/credit` | Add account credits    |

---

## AI Worker (Python)

### Directory Structure

```
ai-worker/
├── app/
│   ├── main.py                  # Worker entry point
│   ├── worker.py                # Task processor
│   ├── config.py                # Configuration
│   └── tasks/
│       ├── transcribe.py        # Speech-to-text
│       ├── translate.py         # Text translation
│       └── tts.py               # Text-to-speech
├── Dockerfile
├── requirements.txt
└── config.py
```

### Setup & Dependencies

```bash
# Install dependencies
pip install -r ai-worker/requirements.txt

# Run worker
make worker

# Test worker
make test-worker
```

### Configuration

Edit `ai-worker/config.py`:

```python
class Config:
    RABBITMQ_URL = os.getenv("RABBITMQ_URL", "amqp://guest:guest@localhost:5672/")
    RABBITMQ_QUEUE = os.getenv("RABBITMQ_QUEUE", "jobs.queue")
    API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8080")
    USE_OPENAI = os.getenv("USE_OPENAI", "false").lower() == "true"
    USE_COQUI = os.getenv("USE_COQUI", "false").lower() == "true"
```

---

## Testing

### Run All Tests

```bash
# API tests (Go)
make test-api

# Worker tests (Python)
make test-worker
```

### API Testing Script

```bash
# Comprehensive end-to-end testing
./scripts/test_api.sh

# What it tests:
# 1. User signup
# 2. Presign upload URL
# 3. Job creation
# 4. Get job status
# 5. Billing credit function
# 6. Logout
# 7. Protected endpoint rejection after logout
```

### Manual Testing

```bash
# 1. Signup
curl -X POST http://localhost:8080/api/v1/auth/signup \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com",
    "password": "securepass123",
    "name": "Test User"
  }'

# 2. Create job
curl -X POST http://localhost:8080/api/v1/jobs \
  -H "Content-Type: application/json" \
  -H "Cookie: octavia_session=YOUR_SESSION_ID" \
  -d '{
    "source_file_url": "http://localhost:8080/upload/test.mp3",
    "source_lang": "en",
    "target_lang": "es",
    "duration": 60
  }'

# 3. Get job status
curl http://localhost:8080/api/v1/jobs/JOB_ID \
  -H "Cookie: octavia_session=YOUR_SESSION_ID"
```

---

## Docker Operations

### Build Images

```bash
# Build all
make build

# Build specific service
docker build -t octavia-api-gateway ./api-gateway
docker build -t octavia-ai-worker ./ai-worker
```

### Run with Docker Compose

```bash
# Development (includes database, Redis, RabbitMQ)
make dev

# Production compose
docker compose -f docker-compose.prod.yml up -d

# View logs
docker compose logs -f api-gateway
docker compose logs -f ai-worker

# Stop services
make down
```

### Access Services

```bash
# RabbitMQ Management Console
http://localhost:15672
# Username: guest
# Password: guest

# Database
docker exec -it octavia-postgres-1 psql -U octavia -d octavia

# Redis CLI
docker exec -it octavia-redis-1 redis-cli

# Container logs
docker compose logs api-gateway -f
docker compose logs ai-worker -f
```

---

## Debugging

### View Logs

```bash
# API Gateway
make logs-api

# AI Worker
make logs-worker

# All services
docker compose logs -f
```

### Common Issues

**Issue**: Port already in use

```bash
# Find and kill process on port 8080
lsof -ti:8080 | xargs kill -9

# Or use different port
PORT=8081 make api
```

**Issue**: Redis connection error

```bash
# Check Redis is running
docker compose ps redis

# Restart Redis
docker compose restart redis
```

**Issue**: Database connection refused

```bash
# Check Postgres is running
docker compose ps postgres

# View Postgres logs
docker compose logs postgres

# Restart Postgres
docker compose restart postgres
```

**Issue**: RabbitMQ connection error

```bash
# Check RabbitMQ is running
docker compose ps rabbitmq

# View RabbitMQ logs
docker compose logs rabbitmq
```

---

## Performance & Monitoring

### Health Checks

```bash
# API Gateway health
curl http://localhost:8080/health

# Worker health (if exposed)
curl http://localhost:8000/health
```

### Resource Usage

```bash
# Monitor Docker containers
docker stats

# Monitor processes
top
# Press 'm' to sort by memory
# Press 'q' to quit
```

### Database Queries

```bash
# Connect to database
docker exec -it octavia-postgres-1 psql -U octavia -d octavia

# Slow query log
SELECT * FROM pg_stat_statements ORDER BY mean_exec_time DESC;

# Connection count
SELECT count(*) FROM pg_stat_activity;
```

---

## Production Deployment

### Environment Setup

```bash
# Copy and edit for production
cp .env.example .env.production

# Edit critical values:
# - DATABASE_URL (use Neon)
# - REDIS_URL (use Upstash)
# - SESSION_SECRET (strong random value)
# - SERVICE_API_KEY (strong random value)
```

### Build & Deploy

```bash
# Build images
make build

# Tag for registry
docker tag octavia-api-gateway:latest registry.example.com/octavia-api-gateway:latest
docker tag octavia-ai-worker:latest registry.example.com/octavia-ai-worker:latest

# Push to registry
docker push registry.example.com/octavia-api-gateway:latest
docker push registry.example.com/octavia-ai-worker:latest

# Deploy with docker-compose.prod.yml
docker compose -f docker-compose.prod.yml up -d
```

---

## Troubleshooting Checklist

- [ ] Docker is running (`docker ps`)
- [ ] Services are up (`make dev` completed)
- [ ] Database is accessible (`docker exec octavia-postgres-1 psql ...`)
- [ ] Redis is accessible (`docker exec octavia-redis-1 redis-cli ping`)
- [ ] RabbitMQ is accessible (http://localhost:15672)
- [ ] API Gateway is running (`curl http://localhost:8080/health`)
- [ ] Test script passes (`./scripts/test_api.sh`)

---

## Support & Documentation

- [Go Documentation](https://golang.org/doc/)
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [PostgreSQL Documentation](https://www.postgresql.org/docs/)
- [Redis Documentation](https://redis.io/documentation)
- [RabbitMQ Documentation](https://www.rabbitmq.com/documentation.html)
- [Docker Documentation](https://docs.docker.com/)

---

**Last Updated**: 2025-11-23  
**Status**: ✅ Ready for Development  
**Version**: 1.0.0
