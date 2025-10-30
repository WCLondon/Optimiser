# Step-by-Step Implementation Guide

This guide will walk you through implementing the new architecture for the BNG Optimiser. No prior experience with Docker, FastAPI, or Redis required!

## 📋 Prerequisites

Before you begin, make sure you have:

1. **Python 3.11+** installed
   - Check: `python --version`
   - Download from: https://www.python.org/downloads/

2. **Docker Desktop** installed
   - Check: `docker --version`
   - Download from: https://www.docker.com/products/docker-desktop/

3. **Git** installed (you likely already have this)
   - Check: `git --version`

## 🎯 Quick Start (Easiest Option)

If you just want to see it working locally, follow these 3 steps:

### Step 1: Start the Services

Open a terminal in the project directory and run:

```bash
make local-up
```

This single command will:
- Start Redis (job queue and cache)
- Start the FastAPI backend (API server)
- Start 2 worker processes (for background jobs)
- Start the Streamlit frontend (web UI)

**Wait for the message**: "Services starting..."

### Step 2: Access the Application

Open your web browser and go to:

- **Frontend (Streamlit)**: http://localhost:8501
- **Backend API**: http://localhost:8000
- **API Documentation**: http://localhost:8000/docs

### Step 3: Test It Works

1. Use the Streamlit app as normal
2. Click "Optimize" 
3. The app should stay responsive (not freeze)
4. Results appear when processing completes

To stop everything:

```bash
make local-down
```

---

## 🔧 Detailed Setup (If Quick Start Doesn't Work)

### Option A: Docker Compose (Recommended)

#### Step 1: Verify Docker is Running

```bash
docker ps
```

If you get an error, start Docker Desktop application first.

#### Step 2: Check Files Exist

Make sure these files are in your project:

```bash
ls docker-compose.yml
ls backend/app.py
ls backend/worker.py
```

All should show the files exist.

#### Step 3: Build the Docker Images

```bash
docker-compose build
```

This will take 5-10 minutes the first time. It's downloading and installing all dependencies.

#### Step 4: Start the Services

```bash
docker-compose up -d
```

The `-d` flag runs it in the background.

#### Step 5: Check Everything Started

```bash
docker-compose ps
```

You should see 4 services running:
- `redis`
- `backend`
- `worker` (2 instances)
- `frontend`

#### Step 6: View Logs (if something isn't working)

```bash
# All services
docker-compose logs

# Specific service
docker-compose logs backend
docker-compose logs frontend
docker-compose logs worker
```

#### Step 7: Stop Services When Done

```bash
docker-compose down
```

---

### Option B: Manual Setup (Without Docker)

If you prefer not to use Docker, you can run each component manually:

#### Step 1: Install Redis

**On macOS:**
```bash
brew install redis
brew services start redis
```

**On Ubuntu/Debian:**
```bash
sudo apt-get install redis-server
sudo systemctl start redis
```

**On Windows:**
- Download from: https://redis.io/download
- Or use Docker just for Redis: `docker run -d -p 6379:6379 redis:7-alpine`

#### Step 2: Install Python Dependencies

Backend dependencies:
```bash
pip install -r backend/requirements.txt
```

Frontend dependencies (if different):
```bash
pip install -r requirements.txt
```

#### Step 3: Set Environment Variables

**On macOS/Linux:**
```bash
export REDIS_HOST=localhost
export REDIS_PORT=6379
export DATABASE_URL=your_database_url_here
```

**On Windows (PowerShell):**
```powershell
$env:REDIS_HOST="localhost"
$env:REDIS_PORT="6379"
$env:DATABASE_URL="your_database_url_here"
```

#### Step 4: Start Backend (in one terminal)

```bash
cd backend
uvicorn app:app --reload --host 0.0.0.0 --port 8000
```

Keep this terminal open.

#### Step 5: Start Worker (in another terminal)

```bash
python backend/worker.py
```

Keep this terminal open too.

#### Step 6: Start Frontend (in a third terminal)

```bash
export BACKEND_URL=http://localhost:8000
streamlit run app.py
```

Now you should have:
- Backend API at http://localhost:8000
- Frontend at http://localhost:8501

---

## 🧪 Testing the Setup

### Test 1: Backend Health Check

Open a browser or use curl:

```bash
curl http://localhost:8000/health
```

Expected output:
```json
{
  "status": "ok",
  "redis": "connected",
  "timestamp": "2025-10-30T10:00:00"
}
```

### Test 2: Backend API Documentation

Visit http://localhost:8000/docs

You should see interactive API documentation.

### Test 3: Create a Test Job

```bash
curl -X POST http://localhost:8000/jobs \
  -H "Content-Type: application/json" \
  -d '{"demand_df": {}, "target_lpa": "Test"}'
```

You should get back a job ID or cached result.

### Test 4: Frontend Works

1. Go to http://localhost:8501
2. The app should load normally
3. Try entering some data and clicking "Optimize"
4. The UI should not freeze

---

## 🐛 Troubleshooting

### Problem: "Cannot connect to Redis"

