# BNG Optimiser - Architecture Overview

## New Architecture (FastAPI Backend + Streamlit Frontend)

The BNG Optimiser has been refactored into a microservices architecture for improved performance, scalability, and maintainability.

### Architecture Diagram

```
┌─────────────┐
│   Browser   │
└──────┬──────┘
       │
       v
┌─────────────────────┐
│  Streamlit Frontend │  (Port 8501)
│  - UI/UX            │
│  - Form controls    │
│  - Job submission   │
│  - Result display   │
└──────┬──────────────┘
       │ HTTP
       v
┌─────────────────────┐
│  FastAPI Backend    │  (Port 8000)
│  - Job queue API    │
│  - Result caching   │
│  - Health checks    │
└──────┬──────────────┘
       │
       v
┌─────────────────────┐       ┌──────────────┐
│      Redis          │◄──────┤ RQ Workers   │
│  - Job queue        │       │ - Optimization│
│  - Result cache     │       │ - Heavy compute│
└─────────────────────┘       └──────────────┘
       │
       v
┌─────────────────────┐
│    PostgreSQL       │
│  - Reference data   │
│  - Submissions      │
└─────────────────────┘
```

### Components

#### 1. **Streamlit Frontend** (`app.py`)
- User interface and interaction
- Form-based input to prevent unnecessary reruns
- Polls backend for job status
- Displays results with caching

#### 2. **FastAPI Backend** (`backend/app.py`)
- RESTful API for job management
- Input hashing for deterministic caching
- Redis-based result caching (12-hour TTL)
- Health monitoring endpoints

**Endpoints**:
- `GET /health` - Health check
- `POST /jobs` - Create optimization job
- `GET /jobs/{job_id}` - Get job status/result
- `DELETE /cache/{key}` - Clear specific cache entry
- `POST /cache/clear-all` - Clear all cached results

#### 3. **RQ Workers** (`backend/worker.py`)
- Background job processing
- Isolated heavy computation
- Horizontal scaling capability
- Automatic retry on failure

#### 4. **Redis**
- Job queue (via RQ)
- Result caching
- Distributed locking

#### 5. **PostgreSQL**
- Reference tables (Banks, Pricing, etc.)
- Submission history
- User/admin data

### Performance Improvements

#### Phase A: Streamlit Rerun Control
- ✅ Form-based input collection (no reruns while typing)
- ✅ `@st.cache_data` for expensive pure functions
- ✅ `@st.cache_resource` for long-lived connections
- ✅ Session state for result persistence
- ✅ Progress indicators for long operations

#### Phase B: Background Processing
- ✅ Non-blocking optimization via job queue
- ✅ Intelligent caching (input hash → cached result)
- ✅ Horizontal worker scaling
- ✅ Graceful degradation if workers are busy

#### Phase C: Deployment
- ✅ Docker containers for all components
- ✅ One-command local deployment (`make local-up`)
- ✅ Cloud Run deployment guide
- ✅ Fly.io deployment guide
- ✅ Makefile for common operations

### Key Benefits

1. **Snappy UI**: No more freezing during optimization
2. **Smart Caching**: Identical requests return instantly
3. **Scalable**: Add more workers to handle load
4. **Resilient**: Workers can restart without losing state
5. **Observable**: Clear separation enables better monitoring

## Deployment Options

### Local Development

Start all services:
```bash
make local-up
```

Access:
- Frontend: http://localhost:8501
- Backend API: http://localhost:8000
- API docs: http://localhost:8000/docs

Stop services:
```bash
make local-down
```

### Cloud Run (Google Cloud)

See [cloudrun.md](cloudrun.md) for detailed instructions.

Quick deploy:
```bash
make deploy-all PROJECT_ID=your-project-id
```

### Fly.io

See [flyio.md](flyio.md) for detailed instructions.

Quick deploy:
```bash
flyctl deploy --config fly.backend.toml
flyctl deploy --config fly.frontend.toml
```

## Migration from Monolith

### What Changed

**Before**: Single Streamlit app with synchronous optimization
- User clicks "Optimize" → UI freezes
- Slow for complex optimizations
- No caching across sessions
- All computation in-process

**After**: Distributed architecture with async job processing
- User clicks "Optimize" → Job submitted to queue
- UI remains responsive with progress indicator
- Results cached in Redis
- Workers handle computation

### Backward Compatibility

The existing `app.py` functionality remains unchanged:
- All existing features work the same
- Database schema unchanged
- API contracts preserved
- Can still run standalone (without backend)

### Enabling Backend Mode

Set environment variable:
```bash
export BACKEND_URL=http://localhost:8000
streamlit run app.py
```

If `BACKEND_URL` is not set, app runs in legacy standalone mode.

## Development

### Running Tests

