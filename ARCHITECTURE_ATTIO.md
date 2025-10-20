# BNG Optimiser - Attio App Architecture

## System Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────┐
│                           Attio Platform                            │
│                                                                     │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │                     Record Page (e.g., Project)               │  │
│  │                                                                │  │
│  │  ┌──────────────────────────────────────────────────────┐    │  │
│  │  │         BNG Quote Widget (React Component)           │    │  │
│  │  │                                                        │    │  │
│  │  │  • Form: Demand (Habitat, Units)                      │    │  │
│  │  │  • Location: Postcode/Address                         │    │  │
│  │  │  • Run Quote Button                                   │    │  │
│  │  │  • Progress Display                                   │    │  │
│  │  │  • Results Panel                                      │    │  │
│  │  │  • Save to Attio Button                               │    │  │
│  │  │                                                        │    │  │
│  │  └───────────────────┬────────────────────────────────────┘    │  │
│  │                      │                                         │  │
│  └──────────────────────┼─────────────────────────────────────────┘  │
│                         │                                            │
│                         │ HTTP REST API                              │
│                         │ (POST /run, GET /status, POST /save)       │
└─────────────────────────┼────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────────────┐
│                      FastAPI Backend Server                         │
│                      (Port 8080)                                    │
│                                                                     │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │                     API Endpoints                            │  │
│  │                                                                │  │
│  │  POST   /run          → Start optimization job              │  │
│  │  GET    /status/{id}  → Poll job status                     │  │
│  │  POST   /save         → Save results to Attio               │  │
│  │  GET    /health       → Health check                        │  │
│  │  GET    /jobs         → List all jobs (debug)               │  │
│  │                                                                │  │
│  └───────────────────────┬──────────────────────────────────────┘  │
│                          │                                          │
│  ┌───────────────────────▼──────────────────────────────────────┐  │
│  │              Job Queue & Processing                          │  │
│  │                                                                │  │
│  │  • In-memory job store (MVP)                                │  │
│  │  • Background task processing                                │  │
│  │  • Job status tracking                                       │  │
│  │  • TODO: Redis-based queue for production                   │  │
│  │                                                                │  │
│  └───────────────────────┬──────────────────────────────────────┘  │
│                          │                                          │
│  ┌───────────────────────▼──────────────────────────────────────┐  │
│  │            Optimiser Core Logic                              │  │
│  │            (optimiser_core.py)                               │  │
│  │                                                                │  │
│  │  • run_quote(payload) → Main entry point                    │  │
│  │  • find_location() → LPA/NCA lookup                         │  │
│  │  • TODO: Extract full optimise() from app.py                │  │
│  │  • TODO: prepare_options() logic                            │  │
│  │  • TODO: PuLP solver integration                            │  │
│  │                                                                │  │
│  └───────────────────────┬──────────────────────────────────────┘  │
│                          │                                          │
│                          ▼                                          │
│                   Backend Data                                      │
│              (Banks, Pricing, Catalog, Stock)                       │
│                                                                     │
│              TODO: Load from Excel or Database                      │
└──────────────────┬──────────────────────────────┬──────────────────┘
                   │                               │
                   │                               │ Attio API
                   ▼                               ▼
┌────────────────────────────────┐  ┌─────────────────────────────────┐
│     PostgreSQL Database        │  │      Attio Assert Record        │
│                                │  │           API                   │
│  • submissions table           │  │                                 │
│  • allocations table           │  │  • Upsert quote records         │
│  • Historical tracking         │  │  • Match by record_id           │
│  • JSON data storage           │  │  • Update Company/Project       │
│                                │  │                                 │
└────────────────────────────────┘  └─────────────────────────────────┘
```

## Data Flow Sequence

### 1. User Runs Quote

```
User (Widget)
    │
    │ 1. Fill form (demand, location)
    │ 2. Click "Run Quote"
    │
    ├──► POST /run
    │    {
    │      record_id: "...",
    │      demand: [{habitat_name: "...", units: 10}],
    │      location: {postcode: "SW1A 1AA"}
    │    }
    │
Backend
    │
    │ 3. Create job_id
    │ 4. Queue background task
    │ 5. Return job_id
    │
    ├──► { job_id: "abc-123", status: "pending" }
    │
Widget
    │
    │ 6. Start polling every 2s
    │
```

### 2. Job Processing

```
Backend (Background Task)
    │
    │ 1. Update status to "running"
    │
    ├──► run_quote(payload)
    │        │
    │        ├── Load backend data
    │        ├── Find location (LPA/NCA)
    │        ├── Build options
    │        ├── Run optimization (PuLP/Greedy)
    │        └── Return results
    │
    │ 2. Update status to "completed"
    │ 3. Store results in job
```

### 3. Status Polling

```
Widget
    │
    │ Every 2 seconds:
    │
    ├──► GET /status/abc-123
    │
Backend
    │
    ├──► {
    │      job_id: "abc-123",
    │      status: "running",
    │      progress: "Running optimization...",
    │      result: null
    │    }
    │
Widget
    │
    │ Continue polling until status = "completed" or "failed"
    │
    ├──► GET /status/abc-123
    │
