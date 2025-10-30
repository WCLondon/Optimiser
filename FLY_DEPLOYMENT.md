# Fly.io Deployment Guide

This guide covers deploying the BNG Optimiser to Fly.io.

## Prerequisites

1. Fly.io account (sign up at https://fly.io)
2. `flyctl` CLI installed and authenticated
3. Docker installed locally

## Architecture

The deployment consists of:
- **Frontend**: Streamlit app on Fly.io
- **Backend**: FastAPI on Fly.io
- **Worker**: Background workers on Fly.io
- **Redis**: Fly.io Redis (Upstash)

## Step-by-Step Deployment

### 1. Install Fly CLI

```bash
# macOS
brew install flyctl

# Linux
curl -L https://fly.io/install.sh | sh

# Windows
iwr https://fly.io/install.ps1 -useb | iex
```

### 2. Authenticate

```bash
flyctl auth login
```

### 3. Create Redis Instance

```bash
# Create Redis using Upstash
flyctl redis create bng-redis --region lhr

# Note the connection details provided
```

### 4. Deploy Backend

```bash
# Launch backend (first time)
flyctl launch --config fly.backend.toml --no-deploy

# Set Redis connection (from step 3)
flyctl secrets set \
  REDIS_HOST=your-redis-host.upstash.io \
  REDIS_PORT=6379 \
  REDIS_PASSWORD=your-redis-password \
  --app bng-backend

# Deploy
flyctl deploy --config fly.backend.toml

# Get backend URL
export BACKEND_URL=$(flyctl info --app bng-backend --json | jq -r '.Hostname')
echo "Backend URL: https://$BACKEND_URL"
```

### 5. Deploy Worker

```bash
# Create worker app
flyctl launch --config fly.worker.toml --no-deploy

# Set Redis connection
flyctl secrets set \
  REDIS_HOST=your-redis-host.upstash.io \
  REDIS_PORT=6379 \
  REDIS_PASSWORD=your-redis-password \
  --app bng-worker

# Deploy
flyctl deploy --config fly.worker.toml

# Scale workers (2 instances)
flyctl scale count 2 --app bng-worker
```

### 6. Deploy Frontend

```bash
# Launch frontend
flyctl launch --config fly.frontend.toml --no-deploy

# Set backend URL and database credentials
flyctl secrets set \
  BACKEND_URL=https://bng-backend.fly.dev \
  DATABASE_URL=postgresql://user:pass@host:port/db \
  --app bng-frontend

# Deploy
flyctl deploy --config fly.frontend.toml

# Get frontend URL
flyctl info --app bng-frontend
```

## Scaling

### Adjust Instance Count

```bash
# Scale backend (1-4 instances based on load)
flyctl scale count 2 --app bng-backend

# Scale workers (2-4 instances)
flyctl scale count 3 --app bng-worker

# Scale frontend (1-3 instances)
flyctl scale count 2 --app bng-frontend
```

### Adjust VM Size

```bash
# Upgrade backend to larger VM
flyctl scale vm shared-cpu-4x --app bng-backend

# Upgrade frontend for more memory
flyctl scale vm shared-cpu-8x --app bng-frontend

# Upgrade worker for heavy computation
flyctl scale vm shared-cpu-4x --app bng-worker
```

## Cost Optimization

### Recommended Settings

**Backend**:
- VM: shared-cpu-2x (2GB RAM)
- Instances: 1-2
- Auto-stop: disabled (always ready)

**Frontend**:
- VM: shared-cpu-4x (4GB RAM)
- Instances: 1-2
- Auto-stop: disabled (avoid cold starts)

**Worker**:
- VM: shared-cpu-2x (2GB RAM)
- Instances: 2-4 (based on load)
- Auto-stop: enabled (cost savings)

**Redis**:
- Upstash Redis: ~$10/month for 256MB

### Expected Costs (USD/month)

- Backend: ~$15-30
- Frontend: ~$30-60 (needs more RAM)
- Worker (2 instances): ~$30-60
- Redis: ~$10
- **Total**: ~$85-160/month

## Monitoring

### View Logs

```bash
# Real-time logs
flyctl logs --app bng-backend
flyctl logs --app bng-frontend
flyctl logs --app bng-worker

# Historical logs
flyctl logs --app bng-backend --since 1h
```

### Metrics

```bash
# Check app status
flyctl status --app bng-backend

# View metrics
flyctl dashboard metrics --app bng-backend
```

### Monitoring Dashboard

Access Fly.io dashboard: https://fly.io/dashboard

## Troubleshooting

### Backend Health Check Failing

```bash
# Check backend health
curl https://bng-backend.fly.dev/health

# View recent logs
flyctl logs --app bng-backend

# SSH into instance
flyctl ssh console --app bng-backend
```

### Redis Connection Issues

```bash
# Test Redis connection
flyctl redis connect bng-redis

# Check Redis status
flyctl redis status bng-redis
```

### Frontend Not Loading

```bash
# Check frontend status
flyctl status --app bng-frontend

# View logs
flyctl logs --app bng-frontend

# Restart
flyctl apps restart bng-frontend
```

## Updates

### Deploy New Version

```bash
# Build and deploy backend
flyctl deploy --config fly.backend.toml

# Deploy frontend
flyctl deploy --config fly.frontend.toml

# Deploy worker
flyctl deploy --config fly.worker.toml
```

### Rollback

```bash
# List releases
flyctl releases --app bng-backend

# Rollback to previous version
flyctl releases rollback --app bng-backend
```

## Custom Domains

```bash
# Add custom domain to frontend
flyctl certs add bng.yourdomain.com --app bng-frontend

# Check certificate status
flyctl certs show bng.yourdomain.com --app bng-frontend
```

Add DNS record:
```
CNAME bng.yourdomain.com bng-frontend.fly.dev
```

## Cleanup

```bash
# Delete apps
flyctl apps destroy bng-backend
flyctl apps destroy bng-frontend
flyctl apps destroy bng-worker

# Delete Redis
flyctl redis destroy bng-redis
```

## Advanced: Custom Regions

Deploy to multiple regions for better global performance:

```bash
# Add region to app
flyctl regions add fra --app bng-backend
flyctl regions add syd --app bng-backend

# Scale in specific region
flyctl scale count 1 --region lhr --app bng-backend
flyctl scale count 1 --region fra --app bng-backend
```

## Support

- Fly.io Docs: https://fly.io/docs
- Community: https://community.fly.io
- Status: https://status.fly.io
