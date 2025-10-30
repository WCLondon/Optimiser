# Quick Start Guide - Local Development

This guide will help you get the BNG Optimiser running locally with the new backend architecture.

## Prerequisites

- Docker and Docker Compose installed
- PostgreSQL database (or use Docker Compose setup)
- Python 3.11+ (for standalone mode)

## Option 1: Full Stack with Docker Compose (Recommended)

### 1. Configure Environment

Create a `.env` file in the project root:

```bash
# Database (use your PostgreSQL connection)
DATABASE_URL=postgresql://user:password@host:5432/optimiser_db

# Or use a local PostgreSQL in Docker
# DATABASE_URL=postgresql://optimiser:optimiser@postgres:5432/optimiser
```

### 2. Start All Services

```bash
make local-up
```

This starts:
- Redis (job queue and cache)
- FastAPI backend (port 8000)
- RQ workers (2 replicas)
- Streamlit frontend (port 8501)

### 3. Access the Application

- **Frontend UI**: http://localhost:8501
- **Backend API**: http://localhost:8000
- **API Documentation**: http://localhost:8000/docs

### 4. View Logs

```bash
# All services
make local-logs

# Specific service
docker-compose logs -f backend
docker-compose logs -f worker
docker-compose logs -f frontend
```

### 5. Stop Services

```bash
make local-down
```

## Option 2: Standalone Mode (Original)

Run the Streamlit app without the backend:

```bash
# Install dependencies
pip install -r requirements.txt

# Run app
streamlit run app.py
```

This runs in legacy mode without background job processing.

## Option 3: Frontend + Backend (Manual)

### Terminal 1: Start Redis

```bash
docker run -p 6379:6379 redis:7-alpine
```

### Terminal 2: Start Backend

```bash
# Install dependencies
pip install -r backend/requirements.txt

# Set environment
export REDIS_HOST=localhost
export REDIS_PORT=6379
export DATABASE_URL=postgresql://...

# Run backend
cd backend
uvicorn app:app --reload --host 0.0.0.0 --port 8000
```

### Terminal 3: Start Worker

```bash
# Set environment
export REDIS_HOST=localhost
export REDIS_PORT=6379
export DATABASE_URL=postgresql://...

# Run worker
python backend/worker.py
```

### Terminal 4: Start Frontend

```bash
# Set environment
export BACKEND_URL=http://localhost:8000
export DATABASE_URL=postgresql://...

# Run frontend
streamlit run app.py
```

## Testing the Setup

### 1. Check Backend Health

```bash
curl http://localhost:8000/health
```

Expected response:
```json
{
  "status": "ok",
  "redis": "connected",
  "timestamp": "2025-10-30T09:00:00"
}
```

### 2. Test Job Creation

```bash
curl -X POST http://localhost:8000/jobs \
  -H "Content-Type: application/json" \
  -d '{
    "demand_df": {"habitat_name": ["Grassland"], "units_required": [10.0]},
    "target_lpa": "Winchester",
    "target_nca": "South Downs"
  }'
```

### 3. Check Job Status

```bash
curl http://localhost:8000/jobs/{job_id}
```

### 4. Run Validation Tests

```bash
python test_backend_validation.py
```

Expected: All tests should pass ✅

## Troubleshooting

### Redis Connection Failed

```bash
# Check if Redis is running
docker ps | grep redis

# Or check Redis directly
redis-cli ping
```

### Backend Not Starting

Check logs:
```bash
docker-compose logs backend
```

Common issues:
- Redis not available: Start Redis first
- Port 8000 already in use: Change port or stop other service
- Database connection error: Check DATABASE_URL

### Worker Not Processing Jobs

```bash
# Check worker logs
docker-compose logs worker

# Check Redis queue
docker-compose exec redis redis-cli
> LLEN rq:queue:jobs
```

### Frontend Can't Reach Backend

Check environment variable:
```bash
echo $BACKEND_URL
# Should be: http://localhost:8000
```

In Docker Compose, this is set automatically to `http://backend:8000`.

## Development Workflow

### Making Changes

1. **Backend changes**: Edit files in `backend/`, then restart:
   ```bash
   docker-compose restart backend worker
   ```

2. **Frontend changes**: Streamlit auto-reloads, just refresh browser

3. **Database schema changes**: 
   - Update `database.py`
   - Restart frontend: `docker-compose restart frontend`

### Debugging

#### Backend with breakpoints:
```bash
# Stop docker-compose backend
docker-compose stop backend

# Run manually with debugger
cd backend
python -m pdb app.py
```

#### Frontend with debugger:
```bash
docker-compose stop frontend
streamlit run app.py --server.port 8501
```

### Testing Changes

```bash
# Run backend validation
python test_backend_validation.py

# Test API manually
curl http://localhost:8000/health

# Check worker is processing
docker-compose logs -f worker
```

## Database Setup

### Using Docker Compose (Easy)

Add to `docker-compose.yml`:

```yaml
  postgres:
    image: postgres:15-alpine
    environment:
      POSTGRES_DB: optimiser
      POSTGRES_USER: optimiser
      POSTGRES_PASSWORD: optimiser
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data
```

### Using Existing PostgreSQL

1. Create database:
   ```sql
   CREATE DATABASE optimiser;
   CREATE USER optimiser WITH PASSWORD 'yourpassword';
   GRANT ALL PRIVILEGES ON DATABASE optimiser TO optimiser;
   ```

2. Set DATABASE_URL:
   ```bash
   export DATABASE_URL=postgresql://optimiser:yourpassword@localhost:5432/optimiser
   ```

## Monitoring

### Check Service Status

```bash
make test-backend
make test-frontend
```

### View Metrics

```bash
# Redis info
make redis-cli
> INFO stats
> LLEN rq:queue:jobs
```

### Check Logs

```bash
# All logs
make local-logs

# Specific service
make worker-logs
```

## Next Steps

- Review [ARCHITECTURE.md](ARCHITECTURE.md) for system design
- See [cloudrun.md](cloudrun.md) for Cloud Run deployment
- See [flyio.md](flyio.md) for Fly.io deployment
- Check [README.md](README.md) for feature documentation

## Getting Help

If you encounter issues:
1. Check logs: `make local-logs`
2. Verify services are running: `docker-compose ps`
3. Test connectivity: `make test-backend`
4. Review [ARCHITECTURE.md](ARCHITECTURE.md) for architecture details