Backend
    │
    ├──► {
    │      job_id: "abc-123",
    │      status: "completed",
    │      result: {
    │        total_cost: 12500,
    │        contract_size: "small",
    │        allocations: [...]
    │      }
    │    }
    │
Widget
    │
    │ Display results to user
```

### 4. Save to Attio

```
User
    │
    │ Click "Save to Attio"
    │
Widget
    │
    ├──► POST /save
    │    {
    │      record_id: "...",
    │      quote_results: { ... }
    │    }
    │
Backend
    │
    ├──► map_quote_to_attio_record(results)
    │        │
    │        └── {
    │              data: {
    │                values: {
    │                  total_cost: 12500,
    │                  contract_size: "small",
    │                  allocations_json: [...],
    │                  quote_date: "2025-10-20T..."
    │                }
    │              }
    │            }
    │
    ├──► POST https://api.attio.com/v2/objects/quote/records
    │    Headers: { Authorization: "Bearer <API_KEY>" }
    │
Attio API
    │
    ├──► Record created/updated
    │
Backend
    │
    ├──► { success: true, record: {...} }
    │
Widget
    │
    │ Show success message
```

## Component Responsibilities

### Frontend Widget (QuoteWidget.tsx)
- **UI/UX**: Form inputs, buttons, progress indicators
- **State Management**: Demand rows, location, job status
- **API Communication**: POST /run, poll /status, POST /save
- **Context**: Read recordId from Attio context
- **Error Handling**: Display errors, handle timeouts

### Backend API (main.py)
- **Request Validation**: Pydantic models
- **Job Management**: Create, track, update jobs
- **Background Tasks**: Async job processing
- **API Integration**: Call Attio Assert Record
- **Response Formatting**: JSON responses

### Optimiser Core (optimiser_core.py)
- **Business Logic**: Pure optimization function
- **Location Services**: LPA/NCA lookup
- **Data Processing**: Demand validation, option building
- **Solver**: PuLP optimization or greedy fallback
- **No Dependencies**: No FastAPI, no UI, pure Python

### Configuration (config.py)
- **Environment Variables**: Load from .env
- **Settings Management**: Centralized configuration
- **Defaults**: Sensible defaults for all settings

## Deployment Architecture

### Development
```
Docker Compose Stack:
├── Backend (FastAPI) - :8080
├── Database (PostgreSQL) - :5432
├── Cache (Redis) - :6379
└── Admin (pgAdmin) - :5050

Frontend:
└── Attio Dev Mode (local SDK)
```

### Production
```
Cloud Infrastructure:
├── Backend: AWS ECS / Google Cloud Run / Heroku
├── Database: AWS RDS / Google Cloud SQL (PostgreSQL)
├── Cache: AWS ElastiCache / Google Memorystore (Redis)
├── Monitoring: CloudWatch / Stackdriver
└── Logging: CloudWatch Logs / Stackdriver Logging

Frontend:
└── Attio Production Workspace
```

## Security Considerations

### Backend API
- ⚠️ Currently: No authentication
- 🎯 TODO: Add API key validation
- 🎯 TODO: Rate limiting per client
- 🎯 TODO: Input sanitization (Pydantic helps)
- 🎯 TODO: HTTPS only in production

### Attio Integration
- ✅ API key stored in environment variable
- ✅ HTTPS for API calls
- 🎯 TODO: Scope validation
- 🎯 TODO: Error handling for permission issues

### Data Storage
- ✅ PostgreSQL credentials in .env
- ⚠️ Job data in memory (temporary)
- 🎯 TODO: Encrypt sensitive data at rest
- 🎯 TODO: Audit logging

## Performance Considerations

### Optimization Speed
- Current: Depends on app.py extraction
- Target: < 5 seconds for typical quote
- Strategy: Caching, pre-computed lookups

### API Response Time
- Health check: < 100ms
- Job creation: < 500ms
- Status polling: < 200ms
- Save to Attio: < 2s

### Scalability
- Current: Single instance
- TODO: Horizontal scaling with Redis queue
- TODO: Load balancer
- TODO: Database connection pooling

## Monitoring & Observability

### Metrics to Track
- API request rate
- Job success/failure rate
- Optimization duration
- Attio API call latency
- Error rates by endpoint

### Logging
- Structured JSON logs
- Request/response logging
- Job lifecycle events
- Error stack traces

### Alerting
- Failed job rate > threshold
- API response time > SLA
- Database connection failures
- Attio API errors

## Migration Checklist

- [x] Project structure created
- [x] Backend API scaffolded
- [x] Frontend widget scaffolded
- [x] Docker infrastructure ready
- [x] Documentation complete
- [x] Basic tests passing
- [ ] Optimization logic extracted
- [ ] Backend data loading implemented
- [ ] Location services integrated
- [ ] End-to-end testing
- [ ] Production deployment
- [ ] Monitoring setup
- [ ] User acceptance testing

---

**Document Version**: 1.0
**Last Updated**: 2025-10-20
**Status**: Architecture defined, implementation in progress
