# Cloud Run Deployment Guide

This guide explains how to deploy the BNG Optimiser to Google Cloud Run with Redis for job queueing and caching.

## Prerequisites

1. **Google Cloud Project**: Create or select a project
2. **gcloud CLI**: Install and authenticate
   ```bash
   gcloud auth login
   gcloud config set project YOUR_PROJECT_ID
   ```
3. **Enable Required APIs**:
   ```bash
   gcloud services enable run.googleapis.com
   gcloud services enable containerregistry.googleapis.com
   gcloud services enable redis.googleapis.com
   ```

## Architecture

The deployment consists of:
- **Frontend**: Streamlit app (Cloud Run)
- **Backend**: FastAPI service (Cloud Run)
- **Worker**: RQ worker (Cloud Run Jobs or Compute Engine)
- **Redis**: Memorystore for Redis (managed Redis)
- **PostgreSQL**: Cloud SQL or external database

## Step 1: Set Up Redis (Memorystore)

Create a Redis instance:

```bash
gcloud redis instances create bng-redis \
    --size=1 \
    --region=europe-west2 \
    --redis-version=redis_7_0 \
    --tier=basic
```

Get the Redis host:
```bash
REDIS_HOST=$(gcloud redis instances describe bng-redis --region=europe-west2 --format='get(host)')
echo "Redis host: $REDIS_HOST"
```

## Step 2: Set Up PostgreSQL (Cloud SQL)

Create a PostgreSQL instance:

```bash
gcloud sql instances create bng-db \
    --database-version=POSTGRES_15 \
    --tier=db-f1-micro \
    --region=europe-west2
```

Create database and user:
```bash
gcloud sql databases create optimiser --instance=bng-db
gcloud sql users create bnguser --instance=bng-db --password=YOUR_SECURE_PASSWORD
```

Get connection name:
```bash
CONNECTION_NAME=$(gcloud sql instances describe bng-db --format='get(connectionName)')
echo "Connection name: $CONNECTION_NAME"
```

## Step 3: Configure Environment Variables

Create a `.env` file:
```bash
PROJECT_ID=your-gcp-project-id
REGION=europe-west2
REDIS_HOST=<your-redis-host>
DATABASE_URL=postgresql://bnguser:password@/optimiser?host=/cloudsql/<connection-name>
```

## Step 4: Build and Push Images

Set your project ID:
```bash
export PROJECT_ID=your-gcp-project-id
```

Build and push all images:
```bash
make build-all PROJECT_ID=$PROJECT_ID
make push-all PROJECT_ID=$PROJECT_ID
```

Or manually:
```bash
# Backend
docker build -t gcr.io/$PROJECT_ID/bng-backend:latest -f docker/Dockerfile.backend .
docker push gcr.io/$PROJECT_ID/bng-backend:latest

# Frontend
docker build -t gcr.io/$PROJECT_ID/bng-frontend:latest -f docker/Dockerfile.frontend .
docker push gcr.io/$PROJECT_ID/bng-frontend:latest

# Worker
docker build -t gcr.io/$PROJECT_ID/bng-worker:latest -f docker/Dockerfile.worker .
docker push gcr.io/$PROJECT_ID/bng-worker:latest
```

## Step 5: Deploy Backend

Deploy the FastAPI backend:

```bash
gcloud run deploy bng-backend \
    --image=gcr.io/$PROJECT_ID/bng-backend:latest \
    --platform=managed \
    --region=europe-west2 \
    --allow-unauthenticated \
    --min-instances=1 \
    --max-instances=10 \
    --cpu=2 \
    --memory=4Gi \
    --port=8000 \
    --set-env-vars="REDIS_HOST=$REDIS_HOST,REDIS_PORT=6379,CACHE_TTL=43200" \
    --set-secrets="DATABASE_URL=bng-database-url:latest" \
    --vpc-connector=bng-connector \
    --vpc-egress=private-ranges-only
```

**Important flags explained**:
- `--min-instances=1`: Keeps at least one instance running to avoid cold starts
- `--cpu=2` and `--memory=4Gi`: Adequate resources for optimization tasks
- `--vpc-connector`: Required to access Redis Memorystore (must be created first)
- `--allow-unauthenticated`: Makes API public (adjust for production)

Get backend URL:
```bash
BACKEND_URL=$(gcloud run services describe bng-backend --region=europe-west2 --format='value(status.url)')
echo "Backend URL: $BACKEND_URL"
```

## Step 6: Deploy Workers

For Cloud Run Jobs (batch processing):

```bash
gcloud run jobs create bng-worker \
    --image=gcr.io/$PROJECT_ID/bng-worker:latest \
    --region=europe-west2 \
    --set-env-vars="REDIS_HOST=$REDIS_HOST,REDIS_PORT=6379" \
    --set-secrets="DATABASE_URL=bng-database-url:latest" \
    --vpc-connector=bng-connector \
    --vpc-egress=private-ranges-only \
    --cpu=2 \
    --memory=4Gi \
    --max-retries=3 \
    --parallelism=2
```

Or for continuous workers on Compute Engine (recommended for production):

