# New Architecture Summary

## What Changed

The BNG Optimiser has been refactored from a monolithic Streamlit app into a modern microservices architecture:

### Before (Monolith)
```
User → Streamlit App → Optimization (blocks UI) → PostgreSQL
```

### After (Microservices)
```
User → Streamlit Frontend → FastAPI Backend → Redis Queue → RQ Workers → PostgreSQL
                                              ↓
                                         Cache (12h TTL)
```

## Key Improvements

### 1. **Non-Blocking UI** 🚀
- Optimization runs in background workers
- UI remains responsive during processing
- Real-time progress updates

### 2. **Smart Caching** 💾
- Identical requests return instantly from cache
- 12-hour TTL for results
- Input-based deterministic hashing

### 3. **Horizontal Scaling** 📈
- Add more workers to handle increased load
- Independent scaling of frontend/backend/workers
- No single point of failure

### 4. **Easy Deployment** 🐳
- Docker containers for all components
- One-command local setup: `make local-up`
- Cloud Run and Fly.io deployment guides

### 5. **Better Performance** ⚡
- Form-based inputs (no reruns while typing)
- Cached database queries
- Optimized resource management

## Architecture Overview

### Components

1. **Streamlit Frontend** (Port 8501)
   - User interface
   - Form-based input collection
   - Job submission and result polling
   - Session state management

2. **FastAPI Backend** (Port 8000)
   - RESTful API for job management
   - Result caching with Redis
   - Health monitoring
   - API documentation at `/docs`

3. **RQ Workers**
   - Background job processing
   - Heavy optimization computations
   - Isolated execution environment
   - Automatic retries on failure

4. **Redis**
   - Job queue (via RQ)
   - Result caching (12-hour TTL)
   - Distributed state management

5. **PostgreSQL**
   - Reference data (Banks, Pricing, etc.)
   - Submission history
   - User data

### Data Flow

1. User enters demand and location
2. Frontend submits job to backend API
3. Backend checks cache for existing result
4. If cached: return immediately
5. If not: enqueue job for worker
6. Worker processes optimization
7. Result stored in cache
8. Frontend polls and displays result

## Quick Start

### Local Development with Docker Compose

```bash
# Start all services
make local-up

# Access application
open http://localhost:8501

# View logs
make local-logs

# Stop services
make local-down
```

See [QUICKSTART.md](QUICKSTART.md) for detailed setup instructions.

### Standalone Mode (Original)

```bash
# Run without backend
streamlit run app.py
```

## Deployment

### Cloud Run (Google Cloud)

```bash
# Set project
export PROJECT_ID=your-project-id

# Build and deploy
make deploy-all PROJECT_ID=$PROJECT_ID
```

See [cloudrun.md](cloudrun.md) for complete guide.

### Fly.io

```bash
# Deploy services
flyctl deploy --config fly.backend.toml
flyctl deploy --config fly.frontend.toml
```

See [flyio.md](flyio.md) for complete guide.

## API Endpoints

### Backend API (Port 8000)

- `GET /health` - Health check
- `POST /jobs` - Create optimization job
  ```json
  {
    "demand_df": {...},
    "target_lpa": "Winchester",
    "target_nca": "South Downs"
  }
  ```
- `GET /jobs/{job_id}` - Get job status and result
- `DELETE /cache/{key}` - Clear cache entry
- `POST /cache/clear-all` - Clear all cache

Interactive docs: http://localhost:8000/docs

## Performance Improvements

### Streamlit Optimizations (Phase A)

- ✅ Form-based input collection
- ✅ `@st.cache_data` for expensive functions
- ✅ `@st.cache_resource` for database connections
- ✅ Session state for result persistence
- ✅ Progress indicators

### Backend Processing (Phase B)

- ✅ Asynchronous job processing
- ✅ Redis-based result caching
- ✅ Input hashing for cache keys
- ✅ Horizontal worker scaling
- ✅ Automatic retries

### Infrastructure (Phase C)

- ✅ Docker containerization
- ✅ Docker Compose for local dev
- ✅ Cloud Run deployment guide
- ✅ Fly.io deployment guide
- ✅ Makefile automation

## Testing

### Validation Tests

```bash
# Run backend validation
python test_backend_validation.py
```

Expected output:
```
✅ All tests passed!
```

### Manual Testing

