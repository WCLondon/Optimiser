# Cloud Run Deployment Guide

This guide covers deploying the BNG Optimiser to Google Cloud Run.

## Prerequisites

1. Google Cloud account with billing enabled
2. `gcloud` CLI installed and authenticated
3. Docker installed locally
4. Project ID and preferred region

## Architecture

The deployment consists of:
- **Frontend**: Streamlit app on Cloud Run
- **Backend**: FastAPI on Cloud Run
- **Worker**: Cloud Run Jobs (or GKE for persistent workers)
- **Redis**: Memorystore for Redis (or Cloud Run with persistent Redis)

## Step-by-Step Deployment

### 1. Set Up Project

```bash
# Set project ID
export PROJECT_ID=your-gcp-project
export REGION=europe-west2

# Configure gcloud
gcloud config set project $PROJECT_ID
gcloud config set run/region $REGION

# Enable required APIs
gcloud services enable \
  run.googleapis.com \
  containerregistry.googleapis.com \
  redis.googleapis.com
```

### 2. Set Up Redis (Memorystore)

```bash
# Create Redis instance
gcloud redis instances create bng-redis \
  --size=1 \
  --region=$REGION \
  --redis-version=redis_7_0

# Get Redis host
export REDIS_HOST=$(gcloud redis instances describe bng-redis \
  --region=$REGION \
  --format='get(host)')

echo "Redis host: $REDIS_HOST"
```

### 3. Build and Push Images

```bash
# Configure Docker for GCR
gcloud auth configure-docker

# Build and push backend
make push-backend PROJECT_ID=$PROJECT_ID

# Build and push frontend
make push-frontend PROJECT_ID=$PROJECT_ID

# Build and push worker
make push-worker PROJECT_ID=$PROJECT_ID
```

### 4. Deploy Backend

```bash
# Deploy backend API
gcloud run deploy bng-backend \
  --image gcr.io/$PROJECT_ID/bng-backend:latest \
  --platform managed \
  --region $REGION \
  --allow-unauthenticated \
  --min-instances 1 \
  --max-instances 10 \
  --memory 2Gi \
  --cpu 2 \
  --set-env-vars REDIS_HOST=$REDIS_HOST,REDIS_PORT=6379

# Get backend URL
export BACKEND_URL=$(gcloud run services describe bng-backend \
  --region=$REGION \
  --format='value(status.url)')

echo "Backend URL: $BACKEND_URL"
```

### 5. Deploy Worker

Option A: Cloud Run Jobs (for periodic processing)
```bash
gcloud run jobs create bng-worker \
  --image gcr.io/$PROJECT_ID/bng-worker:latest \
  --region $REGION \
  --max-retries 3 \
  --memory 2Gi \
  --cpu 2 \
  --set-env-vars REDIS_HOST=$REDIS_HOST,REDIS_PORT=6379
```

Option B: Cloud Run Service (for continuous processing)
```bash
gcloud run deploy bng-worker \
  --image gcr.io/$PROJECT_ID/bng-worker:latest \
  --platform managed \
  --region $REGION \
  --no-allow-unauthenticated \
  --min-instances 1 \
  --max-instances 5 \
  --memory 2Gi \
  --cpu 2 \
  --set-env-vars REDIS_HOST=$REDIS_HOST,REDIS_PORT=6379
```

### 6. Deploy Frontend

```bash
# Set up database URL (if using Cloud SQL)
export DATABASE_URL="postgresql://user:pass@host:port/db"

# Deploy frontend
gcloud run deploy bng-frontend \
  --image gcr.io/$PROJECT_ID/bng-frontend:latest \
  --platform managed \
  --region $REGION \
  --allow-unauthenticated \
  --min-instances 1 \
  --max-instances 5 \
  --memory 4Gi \
  --cpu 2 \
  --port 8501 \
  --set-env-vars BACKEND_URL=$BACKEND_URL

# Get frontend URL
gcloud run services describe bng-frontend \
  --region=$REGION \
  --format='value(status.url)'
```

### 7. Configure Secrets

For sensitive configuration (database passwords, API keys):

```bash
# Create secrets
echo -n "your-db-password" | gcloud secrets create db-password --data-file=-

# Grant access to Cloud Run service
gcloud secrets add-iam-policy-binding db-password \
  --member=serviceAccount:PROJECT_NUMBER-compute@developer.gserviceaccount.com \
  --role=roles/secretmanager.secretAccessor

# Update service to use secret
gcloud run services update bng-frontend \
  --update-secrets=DATABASE_PASSWORD=db-password:latest
```

## Cost Optimization

### Recommended Settings

**Backend**:
- Min instances: 1 (avoid cold starts)
- Max instances: 10 (control costs)
- Memory: 2Gi
- CPU: 2

**Frontend**:
- Min instances: 1 (always ready)
- Max instances: 5
- Memory: 4Gi (Streamlit needs more RAM)
- CPU: 2

**Worker**:
- Min instances: 1 (always processing)
- Max instances: 5 (scale with load)
- Memory: 2Gi
- CPU: 2

**Redis**:
- Size: 1GB (standard tier for HA)
- Version: 7.0

### Expected Costs (EUR/month)

- Cloud Run (Backend): ~€20-50
- Cloud Run (Frontend): ~€20-50
- Cloud Run (Worker): ~€20-50
- Memorystore Redis (1GB): ~€25
- **Total**: ~€85-175/month (depends on traffic)

## Monitoring

### View Logs

```bash
# Backend logs
gcloud run services logs read bng-backend --region=$REGION

# Frontend logs
gcloud run services logs read bng-frontend --region=$REGION

# Worker logs
gcloud run services logs read bng-worker --region=$REGION
```

### Metrics

Access Cloud Console for:
- Request counts
- Response times
- Error rates
- Resource utilization

## Troubleshooting

### Backend not connecting to Redis

1. Check VPC Connector is configured
2. Verify Redis instance is in same region
3. Check firewall rules allow Cloud Run → Redis

### Frontend can't reach Backend

1. Verify BACKEND_URL environment variable
2. Check backend allows unauthenticated access (or set up IAM)
3. Test backend health: `curl $BACKEND_URL/health`

### Worker not processing jobs

1. Check Redis connection
2. Verify RQ queue name matches
3. Check worker logs for errors

## Updates

To update a service:

```bash
# Build new image
make push-backend PROJECT_ID=$PROJECT_ID

# Deploy update (Cloud Run auto-deploys latest)
gcloud run services update bng-backend \
  --image gcr.io/$PROJECT_ID/bng-backend:latest
```

## Cleanup

```bash
# Delete services
gcloud run services delete bng-backend --region=$REGION
gcloud run services delete bng-frontend --region=$REGION
gcloud run services delete bng-worker --region=$REGION

# Delete Redis
gcloud redis instances delete bng-redis --region=$REGION

# Delete images
gcloud container images delete gcr.io/$PROJECT_ID/bng-backend:latest
gcloud container images delete gcr.io/$PROJECT_ID/bng-frontend:latest
gcloud container images delete gcr.io/$PROJECT_ID/bng-worker:latest
```
