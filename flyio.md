# Fly.io Deployment Guide

This guide explains how to deploy the BNG Optimiser to Fly.io with Redis and PostgreSQL.

## Prerequisites

1. **Fly.io Account**: Sign up at https://fly.io
2. **flyctl CLI**: Install the Fly.io CLI
   ```bash
   curl -L https://fly.io/install.sh | sh
   ```
3. **Authenticate**:
   ```bash
   flyctl auth login
   ```

## Architecture

The deployment consists of:
- **Frontend**: Streamlit app (Fly.io app)
- **Backend**: FastAPI service (Fly.io app)
- **Worker**: RQ worker (Fly.io app)
- **Redis**: Upstash Redis or Fly.io Redis
- **PostgreSQL**: Fly.io Postgres

## Step 1: Create PostgreSQL Database

Create a Postgres cluster:

```bash
flyctl postgres create --name bng-postgres --region lhr --initial-cluster-size 1
```

Save the connection string provided (you'll need it later).

Create the database:
```bash
flyctl postgres connect -a bng-postgres
# In psql:
CREATE DATABASE optimiser;
CREATE USER bnguser WITH PASSWORD 'secure_password';
GRANT ALL PRIVILEGES ON DATABASE optimiser TO bnguser;
\q
```

## Step 2: Create Redis Instance

Option A - Use Upstash Redis (recommended):
```bash
# Sign up at upstash.com and create a Redis database
# Get connection details: host, port, password
```

Option B - Use Fly.io Redis:
```bash
flyctl redis create --name bng-redis --region lhr
```

Get Redis connection details:
```bash
flyctl redis status bng-redis
```

## Step 3: Deploy Backend

Initialize the backend app:

```bash
flyctl apps create bng-backend --org personal
```

Deploy backend:
```bash
flyctl deploy --config fly.backend.toml
```

Set secrets:
```bash
flyctl secrets set -a bng-backend \
  DATABASE_URL="postgresql://bnguser:password@bng-postgres.internal:5432/optimiser"
```

Get backend URL:
```bash
BACKEND_URL=$(flyctl info -a bng-backend --json | jq -r '.Hostname')
echo "Backend URL: https://$BACKEND_URL"
```

## Step 4: Deploy Worker

Create worker configuration:

```toml
# fly.worker.toml
app = "bng-worker"
primary_region = "lhr"

[build]
  dockerfile = "docker/Dockerfile.worker"

[env]
  REDIS_HOST = "bng-redis.internal"
  REDIS_PORT = "6379"

[[services]]
  # No HTTP service - this is a background worker

[[vm]]
  cpu_kind = "shared"
  cpus = 2
  memory_gb = 2
```

Deploy worker:
```bash
flyctl apps create bng-worker --org personal
flyctl deploy --config fly.worker.toml

# Set secrets
flyctl secrets set -a bng-worker \
  DATABASE_URL="postgresql://bnguser:password@bng-postgres.internal:5432/optimiser"
```

Scale workers:
```bash
flyctl scale count 2 -a bng-worker
```

## Step 5: Deploy Frontend

Deploy frontend:
```bash
flyctl apps create bng-frontend --org personal
flyctl deploy --config fly.frontend.toml
```

Set secrets:
```bash
flyctl secrets set -a bng-frontend \
  BACKEND_URL="https://bng-backend.fly.dev" \
  DATABASE_URL="postgresql://bnguser:password@bng-postgres.internal:5432/optimiser"
```

## Step 6: Configure Streamlit Secrets

Create a secret for Streamlit configuration:

```bash
# Create a file with secrets
cat > secrets.toml << EOF
[database]
url = "postgresql://bnguser:password@bng-postgres.internal:5432/optimiser"

[auth]
username = "WC0323"
password = "Wimborne"

[admin]
password = "WCAdmin2024"
EOF

# Deploy with secrets as a file mount
flyctl secrets set -a bng-frontend \
  STREAMLIT_SECRETS="$(base64 secrets.toml)"
```

Or use Fly.io volumes:
```bash
flyctl volumes create streamlit_secrets -a bng-frontend --region lhr --size 1
# Mount at /app/.streamlit/secrets.toml in fly.frontend.toml
```

## Step 7: Verify Deployment

Check all services:
```bash
flyctl status -a bng-backend
flyctl status -a bng-frontend
flyctl status -a bng-worker
```

Test backend:
```bash
curl https://bng-backend.fly.dev/health
```

Access frontend:
```bash
flyctl open -a bng-frontend
```

## Scaling

### Auto-scaling

Configure auto-scaling for each app:

```bash
# Backend (API)
flyctl scale count 2-10 -a bng-backend

# Frontend
flyctl scale count 1-5 -a bng-frontend

# Workers
flyctl scale count 2-4 -a bng-worker
```

### Manual scaling

```bash
# Scale up
flyctl scale count 5 -a bng-backend

# Scale down
flyctl scale count 1 -a bng-backend
```

### Machine size

```bash
# Increase resources
flyctl scale vm shared-cpu-2x --memory 4096 -a bng-backend
```

## Monitoring

### View logs

```bash
# Backend logs
flyctl logs -a bng-backend

# Follow logs
flyctl logs -a bng-backend -f

# Frontend logs
flyctl logs -a bng-frontend
```

### Metrics

```bash
flyctl dashboard -a bng-backend
```

### SSH into machine

```bash
flyctl ssh console -a bng-backend
```

## Custom Domain

Add custom domain:

```bash
flyctl certs create app.yourdomain.com -a bng-frontend
```

Add DNS records as instructed by Fly.io.

## Regions and Multi-Region

Deploy to multiple regions:

```bash
# Add region
flyctl regions add ams -a bng-backend  # Amsterdam
flyctl regions add sin -a bng-backend  # Singapore

# List regions
flyctl regions list -a bng-backend

# Scale per region
flyctl scale count 2 --region lhr -a bng-backend
flyctl scale count 1 --region ams -a bng-backend
```

## Secrets Management

List secrets:
```bash
flyctl secrets list -a bng-backend
```

Update secret:
```bash
flyctl secrets set DATABASE_URL="new-connection-string" -a bng-backend
```

Remove secret:
```bash
flyctl secrets unset SECRET_NAME -a bng-backend
```

## Updating

Deploy new version:
```bash
flyctl deploy --config fly.backend.toml
flyctl deploy --config fly.frontend.toml
flyctl deploy --config fly.worker.toml
```

Deploy without building (use existing image):
```bash
flyctl deploy --image gcr.io/project/bng-backend:latest -a bng-backend
```

## Rollback

List releases:
```bash
flyctl releases -a bng-backend
```

Rollback to previous version:
```bash
flyctl releases rollback -a bng-backend
```

## Cost Estimates

**Hobby tier** (development):
- 3 shared-cpu-1x apps (256MB): $0/month (free tier)
- Postgres (shared-cpu-1x, 10GB): $1.94/month
- Redis (256MB): $0/month (Upstash free tier)
- **Total**: ~$2/month

**Production tier**:
- Backend 2x shared-cpu-2x (4GB): ~$24/month
- Frontend 2x shared-cpu-2x (4GB): ~$24/month
- Workers 2x shared-cpu-2x (2GB): ~$16/month
- Postgres (dedicated-cpu-2x, 50GB): ~$29/month
- Redis (2GB, Upstash): ~$10/month
- **Total**: ~$103/month

Fly.io pricing: https://fly.io/docs/about/pricing/

## Troubleshooting

### App won't start

Check logs:
```bash
flyctl logs -a bng-backend
```

Check machine status:
```bash
flyctl status -a bng-backend
```

Restart machines:
```bash
flyctl machine restart --app bng-backend
```

### High latency

- Add more regions closer to users
- Increase machine resources
- Check database connection pooling
- Monitor Redis performance

### Worker not processing jobs

Check worker logs:
```bash
flyctl logs -a bng-worker
```

Verify Redis connection:
```bash
flyctl ssh console -a bng-worker
# Inside: redis-cli -h $REDIS_HOST ping
```

### Database connection issues

Test connection:
```bash
flyctl postgres connect -a bng-postgres
```

Check proxy status:
```bash
flyctl proxy 15432:5432 -a bng-postgres
# Connect locally: psql postgresql://user:pass@localhost:15432/optimiser
```

## Environment-Specific Configuration

### Development
```bash
flyctl secrets set -a bng-backend \
  ENV=development \
  DEBUG=true \
  LOG_LEVEL=debug
```

### Production
```bash
flyctl secrets set -a bng-backend \
  ENV=production \
  DEBUG=false \
  LOG_LEVEL=info
```

## Backup and Recovery

### Database backups

Fly.io Postgres includes automatic daily backups.

Manual backup:
```bash
flyctl postgres db pg_dump optimiser -a bng-postgres > backup.sql
```

Restore:
```bash
flyctl postgres connect -a bng-postgres < backup.sql
```

### Volume snapshots

```bash
flyctl volumes snapshots list <volume-id>
flyctl volumes snapshots create <volume-id>
```

## Security Best Practices

1. **Use secrets** for all sensitive data
2. **Enable authentication** for production apps
3. **Use private networking** for internal communication
4. **Regularly update** base images and dependencies
5. **Enable audit logging** in production
6. **Use strong passwords** for database and Redis
7. **Restrict access** with Fly.io Organizations and teams

## Support

For Fly.io-specific issues:
- Documentation: https://fly.io/docs
- Community: https://community.fly.io
- Status: https://status.fly.io

For application issues:
- Check logs: `flyctl logs -a APP_NAME`
- Test locally: `docker-compose up`
- Review Cloud Run guide for architecture details
