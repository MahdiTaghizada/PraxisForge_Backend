# PraxisForge Setup Guide

Complete step-by-step guide to get the PraxisForge backend running on your local machine.

---

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Environment Configuration](#1-environment-configuration)
3. [Docker Deployment](#2-docker-deployment)
4. [Database & Vector Store Setup](#3-database--vector-store-setup)
5. [Health Check & Validation](#4-health-check--validation)
6. [Local Development (Optional)](#5-local-development-optional)
7. [Troubleshooting](#6-troubleshooting)

---

## Prerequisites

- **Docker Desktop** (Windows/Mac) or Docker Engine + Docker Compose (Linux)
- **Python 3.12+** (for local development only)
- **API Keys** (required):
  - [Google AI Studio](https://aistudio.google.com/apikey) - Gemini API key
  - [Groq Console](https://console.groq.com/keys) - Groq API key  
  - [Tavily](https://tavily.com/) - Tavily Search API key

---

## 1. Environment Configuration

### Create your `.env` file

```powershell
# Copy the example file
Copy-Item .env.example .env
```

### Edit `.env` with your credentials

Open `.env` in your editor and fill in the required values:

```env
# ============================================
# REQUIRED - PostgreSQL (keep defaults for Docker)
# ============================================
POSTGRES_HOST=postgres
POSTGRES_PORT=5432
POSTGRES_USER=praxisforge
POSTGRES_PASSWORD=your_secure_password_here
POSTGRES_DB=praxisforge

# ============================================
# REQUIRED - Qdrant Vector Database (keep defaults for Docker)
# ============================================
QDRANT_URL=http://qdrant:6333
QDRANT_COLLECTION_NAME=praxisforge

# ============================================
# REQUIRED - AI API Keys (get from providers)
# ============================================
GEMINI_API_KEY=your_gemini_api_key_here
GROQ_API_KEY=your_groq_api_key_here
TAVILY_API_KEY=your_tavily_api_key_here

# ============================================
# REQUIRED - JWT Authentication
# ============================================
# Note: PraxisForge delegates user creation and token generation to 
# the `backend-forge` microservice.
# The keys below must exactly match those in `backend-forge/.env`.
JWT_SECRET=your_jwt_secret_here_minimum_32_chars
JWT_ALGORITHM=HS256

# ============================================
# Application Settings (optional, defaults shown)
# ============================================
APP_ENV=development
DEBUG=true
LOG_LEVEL=INFO
```

### Generate a secure JWT secret

```powershell
# PowerShell - generate a secure random key
[Convert]::ToBase64String((1..48 | ForEach-Object { Get-Random -Maximum 256 }))
```

---

## 2. Docker Deployment

### Start all services

```powershell
# Build and start containers in detached mode
docker compose up --build -d
```

This starts three containers:
- `praxisforge-postgres` - PostgreSQL 16 database (port 5432)
- `praxisforge-qdrant` - Qdrant vector database (port 6333/6334)
- `praxisforge-app` - FastAPI application (port 8000)

### Monitor startup logs

```powershell
# Watch all logs
docker compose logs -f

# Watch only the app logs
docker compose logs -f app
```

Wait until you see:
```
INFO:     Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)
```

### Service management commands

```powershell
# Stop all services
docker compose down

# Stop and remove volumes (clears all data)
docker compose down -v

# Restart a specific service
docker compose restart app

# View running containers
docker compose ps
```

---

## 3. Database & Vector Store Setup

### Automatic Setup (via Docker)

When the app container starts, it automatically:
1. Creates all PostgreSQL tables via SQLAlchemy
2. Initializes the Qdrant collection with proper indexes

You should see in logs:
```
INFO:root:Database tables ensured
INFO:root:Qdrant collection ensured
```

### Manual Migration (Alternative)

If you prefer to manage migrations explicitly:

```powershell
# Run inside the app container
docker compose exec app alembic upgrade head
```

### Manual Qdrant Initialization (Standalone)

If running Qdrant outside Docker:

```powershell
# Set environment for local Qdrant
$env:QDRANT_URL = "http://localhost:6333"

# Run initialization script
python scripts/init_qdrant.py
```

---

## 4. Health Check & Validation

### Quick health check

```powershell
# Basic health status
Invoke-RestMethod http://localhost:8000/health
```

Expected response (all services healthy):
```json
{
  "status": "healthy",
  "version": "0.2.0",
  "services": {
    "postgres": {
      "status": "healthy",
      "message": "Connected",
      "latency_ms": 2.5
    },
    "qdrant": {
      "status": "healthy",
      "message": "Collection 'praxisforge' has 0 points",
      "latency_ms": 15.3
    }
  }
}
```

### Kubernetes-style probes

```powershell
# Readiness probe (returns 200 if ready for traffic)
Invoke-RestMethod http://localhost:8000/health/ready

# Liveness probe (returns 200 if process is alive)
Invoke-RestMethod http://localhost:8000/health/live
```

### API Documentation

Open in browser:
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

### Test the API

```powershell
# Create a test project (requires valid JWT - adjust for your auth setup)
$headers = @{ "Authorization" = "Bearer YOUR_JWT_TOKEN" }

$body = @{
    name = "Test Project"
    description = "My first PraxisForge project"
    mode = "startup"
} | ConvertTo-Json

Invoke-RestMethod -Uri http://localhost:8000/api/v1/projects `
    -Method POST -Headers $headers -Body $body -ContentType "application/json"
```

---

## 5. Local Development (Optional)

For development without Docker:

### Create virtual environment

```powershell
# Create venv
python -m venv .venv

# Activate it
.\.venv\Scripts\Activate.ps1

# Install dependencies
pip install -r requirements.txt
```

### Start services manually

```powershell
# Start only postgres and qdrant via Docker
docker compose up postgres qdrant -d

# Update .env for local development
# Change POSTGRES_HOST to localhost
# Change QDRANT_URL to http://localhost:6333

# Run migrations
alembic upgrade head

# Initialize Qdrant
python scripts/init_qdrant.py

# Start the FastAPI server
uvicorn src.presentation.main:app --reload --host 0.0.0.0 --port 8000
```

### Running tests

```powershell
# Install test dependencies (if not in requirements.txt)
pip install pytest pytest-asyncio httpx

# Run all tests
pytest

# Run with coverage
pytest --cov=src
```

---

## 6. Troubleshooting

### Common Issues

#### Port 5432 already in use (PostgreSQL)

```powershell
# Find what's using the port
netstat -ano | findstr :5432

# Or change the port in docker-compose.yml:
# ports:
#   - "5433:5432"  # Use 5433 externally
```

#### Port 8000 already in use

```powershell
# Find the process
netstat -ano | findstr :8000

# Kill it (replace PID)
Stop-Process -Id <PID> -Force
```

#### Container exits immediately

```powershell
# Check logs for the specific container
docker compose logs app

# Common causes:
# - Missing .env file
# - Invalid API keys
# - Typo in environment variables
```

#### "Cannot connect to Qdrant" error

```powershell
# Verify Qdrant is running
docker compose ps qdrant

# Check Qdrant health directly
Invoke-RestMethod http://localhost:6333/collections
```

#### "Connection refused" to PostgreSQL

```powershell
# Inside Docker, use 'postgres' as host
# Outside Docker, use 'localhost'

# Verify connectivity
docker compose exec postgres pg_isready -U praxisforge
```

#### API key errors (401/403)

- **Gemini**: Verify at https://aistudio.google.com/apikey
- **Groq**: Verify at https://console.groq.com/keys
- **Tavily**: Verify at https://tavily.com/

```powershell
# Test Gemini API key directly
$env:GEMINI_API_KEY = "your_key"
python -c "import google.generativeai as genai; genai.configure(api_key='$env:GEMINI_API_KEY'); print('OK')"
```

#### Database migration errors

```powershell
# Reset database (WARNING: deletes all data)
docker compose down -v
docker compose up --build -d

# Or run fresh migration
docker compose exec app alembic downgrade base
docker compose exec app alembic upgrade head
```

### Viewing Detailed Logs

```powershell
# Enable debug logging
# Set in .env: LOG_LEVEL=DEBUG

# View real-time logs with timestamps
docker compose logs -f --timestamps

# Export logs to file
docker compose logs > praxisforge-logs.txt
```

### Getting Help

1. Check the API docs at `/docs` for endpoint details
2. Review the health endpoint for service status
3. Check container logs for error messages
4. Verify all environment variables are set correctly

---

## Quick Reference

| Service   | Internal URL         | External URL              |
|-----------|---------------------|---------------------------|
| FastAPI   | http://app:8000     | http://localhost:8000     |
| PostgreSQL| postgres:5432       | localhost:5432            |
| Qdrant    | http://qdrant:6333  | http://localhost:6333     |

| Endpoint          | Purpose                          |
|-------------------|----------------------------------|
| `/health`         | Detailed service health status   |
| `/health/ready`   | Kubernetes readiness probe       |
| `/health/live`    | Kubernetes liveness probe        |
| `/docs`           | Swagger UI documentation         |
| `/redoc`          | ReDoc documentation              |

---

**Ready to build your next project!** 🚀
