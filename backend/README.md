# BNG Optimiser Backend

FastAPI microservice for handling heavy computation in background workers.

## Architecture

- **FastAPI app** (`app.py`): REST API endpoints for job submission and status
- **RQ Worker** (`worker.py`): Background worker processing optimization jobs
- **Redis**: Message queue and result cache

## Setup

### Local Development

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Start Redis:
```bash
# Using Docker
docker run -d -p 6379:6379 redis:7-alpine

# Or using local Redis
redis-server
```

3. Start the worker:
```bash
python worker.py
```

4. Start the API server:
```bash
uvicorn app:app --host 0.0.0.0 --port 8000 --reload
```

### Environment Variables

- `REDIS_HOST`: Redis hostname (default: `redis`)
- `REDIS_PORT`: Redis port (default: `6379`)
- `REDIS_DB`: Redis database number (default: `0`)

## API Endpoints

### Health Check
```http
GET /health
```

Returns API and Redis connection status.

### Create Job
```http
POST /jobs
Content-Type: application/json

{
  "params": {
    "demand": [...],
    "target_lpa": "...",
    "target_nca": "...",
    "contract_size": "..."
  }
}
```

Returns:
- If cached: `{job_id: null, status: "finished", result: {...}}`
- If new: `{job_id: "uuid", status: "queued"}`

### Get Job Status
```http
GET /jobs/{job_id}
```

Returns:
- `{job_id: "uuid", status: "queued"}`
- `{job_id: "uuid", status: "started"}`
- `{job_id: "uuid", status: "finished", result: {...}}`
- `{job_id: "uuid", status: "failed", error: "..."}`

## Caching

Results are automatically cached in Redis for 24 hours based on input hash.
Duplicate requests with identical parameters return instantly from cache.

## Deployment

See parent directory `docker/` for containerization and deployment configurations.