```bash
# Create instance template
gcloud compute instance-templates create-with-container bng-worker-template \
    --machine-type=e2-standard-2 \
    --image-family=cos-stable \
    --image-project=cos-cloud \
    --container-image=gcr.io/$PROJECT_ID/bng-worker:latest \
    --container-env=REDIS_HOST=$REDIS_HOST,REDIS_PORT=6379 \
    --scopes=cloud-platform \
    --network=default

# Create managed instance group
gcloud compute instance-groups managed create bng-workers \
    --base-instance-name=bng-worker \
    --template=bng-worker-template \
    --size=2 \
    --region=europe-west2
```

## Step 7: Deploy Frontend

Deploy the Streamlit frontend:

```bash
gcloud run deploy bng-frontend \
    --image=gcr.io/$PROJECT_ID/bng-frontend:latest \
    --platform=managed \
    --region=europe-west2 \
    --allow-unauthenticated \
    --min-instances=1 \
    --max-instances=10 \
    --cpu=2 \
    --memory=4Gi \
    --port=8501 \
    --set-env-vars="BACKEND_URL=$BACKEND_URL" \
    --set-secrets="DATABASE_URL=bng-database-url:latest" \
    --vpc-connector=bng-connector \
    --vpc-egress=private-ranges-only
```

Get frontend URL:
```bash
FRONTEND_URL=$(gcloud run services describe bng-frontend --region=europe-west2 --format='value(status.url)')
echo "Frontend URL: $FRONTEND_URL"
```

## Step 8: Configure VPC Connector (Required for Redis)

Create a VPC connector to allow Cloud Run to access Redis:

```bash
gcloud compute networks vpc-access connectors create bng-connector \
    --region=europe-west2 \
    --range=10.8.0.0/28 \
    --network=default
```

## Step 9: Set Up Secrets

Create secrets for sensitive data:

```bash
# Database URL
echo -n "postgresql://user:pass@host/db" | \
    gcloud secrets create bng-database-url --data-file=-

# Grant access to Cloud Run
gcloud secrets add-iam-policy-binding bng-database-url \
    --member=serviceAccount:PROJECT_NUMBER-compute@developer.gserviceaccount.com \
    --role=roles/secretmanager.secretAccessor
```

## Monitoring and Logging

View logs:
```bash
# Backend logs
gcloud run services logs read bng-backend --region=europe-west2

# Frontend logs
gcloud run services logs read bng-frontend --region=europe-west2
```

Check service health:
```bash
curl $BACKEND_URL/health
```

## Scaling Configuration

### Auto-scaling

Cloud Run automatically scales based on:
- CPU utilization
- Request concurrency
- Custom metrics

Configure scaling:
```bash
gcloud run services update bng-backend \
    --min-instances=1 \
    --max-instances=20 \
    --concurrency=80 \
    --cpu-throttling
```

### Cost Optimization

For development/low-traffic:
- Use `--min-instances=0` (but accept cold starts)
- Use smaller instance types (`--cpu=1 --memory=2Gi`)
- Use `db-f1-micro` for database

For production:
- Use `--min-instances=1` or higher to avoid cold starts
- Use `--cpu=2 --memory=4Gi` for reliable performance
- Consider `db-custom` database tiers

## Updating Services

Deploy new versions:
```bash
# Build and push new images
make push-all PROJECT_ID=$PROJECT_ID

# Deploy updates (automatically routes traffic)
make deploy-all PROJECT_ID=$PROJECT_ID
```

Rollback:
```bash
gcloud run services update-traffic bng-backend \
    --to-revisions=PREVIOUS_REVISION=100
```

## Custom Domain

Map custom domain:
```bash
gcloud run domain-mappings create \
    --service=bng-frontend \
    --domain=app.yourdomain.com \
    --region=europe-west2
```

## Troubleshooting

### Service not accessible
- Check IAM permissions: `--allow-unauthenticated` or configure authentication
- Verify VPC connector is created and attached
- Check Redis connectivity from VPC

### High latency
- Increase `--min-instances` to reduce cold starts
- Increase CPU and memory allocations
- Check Redis connection pooling

### Worker not processing jobs
- Verify Redis connection (check VPC connector)
- Check worker logs in Compute Engine or Cloud Run Jobs
- Ensure workers are running (instance group or job execution)

## Cost Estimates

Approximate monthly costs (us-central1):

**Development**:
- Redis Basic (1GB): ~$35/month
- Cloud SQL db-f1-micro: ~$8/month
- Cloud Run (minimal traffic): ~$10/month
- **Total**: ~$53/month

**Production**:
- Redis Standard (5GB HA): ~$285/month
- Cloud SQL db-custom-2-4096: ~$135/month
- Cloud Run (moderate traffic): ~$100/month
- Compute Engine workers (2x e2-standard-2): ~$70/month
- **Total**: ~$590/month

## Security Best Practices

1. **Never use `--allow-unauthenticated` in production** - configure IAM authentication
2. **Use Secret Manager** for sensitive data
3. **Enable VPC Service Controls** for data protection
4. **Set up Cloud Armor** for DDoS protection
5. **Enable audit logging** for compliance
6. **Use least-privilege service accounts**
7. **Regularly update base images** for security patches

## Support

For issues with deployment:
1. Check Cloud Run logs: `gcloud run services logs read SERVICE_NAME`
2. Verify environment variables are set correctly
3. Test locally first with `docker-compose`
4. Check Redis connectivity with VPC connector
