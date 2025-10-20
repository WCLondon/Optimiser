# Attio App Migration - Quick Start Guide

This guide will help you get the BNG Optimiser Attio App up and running quickly.

## Prerequisites

- Docker and Docker Compose installed
- Attio developer account
- Attio API key
- Basic familiarity with command line

## Quick Start (5 minutes)

### 1. Clone and Configure

```bash
# Navigate to the project directory
cd /path/to/Optimiser

# Copy environment template
cp .env.example .env

# Edit .env and add your Attio API key
nano .env  # or use your preferred editor
```

Required changes in `.env`:
- Set `ATTIO_API_KEY` to your actual Attio API key
- Update `POSTGRES_PASSWORD` and `PGADMIN_PASSWORD` to secure values

### 2. Start Services

```bash
# Start all services with Docker Compose
docker-compose up -d

# Check that services are running
docker-compose ps
```

You should see:
- `backend` - Running on port 8080
- `db` - PostgreSQL on port 5432
- `redis` - Redis on port 6379
- `pgadmin` - (Optional) on port 5050

### 3. Verify Backend

```bash
# Test the backend health endpoint
curl http://localhost:8080/health

# Should return: {"status":"healthy","timestamp":"..."}
```

### 4. Install Frontend (Attio App)

```bash
# Navigate to frontend directory
cd frontend

# Install dependencies
npm install

# Configure the app for your Attio workspace
# Edit attio.json if needed

# Deploy to Attio (requires Attio CLI)
npm run deploy
```

### 5. Configure in Attio

1. **Log in to Attio**
2. **Go to Apps section**
3. **Find "BNG Optimiser" app**
4. **Install the app** in your workspace
5. **Configure widget settings**:
   - Backend URL: `http://your-server:8080` (or your deployed URL)
   - Enable iframe mode: `false` (use native SDK)

### 6. Add Widget to a Record

1. Open any record page in Attio (e.g., a Company or Project)
2. Click "Add widget"
3. Select "Run BNG Quote"
4. The widget should appear on the page

### 7. Test the Widget

1. **Enter demand**: Select a habitat and enter units
2. **Set location**: Enter a postcode (e.g., "SW1A 1AA")
3. **Run quote**: Click "Run Quote"
4. **View results**: Wait for optimization to complete
5. **Save to Attio**: Click "Save to Attio" to persist results

## Development Mode

For local development without Docker:

### Backend

```bash
cd backend

# Install dependencies
pip install -r requirements.txt

# Create .env file
cp .env.example .env
# Edit .env with your settings

# Run server
uvicorn main:app --reload --port 8080
```

### Frontend

```bash
cd frontend

# Install dependencies
npm install

# Run in development mode
npm run dev
```

## Troubleshooting

### Backend won't start

```bash
# Check logs
docker-compose logs backend

# Common issues:
# - Port 8080 already in use: Change port in docker-compose.yml
# - Missing .env file: Copy from .env.example
# - Invalid API key: Check ATTIO_API_KEY in .env
```

### Frontend won't deploy

```bash
# Ensure you have Attio CLI installed
npm install -g @attio/cli

# Login to Attio
attio login

# Deploy
attio deploy
```

### Widget shows CORS error

Check that:
1. Backend CORS is configured (it should be by default)
2. Backend URL in widget settings is correct
3. Backend is accessible from browser

### Database connection issues

```bash
# Check if PostgreSQL is running
docker-compose ps db

# Check database logs
docker-compose logs db

# Connect to database manually
docker-compose exec db psql -U optimiser -d optimiser_db
```

## Next Steps

1. **Load Backend Data**: Add your Excel backend files to the `data/` directory
2. **Customize Mapping**: Edit `map_quote_to_attio_record()` in `backend/main.py`
3. **Create Custom Objects**: Set up Quote objects in Attio if needed
4. **Add Tests**: Create tests for your specific use cases
5. **Deploy to Production**: Set up proper hosting (e.g., AWS, GCP, Heroku)

## Production Deployment

For production, you'll want to:

1. **Use a proper hosting service**:
   - Backend: AWS ECS, Google Cloud Run, Heroku, etc.
   - Database: AWS RDS, Google Cloud SQL, etc.

2. **Set up environment variables** on your hosting platform

3. **Update frontend settings** with production backend URL

4. **Enable HTTPS** for backend API

5. **Set up monitoring and logging**

6. **Configure database backups**

## Support

- Full documentation: See [ATTIO_APP_README.md](./ATTIO_APP_README.md)
- Attio SDK docs: https://docs.attio.com
- Issues: [GitHub repository]

## Summary

You've now:
- ✅ Set up the backend API
- ✅ Deployed the Attio App frontend
- ✅ Configured the widget
- ✅ Tested the complete workflow

The BNG Optimiser is now available as an Attio App!
