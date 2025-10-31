# Shiny for Python Deployment Guide

## Overview

This guide explains how to deploy your Shiny for Python BNG Optimiser application so your team can access it online. Since you've set up the app in Positron (a local development environment), you'll need to deploy it to a hosting service.

## Deployment Options for Shiny for Python

### Option 1: Posit Connect (Recommended for Shiny)

**Best for:** Organizations already using Posit products, native Shiny hosting

Posit Connect is the native platform for Shiny applications with built-in support for:
- One-click publishing from Positron/RStudio
- Automatic scaling
- User authentication
- Scheduled updates
- Easy environment management

#### Steps:

1. **Sign up for Posit Connect:**
   - Cloud: https://posit.co/products/cloud/connect/
   - Self-hosted: https://posit.co/products/enterprise/connect/

2. **Install rsconnect-python:**
   ```bash
   pip install rsconnect-python
   ```

3. **Configure connection:**
   ```bash
   rsconnect add \
     --account <your-account> \
     --name posit-connect \
     --server https://connect.posit.cloud \
     --api-key <your-api-key>
   ```

4. **Deploy from Positron/command line:**
   ```bash
   rsconnect deploy shiny \
     --name bng-optimiser \
     --title "BNG Optimiser" \
     .
   ```

5. **Share with team:**
   - Get the URL from Posit Connect dashboard
   - Configure access permissions (public, authenticated users, specific groups)
   - Share the URL with your team

**Pricing:**
- Starter: $4,995/year (5 concurrent users)
- Standard: $14,995/year (20 concurrent users)
- Professional: $24,995/year (unlimited users)

**Pros:**
- Native Shiny support
- Easy deployment from Positron
- Excellent for Python/R teams
- Built-in authentication

**Cons:**
- Higher cost for small teams
- Requires paid subscription

---

### Option 2: Heroku (Good for Quick Setup)

**Best for:** Quick prototypes, small teams, low cost