```bash
# Test backend health
curl http://localhost:8000/health

# Test job creation
curl -X POST http://localhost:8000/jobs \
  -H "Content-Type: application/json" \
  -d '{"demand_df": {...}}'

# Test job status
curl http://localhost:8000/jobs/{job_id}
```

## Monitoring

### Service Status

```bash
# Check all services
docker-compose ps

# Check specific service
docker-compose logs backend
docker-compose logs worker
```

### Redis Monitoring

```bash
# Connect to Redis CLI
make redis-cli

# Check queue length
LLEN rq:queue:jobs

# Check cached keys
KEYS cache:*
```

### Health Checks

```bash
# Backend health
make test-backend

# Frontend health
make test-frontend
```

## Migration Guide

### From Monolith to Microservices

The migration is **backward compatible**. The app can run in two modes:

#### Standalone Mode (Original)
```bash
# No BACKEND_URL set
streamlit run app.py
```
Optimization runs in-process (blocking UI).

#### Backend Mode (New)
```bash
# Set BACKEND_URL
export BACKEND_URL=http://localhost:8000
streamlit run app.py
```
Optimization runs in background workers (non-blocking UI).

### Configuration Changes

No database schema changes required. Simply add environment variables:

```bash
# Backend
export REDIS_HOST=redis
export REDIS_PORT=6379
export CACHE_TTL=43200

# Frontend (optional)
export BACKEND_URL=http://backend:8000
```

## Cost Estimates

### Local Development
- **Free** (runs on your machine)

### Cloud Run (Production)
- Backend: ~$50/month (2 vCPU, 4GB RAM, min 1 instance)
- Frontend: ~$50/month (2 vCPU, 4GB RAM, min 1 instance)
- Workers: ~$70/month (2x Compute Engine instances)
- Redis: ~$35/month (Memorystore Basic 1GB)
- PostgreSQL: ~$135/month (Cloud SQL)
- **Total**: ~$340/month

### Fly.io (Production)
- Backend: ~$24/month (2x shared-cpu-2x)
- Frontend: ~$24/month (2x shared-cpu-2x)
- Workers: ~$16/month (2x shared-cpu-2x)
- Redis: ~$10/month (Upstash 2GB)
- PostgreSQL: ~$29/month (dedicated-cpu-2x)
- **Total**: ~$103/month

See deployment guides for detailed pricing.

## Security Considerations

1. **API Authentication**: Add auth middleware for production
2. **Rate Limiting**: Implement on job creation endpoint
3. **Input Validation**: Validate all inputs before processing
4. **Secrets Management**: Use secret managers (not env vars)
5. **Network Security**: Use VPCs for service communication
6. **HTTPS Only**: Always use HTTPS in production
7. **CORS**: Restrict origins in production

## Troubleshooting

### Backend Not Responding
- Check if backend is running: `docker-compose ps backend`
- View logs: `docker-compose logs backend`
- Test health: `curl http://localhost:8000/health`

### Workers Not Processing
- Check worker logs: `docker-compose logs worker`
- Verify Redis connection: `make redis-cli` → `PING`
- Check queue: `LLEN rq:queue:jobs`

### Results Not Cached
- Check Redis connection
- Verify CACHE_TTL is set
- Check memory: `INFO memory` in Redis CLI

### Slow Performance
- Scale workers: `docker-compose scale worker=4`
- Check CPU/memory usage
- Review optimization complexity

## Documentation

- [QUICKSTART.md](QUICKSTART.md) - Local setup guide
- [ARCHITECTURE.md](ARCHITECTURE.md) - Detailed architecture
- [cloudrun.md](cloudrun.md) - Cloud Run deployment
- [flyio.md](flyio.md) - Fly.io deployment
- [README.md](README.md) - Main documentation

## Support

For issues or questions:
1. Check [QUICKSTART.md](QUICKSTART.md) for setup help
2. Review [ARCHITECTURE.md](ARCHITECTURE.md) for design details
3. Check logs: `make local-logs`
4. Run tests: `python test_backend_validation.py`
5. Open an issue on GitHub

## Future Enhancements

- [ ] WebSocket support for real-time updates
- [ ] Advanced queue prioritization
- [ ] Multi-region deployment
- [ ] ML-based cache predictions
- [ ] GraphQL API option
- [ ] Analytics dashboard
- [ ] Scheduled background jobs

## Contributing

When contributing:
1. Keep worker tasks stateless
2. Document API endpoints
3. Add tests for new features
4. Update deployment guides
5. Maintain backward compatibility

## License

[Same as main project]
