# Visual Guide: How the New Architecture Works

This guide uses simple diagrams to explain how the refactored system works.

## 🏗️ Before vs After

### Before (Monolithic)

```
┌─────────────────────────────────────┐
│                                     │
│         User Browser                │
│                                     │
└──────────────┬──────────────────────┘
               │
               │ Opens page, types input
               ▼
┌─────────────────────────────────────┐
│                                     │
│      Streamlit Application          │
│                                     │
│  ┌───────────────────────────────┐  │
│  │  1. User types in input       │  │
│  │  2. App reruns immediately ❌ │  │
│  │  3. UI freezes                │  │
│  │  4. Optimization runs         │  │
│  │  5. UI unfreezes              │  │
│  └───────────────────────────────┘  │
│                                     │
└──────────────┬──────────────────────┘
               │
               ▼
┌─────────────────────────────────────┐
│       PostgreSQL Database           │
└─────────────────────────────────────┘
```

**Problems:**
- ❌ UI freezes during optimization
- ❌ Every keystroke triggers a rerun
- ❌ No caching of results
- ❌ Can't scale horizontally
- ❌ One user's heavy job blocks everyone

---

### After (Microservices)

```
┌──────────────────────────────────────────────────────────┐
│                     User Browser                          │
└────────────────────────┬─────────────────────────────────┘
                         │
                         │ Submits form
                         ▼
┌──────────────────────────────────────────────────────────┐
│              Streamlit Frontend                           │
│              (Port 8501)                                  │
│                                                           │
│  ✅ Form-based input (no rerun on typing)                │
│  ✅ Submit button triggers action                        │
│  ✅ UI stays responsive                                  │
│  ✅ Polls for job status                                 │
└────────────────────────┬─────────────────────────────────┘
                         │
                         │ POST /jobs
                         ▼
┌──────────────────────────────────────────────────────────┐
│              FastAPI Backend                              │
│              (Port 8000)                                  │
│                                                           │
│  1. Receive job request                                   │
│  2. Hash inputs (deterministic)                          │
│  3. Check Redis cache first                              │
│  4. If cached: return immediately ⚡                     │
│  5. If not: create job in queue                          │
└─────────┬──────────────────────┬─────────────────────────┘
          │                      │
          │ Enqueue              │ Check/Store
          ▼                      ▼
┌─────────────────┐    ┌──────────────────────────┐
│  Redis Queue    │    │     Redis Cache          │
│                 │    │                          │
│  Job 1: pending │    │  cache:abc123 → result   │
│  Job 2: running │    │  cache:def456 → result   │
│  Job 3: pending │    │  (12 hour TTL)           │
└────────┬────────┘    └──────────────────────────┘
         │
         │ Workers pull jobs
         ▼
┌──────────────────────────────────────────────────────────┐
│                    RQ Workers                             │
│                    (2-4 instances)                        │
│                                                           │
│  Worker 1: Processing Job 2 🔄                           │
│  Worker 2: Waiting for jobs 💤                           │
│                                                           │
│  ✅ Run in background                                    │
│  ✅ Can scale horizontally                               │
│  ✅ Isolate heavy computation                            │
└────────────────────────┬─────────────────────────────────┘
                         │
                         │ Query data
                         ▼
┌──────────────────────────────────────────────────────────┐
│              PostgreSQL Database                          │
│                                                           │
│  • Reference tables (Banks, Pricing, etc.)               │
│  • Submission history                                     │
└──────────────────────────────────────────────────────────┘
```

**Benefits:**
- ✅ UI never freezes
- ✅ No rerun on typing (form-based)
- ✅ Results cached for 12 hours
- ✅ Horizontal scaling (add more workers)
- ✅ Multiple users work simultaneously

---

## 🔄 Job Lifecycle

### Scenario 1: Cache Hit (Instant Result)

```
User submits job with params: {lpa: "Winchester", demand: 10}
                    │
                    ▼
         Frontend → Backend
                    │
                    ▼
         Hash params → "abc123"
                    │
                    ▼
         Check Redis: cache:abc123
                    │
                    ▼
              ✅ FOUND!
                    │
                    ▼
         Return cached result
         (Response time: <50ms)
```

### Scenario 2: Cache Miss (New Job)

```
User submits job with params: {lpa: "Bristol", demand: 15}
                    │
                    ▼
         Frontend → Backend
                    │
                    ▼
         Hash params → "def456"
                    │
                    ▼
         Check Redis: cache:def456
                    │
                    ▼
              ❌ NOT FOUND
                    │
                    ▼
         Create job in queue
                    │
                    ▼
         Return job_id: "xyz789"
                    │
                    ▼
         Frontend starts polling
         GET /jobs/xyz789 every 1 second
                    │
         ┌──────────┴──────────┐
         │                     │
         ▼                     ▼
    status: queued       status: started
         │                     │
         │                     ▼
         │              Worker processing...
         │                     │
         │                     ▼
         │              Store result in cache
         │                     │
         └─────────────────────┘
                    │
                    ▼
              status: finished
                    │
                    ▼
         Return result to frontend
         (Response time: 5-30 seconds)
```