#### Prerequisites:
1. Heroku account (https://heroku.com)
2. Heroku CLI installed

#### Files needed:

**1. Create `Procfile`:**
```bash
web: shiny run --host 0.0.0.0 --port $PORT app.py
```

**2. Create `runtime.txt`:**
```txt
python-3.11.6
```

**3. Ensure `requirements.txt` is complete:**
```txt
shiny>=0.7
shinywidgets>=0.3
pandas>=2.1
numpy>=1.24
plotly>=5.14
folium>=0.16
requests>=2.31
sqlalchemy>=2.0
psycopg[binary]>=3.1
tenacity>=8.0
openpyxl>=3.1
pyxlsb>=1.0
gunicorn>=21.0
```

#### Deployment Steps:

```bash
# 1. Login to Heroku
heroku login

# 2. Create Heroku app
heroku create bng-optimiser

# 3. Add PostgreSQL (if needed)
heroku addons:create heroku-postgresql:mini

# 4. Set environment variables
heroku config:set DATABASE_URL="your-database-url"
heroku config:set AUTH_USERNAME="WC0323"
heroku config:set AUTH_PASSWORD="Wimborne"

# 5. Deploy
git push heroku feature/shiny-migration:main

# 6. Open app
heroku open
```

**Share with team:**
```
Your app will be at: https://bng-optimiser.herokuapp.com
```

**Pricing:**
- Hobby: $7/month (basic, sleeps after 30min inactivity)
- Basic: $25-50/month (no sleep)
- Standard: $250/month (performance dynos)

**Pros:**
- Quick setup
- Free tier available
- Easy Git-based deployment

**Cons:**
- Apps sleep on free tier
- Limited to 512MB RAM on basic tiers
- Less Shiny-specific support

---

### Option 3: Docker + Cloud Run (Scalable, Cost-Effective)

**Best for:** Production deployments, teams with DevOps resources

#### 1. Create `Dockerfile`:

```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY . .

# Expose port
EXPOSE 8080

# Run app
CMD ["shiny", "run", "--host", "0.0.0.0", "--port", "8080", "app.py"]
```

#### 2. Build and test locally:

```bash
# Build image
docker build -t bng-optimiser .

# Test locally
docker run -p 8080:8080 \
  -e DATABASE_URL="your-db-url" \
  bng-optimiser

# Access at http://localhost:8080
```

#### 3. Deploy to Google Cloud Run:

```bash
# Set project
gcloud config set project YOUR_PROJECT_ID

# Build and push to Container Registry
gcloud builds submit --tag gcr.io/YOUR_PROJECT_ID/bng-optimiser

# Deploy to Cloud Run
gcloud run deploy bng-optimiser \
  --image gcr.io/YOUR_PROJECT_ID/bng-optimiser \
  --platform managed \
  --region europe-west2 \
  --allow-unauthenticated \
  --port 8080 \
  --memory 2Gi \
  --cpu 2 \
  --min-instances 1 \
  --max-instances 10 \
  --set-env-vars DATABASE_URL="your-db-url"

# Get URL
gcloud run services describe bng-optimiser --region europe-west2 --format='value(status.url)'
```

**Share with team:**
```
Your app will be at: https://bng-optimiser-xxxxx-ew.a.run.app
```

**Pricing:**
- Pay per use
- ~$15-50/month for moderate usage
- Free tier: 2 million requests/month

**Pros:**
- Scales to zero (no cost when idle)
- Automatic scaling
- Pay per use
- Production-ready

**Cons:**
- Requires Docker knowledge
- More complex setup
- Cold starts (mitigated with min-instances)

---

### Option 4: Fly.io (Modern, Developer-Friendly)

**Best for:** Modern deployments, global edge distribution

#### 1. Install Fly.io CLI:
```bash
curl -L https://fly.io/install.sh | sh
```

#### 2. Create `fly.toml`:

```toml
app = "bng-optimiser"
primary_region = "lhr"

[build]
  dockerfile = "Dockerfile"

[env]
  PORT = "8080"

[http_service]
  internal_port = 8080
  force_https = true
  auto_stop_machines = true
  auto_start_machines = true
  min_machines_running = 1

[[vm]]
  cpu_kind = "shared"
  cpus = 2
  memory_gb = 2
```

#### 3. Deploy:

```bash
# Login
fly auth login

# Launch app
fly launch

# Set secrets
fly secrets set DATABASE_URL="your-db-url"

# Deploy
fly deploy

# Open app
fly open
```

**Share with team:**
```
Your app will be at: https://bng-optimiser.fly.dev
```

**Pricing:**
- Free tier: 3 shared VMs
- Production: ~$10-30/month
- Scale to multiple regions easily

**Pros:**
- Very fast deployment
- Global edge network
- Good free tier
- Developer-friendly

**Cons:**
- Newer platform
- Less enterprise features than Cloud Run

---

## Comparison Table

| Platform | Setup Time | Monthly Cost | Best For | Scaling |
|----------|------------|--------------|----------|---------|
| **Posit Connect** | 30 min | $400-2000 | Enterprise Shiny | Excellent |
| **Heroku** | 15 min | $7-250 | Quick prototypes | Good |
| **Cloud Run** | 1 hour | $15-100 | Production | Excellent |
| **Fly.io** | 30 min | $0-50 | Modern apps | Excellent |

## Recommendations by Use Case

### For Your Team (BNG Optimiser)

**If you have budget ($400+/year):**
→ **Posit Connect** - Native Shiny support, easiest deployment from Positron

**If you want quick & cheap ($7-25/month):**
→ **Heroku** - Deploy in 15 minutes, share URL immediately

**If you want scalable & cost-effective:**
→ **Google Cloud Run** - Production-ready, scales automatically

**If you want modern & global:**
→ **Fly.io** - Fast, global edge, developer-friendly

## Database Hosting

Your app needs PostgreSQL. Options:

1. **Heroku Postgres** ($9/month) - Easiest with Heroku
2. **Google Cloud SQL** ($7/month) - Good with Cloud Run
3. **Fly.io Postgres** ($2/month) - Included with Fly.io
4. **Supabase** (Free tier) - PostgreSQL with admin UI
5. **ElephantSQL** (Free tier) - Managed PostgreSQL

## Security Considerations

Before sharing with team:

1. **Authentication:**
   - Current: Basic username/password in code
   - Production: Use OAuth, SAML, or platform auth (Posit Connect has this built-in)

2. **Environment Variables:**
   - Never commit `.env` or secrets
   - Use platform secrets (Heroku Config Vars, Cloud Run Secrets, etc.)

3. **Database:**
   - Use strong passwords
   - Enable SSL connections
   - Restrict access by IP if possible

4. **HTTPS:**
   - All platforms provide free SSL certificates
   - Always use HTTPS in production

## Quick Start: Deploy to Heroku in 15 Minutes

The fastest way to get your team access:

```bash
# 1. Install Heroku CLI (if not installed)
curl https://cli-assets.heroku.com/install.sh | sh

# 2. Login
heroku login

# 3. Create Procfile
echo "web: shiny run --host 0.0.0.0 --port \$PORT app.py" > Procfile

# 4. Create runtime.txt
echo "python-3.11.6" > runtime.txt

# 5. Create Heroku app
heroku create bng-optimiser

# 6. Add PostgreSQL (if needed)
heroku addons:create heroku-postgresql:mini

# 7. Set environment variables
heroku config:set AUTH_USERNAME="WC0323"
heroku config:set AUTH_PASSWORD="Wimborne"

# 8. Deploy
git add Procfile runtime.txt
git commit -m "Add Heroku deployment files"
git push heroku feature/shiny-migration:main

# 9. Open app
heroku open

# 10. Share URL with team
heroku info -s | grep web_url
```

That's it! Your team can now access the app at the provided URL.

## Monitoring and Maintenance

### View logs:
```bash
# Heroku
heroku logs --tail

# Cloud Run
gcloud run services logs read bng-optimiser --region europe-west2

# Fly.io
fly logs
```

### Scale resources:
```bash
# Heroku
heroku ps:scale web=2  # Scale to 2 dynos

# Cloud Run
gcloud run services update bng-optimiser --memory 4Gi

# Fly.io
fly scale count 3  # Scale to 3 machines
```

## Getting Help

- **Posit Connect:** https://support.posit.co
- **Heroku:** https://devcenter.heroku.com
- **Cloud Run:** https://cloud.google.com/run/docs
- **Fly.io:** https://fly.io/docs

## Next Steps

1. Choose a platform based on your needs and budget
2. Follow the deployment steps for your chosen platform
3. Test the deployed app thoroughly
4. Share the URL with your team
5. Set up monitoring and backups
6. Plan for scaling as usage grows

## Notes for Shiny Migration

Since your app is only ~30% migrated to Shiny:
- The current scaffold will deploy but has limited functionality
- Consider completing the migration before production deployment
- For quick team previews, Heroku or Fly.io are good choices
- For production, wait until migration is complete and use Posit Connect or Cloud Run