**Solution:**
1. Check Redis is running: `redis-cli ping`
2. Should respond with `PONG`
3. If not, start Redis (see Step 1 in Manual Setup)

### Problem: "Port already in use"

**Solution:**
Find what's using the port:

```bash
# Check port 8000
lsof -i :8000

# Check port 8501
lsof -i :8501
```

Kill the process or change the port in the configuration.

### Problem: Docker build fails

**Solution:**
1. Make sure Docker Desktop is running
2. Try cleaning up: `docker system prune -a`
3. Rebuild: `docker-compose build --no-cache`

### Problem: Backend starts but worker doesn't process jobs

**Solution:**
1. Check worker logs: `docker-compose logs worker`
2. Check Redis connection: `docker-compose exec redis redis-cli ping`
3. Restart workers: `docker-compose restart worker`

### Problem: Frontend can't reach backend

**Solution:**
1. Check backend is running: `curl http://localhost:8000/health`
2. If using Docker Compose, backend URL should be `http://backend:8000`
3. If running manually, backend URL should be `http://localhost:8000`

---

## 📚 Understanding the Architecture

### What Each Component Does

1. **Redis** (Port 6379)
   - Stores job queue
   - Caches results for 12 hours
   - Persists data across restarts

2. **Backend** (Port 8000)
   - Receives optimization requests
   - Checks cache first
   - Creates jobs if not cached
   - Returns job status and results

3. **Workers** (No port, background only)
   - Pull jobs from Redis queue
   - Run optimization calculations
   - Store results back to cache
   - Can scale horizontally (add more workers)

4. **Frontend** (Port 8501)
   - Streamlit web interface
   - Submits jobs to backend
   - Polls for job completion
   - Displays results

### How Data Flows

```
1. User enters data → Frontend
2. Frontend submits → Backend API
3. Backend checks cache → Redis
4. If not cached → Create job → Redis Queue
5. Worker picks up job → Redis Queue
6. Worker processes → Optimization
7. Worker stores result → Redis Cache
8. Frontend polls backend → Gets result
9. Frontend displays result
```

---

## 🚀 Deploying to Production

### Option 1: Cloud Run (Google Cloud)

See detailed guide: [cloudrun.md](cloudrun.md)

Quick version:
```bash
export PROJECT_ID=your-gcp-project-id
make deploy-all PROJECT_ID=$PROJECT_ID
```

### Option 2: Fly.io (Cheaper Alternative)

See detailed guide: [flyio.md](flyio.md)

Quick version:
```bash
flyctl deploy --config fly.backend.toml
flyctl deploy --config fly.frontend.toml
```

---

## 🔄 Going Back to Original (Standalone Mode)

If you want to use the app without the backend:

```bash
# Just run Streamlit directly
streamlit run app.py
```

No backend needed! The app will work in standalone mode.

---

## 💡 Next Steps

1. **Read the Architecture Guide**: [ARCHITECTURE.md](ARCHITECTURE.md)
   - Understand how everything fits together

2. **Try the Quick Start Guide**: [QUICKSTART.md](QUICKSTART.md)
   - More detailed local development setup

3. **Explore the API**: http://localhost:8000/docs
   - Interactive API documentation
   - Try creating jobs and checking status

4. **Monitor Performance**:
   ```bash
   # Check Redis cache
   docker-compose exec redis redis-cli
   > KEYS cache:*
   
   # Check job queue
   > LLEN rq:queue:jobs
   ```

5. **Scale Workers** (if needed):
   ```bash
   docker-compose scale worker=4
   ```

---

## 📞 Getting Help

If you get stuck:

1. Check logs:
   ```bash
   make local-logs
   ```

2. Run validation tests:
   ```bash
   python test_backend_validation.py
   ```

3. Review troubleshooting section above

4. Check the comprehensive guides:
   - [ARCHITECTURE.md](ARCHITECTURE.md) - How it works
   - [QUICKSTART.md](QUICKSTART.md) - Detailed setup
   - [REFACTORING_SUMMARY.md](REFACTORING_SUMMARY.md) - What changed

---

## ✅ Checklist

Use this to verify your setup:

- [ ] Docker Desktop installed and running
- [ ] Python 3.11+ installed
- [ ] Can run `make local-up` successfully
- [ ] Can access http://localhost:8501
- [ ] Can access http://localhost:8000/health
- [ ] Backend health check returns "ok"
- [ ] Frontend loads without errors
- [ ] Can submit an optimization job
- [ ] UI stays responsive during optimization
- [ ] Results appear after processing

If all checked, you're ready to go! 🎉

---

## 🎓 Learning Resources

Want to understand the technologies better?

- **FastAPI**: https://fastapi.tiangolo.com/tutorial/
- **Redis**: https://redis.io/docs/getting-started/
- **RQ (Redis Queue)**: https://python-rq.org/docs/
- **Docker**: https://docs.docker.com/get-started/
- **Streamlit**: https://docs.streamlit.io/

Each has excellent beginner-friendly tutorials!