---

## 📊 Request Flow Diagram

### Without Backend (Standalone Mode)

```
┌─────────┐
│  User   │
└────┬────┘
     │ Enter data
     ▼
┌─────────────────┐
│   Streamlit     │ ◄─── Optimization runs here
│                 │      (UI freezes)
│   app.py        │
└────┬────────────┘
     │
     ▼
┌─────────────────┐
│   PostgreSQL    │
└─────────────────┘

Timeline:
0s  ────► User clicks Optimize
0s  ────► UI freezes ❄️
5s  ────► Still processing...
10s ────► Still processing...
15s ────► Done! UI unfreezes ✅
```

### With Backend (New Mode)

```
┌─────────┐
│  User   │
└────┬────┘
     │ Enter data
     ▼
┌─────────────────┐
│   Streamlit     │ ◄─── Just UI and polling
│   (Frontend)    │      (Never freezes!)
└────┬────────────┘
     │ HTTP API
     ▼
┌─────────────────┐
│    FastAPI      │ ◄─── Job management
│   (Backend)     │      (Checks cache, queues jobs)
└────┬────────────┘
     │
     ▼
┌─────────────────┐
│     Redis       │ ◄─── Queue + Cache
└────┬────────────┘
     │
     ▼
┌─────────────────┐
│   RQ Workers    │ ◄─── Actual optimization
│   (2+ workers)  │      (Heavy lifting)
└────┬────────────┘
     │
     ▼
┌─────────────────┐
│   PostgreSQL    │
└─────────────────┘

Timeline:
0s  ────► User clicks Optimize
0s  ────► Request sent to backend ⚡
0.1s───► Job queued (UI still responsive ✅)
1s ────► User can continue using UI 🎉
2s ────► Worker starts processing
...     ► User sees "Processing..." spinner
15s ───► Job complete, result displayed ✅
```

---

## 🎯 Caching Strategy

### How Caching Works

```
┌─────────────────────────────────────────────────────┐
│              Input Parameters                        │
│  {                                                   │
│    "demand_df": {...},                              │
│    "target_lpa": "Winchester",                      │
│    "target_nca": "South Downs"                      │
│  }                                                   │
└────────────────────┬────────────────────────────────┘
                     │
                     ▼
         ┌───────────────────────┐
         │  JSON.stringify()     │
         │  (sorted keys)        │
         └───────────┬───────────┘
                     │
                     ▼
         "{"demand_df":{...},"target_lpa":"Winchester",...}"
                     │
                     ▼
         ┌───────────────────────┐
         │   SHA256 Hash         │
         └───────────┬───────────┘
                     │
                     ▼
         "a3f5b9c2e8d1..."
                     │
                     ▼
         ┌───────────────────────┐
         │ Redis Key             │
         │ "cache:a3f5b9c2e8d1" │
         └───────────────────────┘

Result stored for 12 hours (43200 seconds)
```

### Cache Hit Scenarios

```
Request 1 (New):
User A → {lpa: "Winchester"} → hash: abc123
         Check Redis → NOT FOUND ❌
         Create job → Process → Store in cache
         Response time: 15 seconds

Request 2 (Same params, User B):
User B → {lpa: "Winchester"} → hash: abc123
         Check Redis → FOUND! ✅
         Return cached result
         Response time: 50 milliseconds (300x faster!)

Request 3 (Different params):
User C → {lpa: "Bristol"} → hash: def456
         Check Redis → NOT FOUND ❌
         Create new job...
```

---

## 🔢 Scaling Example

### Before: Single Process

```
┌──────────────────────────────┐
│      Streamlit Process       │
│                              │
│  User 1: Processing job ⏳   │
│  User 2: Waiting... 😴       │
│  User 3: Waiting... 😴       │
│  User 4: Waiting... 😴       │
└──────────────────────────────┘

Max throughput: 1 job at a time
```

### After: Multiple Workers

```
┌──────────────────────────────┐
│        Worker 1              │
│  User 1: Processing job ⏳   │
└──────────────────────────────┘

┌──────────────────────────────┐
│        Worker 2              │
│  User 2: Processing job ⏳   │
└──────────────────────────────┘

┌──────────────────────────────┐
│        Worker 3              │
│  User 3: Processing job ⏳   │
└──────────────────────────────┘

┌──────────────────────────────┐
│        Worker 4              │
│  Waiting for jobs... 💤      │
└──────────────────────────────┘

Max throughput: 4 jobs simultaneously
Can scale to 10, 20, 50+ workers!
```

---

## 🚀 Deployment Options Visualized

### Local Development