```bash
# Test backend API
curl http://localhost:8000/health

# Test job creation
curl -X POST http://localhost:8000/jobs \
  -H "Content-Type: application/json" \
  -d '{"demand_df": {}, "target_lpa": "Test"}'

# Test job status
curl http://localhost:8000/jobs/{job_id}
```

### Adding New Features

When adding new optimization logic:
1. Add function to `backend/tasks.py`
2. Update API models in `backend/app.py`
3. Update frontend to call new endpoint
4. Add tests
5. Update documentation

### Monitoring

#### Backend Logs
```bash
docker-compose logs -f backend
```

#### Worker Logs
```bash
docker-compose logs -f worker
```

#### Redis CLI
```bash
make redis-cli
```

## Configuration

### Environment Variables

**Backend**:
- `REDIS_HOST` - Redis hostname (default: redis)
- `REDIS_PORT` - Redis port (default: 6379)
- `CACHE_TTL` - Cache TTL in seconds (default: 43200 = 12 hours)
- `DATABASE_URL` - PostgreSQL connection string

**Frontend**:
- `BACKEND_URL` - Backend API URL (if using backend mode)
- `DATABASE_URL` - PostgreSQL connection string

**Worker**:
- `REDIS_HOST` - Redis hostname
- `REDIS_PORT` - Redis port
- `DATABASE_URL` - PostgreSQL connection string

### Secrets

Store in `.streamlit/secrets.toml`:
```toml
[database]
url = "postgresql://..."

[auth]
username = "..."
password = "..."

[admin]
password = "..."
```

## Troubleshooting

### Common Issues

**"Backend not responding"**
- Check if backend service is running: `make test-backend`
- Verify `BACKEND_URL` is set correctly
- Check backend logs: `docker-compose logs backend`

**"Jobs not processing"**
- Check worker status: `docker-compose logs worker`
- Verify Redis connection: `make redis-cli` then `PING`
- Check queue status in Redis: `LLEN rq:queue:jobs`

**"Results not cached"**
- Check Redis connection
- Verify `CACHE_TTL` is set
- Check Redis memory usage: `INFO memory`

**"Slow optimization"**
- Scale workers: `docker-compose scale worker=4`
- Check worker CPU/memory usage
- Review optimization algorithm complexity

### Health Checks

Check service health:
```bash
# Backend
curl http://localhost:8000/health

# Frontend (Streamlit)
curl http://localhost:8501/_stcore/health
```

## Performance Tuning

### Worker Scaling

```bash
# Local (docker-compose)
docker-compose scale worker=4

# Cloud Run
gcloud run services update bng-worker --max-instances=10

# Fly.io
flyctl scale count 4 -a bng-worker
```

### Cache Configuration

Adjust TTL based on your needs:
```bash
export CACHE_TTL=86400  # 24 hours
```

Clear cache if needed:
```bash
curl -X POST http://localhost:8000/cache/clear-all
```

### Database Optimization

- Enable connection pooling (SQLAlchemy default)
- Add indexes for frequent queries
- Use read replicas for heavy read workloads

## Security Considerations

1. **API Authentication**: Add authentication middleware for production
2. **Rate Limiting**: Implement rate limiting on job creation
3. **Input Validation**: Validate all inputs before queueing jobs
4. **Secrets Management**: Use secret managers (not env vars) in production
5. **Network Security**: Use VPCs/private networks for service communication
6. **HTTPS**: Always use HTTPS in production
7. **CORS**: Restrict CORS origins in production

## Monitoring and Observability

### Metrics to Track

- Job queue length
- Average job processing time
- Cache hit rate
- API response times
- Worker utilization
- Database connection pool usage

### Recommended Tools

- **Prometheus** + Grafana for metrics
- **Sentry** for error tracking
- **Cloud Logging** (GCP) or **CloudWatch** (AWS)
- **Redis Insights** for Redis monitoring

## Future Enhancements

Potential improvements:
- [ ] WebSocket support for real-time job updates
- [ ] Advanced queue prioritization
- [ ] Multi-region deployment with data locality
- [ ] ML-based optimization caching predictions
- [ ] GraphQL API alternative
- [ ] Scheduled background jobs (cleanup, reports)
- [ ] Advanced analytics dashboard

## Contributing

When contributing to the backend architecture:
1. Keep worker tasks stateless and pure
2. Document all API endpoints in OpenAPI spec
3. Add integration tests for new features
4. Update deployment guides
5. Consider backward compatibility

## License

[Same as main project]

## Support

For architecture-specific questions:
- Backend API issues: Check `backend/app.py`
- Worker issues: Check `backend/worker.py` and task logs
- Deployment issues: See `cloudrun.md` or `flyio.md`
- Performance issues: Review monitoring metrics