```
Your Computer
├── Docker Desktop
│   ├── Redis Container
│   ├── Backend Container
│   ├── Worker Containers (x2)
│   └── Frontend Container
└── Browser → http://localhost:8501

Command: make local-up
Cost: $0
```

### Cloud Run (Google Cloud)

```
Google Cloud
├── Memorystore Redis
├── Cloud Run: Backend
│   ├── Min 1 instance
│   └── Max 10 instances (auto-scale)
├── Compute Engine: Workers
│   └── 2 VMs (always on)
├── Cloud Run: Frontend
│   ├── Min 1 instance
│   └── Max 5 instances (auto-scale)
└── Cloud SQL: PostgreSQL

Command: make deploy-all PROJECT_ID=your-project
Cost: ~$340/month
```

### Fly.io

```
Fly.io
├── Upstash Redis
├── Fly App: Backend
│   └── 2 instances
├── Fly App: Workers
│   └── 2 instances
├── Fly App: Frontend
│   └── 2 instances
└── Fly Postgres

Command: flyctl deploy
Cost: ~$103/month
```

---

## 🎨 UI Flow Comparison

### Old UI Flow (Blocking)

```
1. User enters data
   [Input box]

2. User clicks "Optimize"
   [Button]

3. ⏳ Page freezes
   (Cannot interact with anything)

4. Loading spinner appears
   🌀 "Optimizing..."
   
5. Wait... wait... wait...
   (Could be 30+ seconds)

6. ✅ Results appear
   [Results table]
   
Total time with no interaction: 30 seconds
```

### New UI Flow (Non-blocking)

```
1. User enters data
   [Input box] ✅ Can still type

2. User clicks "Optimize"
   [Button]

3. ✅ Page stays responsive
   [Status: "Job submitted"]

4. Polling starts
   🔄 "Processing... (queued)"
   ↓
   🔄 "Processing... (started)"
   ↓
   🔄 "Processing... (90% done)"

5. Meanwhile, user can:
   - Scroll the page ✅
   - Read documentation ✅
   - Check other tabs ✅
   - Prepare next request ✅

6. ✅ Results appear
   [Results table]
   
Total time: Same, but user is never blocked!
```

---

## 📱 Quick Reference

### Ports & URLs

| Service | Port | URL | Purpose |
|---------|------|-----|---------|
| Frontend | 8501 | http://localhost:8501 | Streamlit UI |
| Backend | 8000 | http://localhost:8000 | FastAPI API |
| API Docs | 8000 | http://localhost:8000/docs | Interactive docs |
| Redis | 6379 | (internal) | Queue & cache |

### Commands

| Task | Command |
|------|---------|
| Start all | `make local-up` |
| Stop all | `make local-down` |
| View logs | `make local-logs` |
| Test backend | `curl http://localhost:8000/health` |
| Access Redis | `make redis-cli` |
| Scale workers | `docker-compose scale worker=4` |

### File Structure

```
Optimiser/
├── app.py                 # Original Streamlit app
├── backend/
│   ├── app.py            # FastAPI service
│   ├── tasks.py          # Worker tasks
│   └── worker.py         # RQ worker
├── docker/
│   ├── Dockerfile.backend
│   ├── Dockerfile.frontend
│   └── Dockerfile.worker
├── docker-compose.yml     # Local orchestration
├── Makefile              # Automation commands
└── STEP_BY_STEP_GUIDE.md # This guide!
```

---

## ✅ Success Indicators

You know it's working when:

1. ✅ `make local-up` completes without errors
2. ✅ All 4 services show as "running" in `docker-compose ps`
3. ✅ http://localhost:8000/health returns `{"status": "ok"}`
4. ✅ http://localhost:8501 loads the Streamlit app
5. ✅ Clicking "Optimize" doesn't freeze the UI
6. ✅ A progress indicator appears while processing
7. ✅ Results appear after processing completes
8. ✅ Second identical request returns instantly (cached!)

---

## 🎓 Understanding by Analogy

Think of it like a restaurant:

**Before (Monolith):**
- One chef does everything
- Takes order, cooks, serves
- If cooking a big meal, no one else can order
- Kitchen freezes for everyone

**After (Microservices):**
- **Frontend** = Waiter (takes orders, serves results)
- **Backend** = Host (manages orders, checks if dish is ready)
- **Redis** = Kitchen ticket system + dish warmer
- **Workers** = Multiple chefs (cook in parallel)
- **PostgreSQL** = Recipe book

When you order:
1. Waiter takes order → Frontend
2. Host checks warmer for pre-made dish → Cache check
3. If not ready, ticket goes to kitchen → Queue job
4. Chef cooks while you wait at table → Worker processes
5. Waiter brings food when ready → Display result

You can talk, browse menu while chef cooks!

---

That's it! You now understand how the new architecture works. Ready to implement it? Follow the [STEP_BY_STEP_GUIDE.md](STEP_BY_STEP_GUIDE.md)!
