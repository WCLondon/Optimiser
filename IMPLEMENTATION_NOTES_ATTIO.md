# Attio App Migration - Implementation Notes

## Overview

This document details the implementation of the BNG Optimiser migration from Streamlit to an Attio App.

## Current Status

### ✅ Completed

1. **Project Structure**
   - Created `backend/` directory for FastAPI server
   - Created `frontend/` directory for Attio App SDK
   - Added comprehensive documentation
   - Set up Docker deployment infrastructure

2. **Backend (FastAPI)**
   - ✅ Created `main.py` with REST endpoints:
     - `POST /run` - Start optimization job
     - `GET /status/{job_id}` - Poll job status
     - `POST /save` - Save results to Attio
     - `GET /health` - Health check
     - `GET /jobs` - List jobs (debugging)
   - ✅ Created `optimiser_core.py` for business logic extraction
   - ✅ Created `config.py` for environment configuration
   - ✅ Added Pydantic models for request/response validation
   - ✅ Implemented job queue (in-memory for now)
   - ✅ Added CORS middleware for cross-origin requests
   - ✅ Created Dockerfile for containerization
   - ✅ Added basic pytest tests (all passing)

3. **Frontend (Attio App SDK)**
   - ✅ Created `attio.json` manifest
   - ✅ Created `package.json` with dependencies
   - ✅ Created `QuoteWidget.tsx` React component:
     - Form inputs for demand (habitat, units)
     - Location inputs (postcode, address)
     - Run Quote button
     - Job status polling
     - Results display panel
     - Save to Attio button
   - ✅ Created `index.tsx` main app entry
   - ✅ Added TypeScript configuration

4. **Integration**
   - ✅ Attio Assert Record endpoint integration
   - ✅ Record mapping function (customizable)
   - ✅ Environment variable configuration

5. **Documentation**
   - ✅ `ATTIO_APP_README.md` - Comprehensive documentation
   - ✅ `ATTIO_QUICKSTART.md` - Quick start guide
   - ✅ API endpoint documentation
   - ✅ Widget usage instructions
   - ✅ Troubleshooting guide

6. **Docker & Deployment**
   - ✅ `backend/Dockerfile` - Backend container
   - ✅ `docker-compose.yml` - Full stack deployment
   - ✅ PostgreSQL database service
   - ✅ Redis cache service
   - ✅ pgAdmin for database management
   - ✅ Environment variable templates

### 🔄 In Progress / TODO

1. **Core Optimization Logic Extraction**
   - ⚠️ **CRITICAL**: The `run_quote()` function in `optimiser_core.py` is currently a placeholder
   - **NEEDED**: Extract the full `optimise()` function from `app.py` (lines ~3154-3428)
   - **NEEDED**: Extract all helper functions:
     - `prepare_options()` - Build options for area habitats
     - `prepare_hedgerow_options()` - Build hedgerow options
     - `prepare_watercourse_options()` - Build watercourse options
     - `select_contract_size()` - Determine contract size
     - `build_tier_for_bank()` - Calculate proximity tier
     - All trading rule logic
     - All PuLP solver logic
     - Greedy algorithm fallback
   - **DEPENDENCIES**: These functions reference:
     - Backend data structures (Banks, Pricing, HabitatCatalog, Stock)
     - Trading rules
     - SRM (Strategic Resource Multipliers)
     - Paired allocation logic

2. **Backend Data Loading**
   - ⚠️ **CRITICAL**: `get_default_backend_data()` returns empty structure
   - **NEEDED**: Implement loading from Excel file or database
   - **OPTIONS**:
     - Load from Excel file (use existing data loading from `app.py`)
     - Cache in memory on startup
     - Store in PostgreSQL and load on demand
     - Use Redis for caching
   - **LOCATION**: The example backend file is at `data/HabitatBackend_WITH_STOCK.xlsx`

3. **Location Services**
   - ⚠️ **PARTIAL**: `find_location()` in `optimiser_core.py` has placeholders
   - **NEEDED**: Extract from `app.py`:
     - `find_site()` function (lines ~800-900)
     - LPA/NCA lookup via ArcGIS
     - Neighbor calculation
     - Geometry handling
   - **DEPENDENCIES**: ArcGIS REST API calls, geometry libraries

4. **Production Job Queue**
   - Current: In-memory job storage (lost on restart)
   - **RECOMMENDED**: Implement Redis-based job queue
   - **OPTIONS**: Celery, RQ, or custom Redis implementation
   - **BENEFIT**: Persistent jobs, worker scaling, job distribution

5. **Testing**
   - ✅ Basic API tests (5 tests passing)
   - TODO: Integration tests with real optimization
   - TODO: Frontend component tests
   - TODO: End-to-end tests
   - TODO: Performance tests

6. **Security**
   - TODO: API authentication/authorization
   - TODO: Rate limiting
   - TODO: Input validation (basic Pydantic validation exists)
   - TODO: Secrets management (currently using env vars)

## Technical Decisions

### Architecture Choices

1. **FastAPI for Backend**
   - Pros: Modern, fast, async support, automatic OpenAPI docs
   - Cons: None significant
   - Alternative considered: Flask (chose FastAPI for better async)

2. **In-Memory Job Queue (MVP)**
   - Pros: Simple, no dependencies, good for development
   - Cons: Jobs lost on restart, no scaling, no distribution
   - Migration path: Redis/Celery when needed

3. **Attio App SDK (Native Widget)**
   - Pros: Native integration, better UX, access to Attio context
   - Cons: Requires learning Attio SDK
   - Alternative: iframe mode (also supported via feature flag)

4. **React for Frontend**
   - Pros: Required by Attio SDK, component model, hooks
   - Cons: None (required)

5. **Pydantic v2 for Validation**
   - Pros: Type safety, automatic validation, FastAPI integration
   - Cons: Breaking changes from v1 (handled)

### Data Flow

```
User interacts with Widget (React)
    ↓
Widget calls Backend API (POST /run)
    ↓
Backend queues job, returns job_id
    ↓
Widget polls status (GET /status/{job_id})
    ↓
Backend runs optimization in background
    ↓
Widget receives results
    ↓
User clicks "Save to Attio"
    ↓
Widget calls Backend (POST /save)
    ↓
Backend calls Attio Assert Record API
    ↓
Record updated in Attio
```

## Code Organization

### Backend Structure
```
backend/
├── __init__.py           # Package init
├── main.py              # FastAPI app, endpoints
├── optimiser_core.py    # Pure optimization logic (TO COMPLETE)
├── config.py            # Settings, env vars
├── requirements.txt     # Dependencies
├── Dockerfile          # Container definition
├── .env.example        # Environment template
└── tests/
    ├── __init__.py
    └── test_api.py     # API tests
```

### Frontend Structure
```
frontend/
├── package.json         # npm dependencies
├── attio.json          # Attio app manifest
├── tsconfig.json       # TypeScript config
└── src/
    ├── index.tsx           # Main app entry
    └── components/
        └── QuoteWidget.tsx # Main widget
```

## Dependencies

### Backend Python Packages
- `fastapi` - Web framework
- `uvicorn` - ASGI server
- `pydantic` - Data validation
- `httpx` - HTTP client for Attio API
- `pandas` - Data processing
- `numpy` - Numerical computations
- `pulp` - Optimization solver
- `sqlalchemy` - Database ORM
- `psycopg` - PostgreSQL driver
- `pytest` - Testing

### Frontend npm Packages
- `@attio/sdk` - Attio App SDK
- `react` - UI library
- `typescript` - Type safety

## Environment Variables

### Backend
- `ATTIO_API_KEY` - **Required** - Attio API authentication
- `ATTIO_API_URL` - Optional - API endpoint (default: production)
- `DATABASE_URL` - Optional - PostgreSQL connection
- `REDIS_URL` - Optional - Redis for job queue
- `PORT` - Optional - Server port (default: 8080)

### Frontend
- Configured via Attio app settings in dashboard
- `backendUrl` - URL of deployed backend

## Migration Path from Streamlit

The original Streamlit app (`app.py`, ~5000 lines) needs these functions extracted:

### Priority 1: Core Optimization (CRITICAL)
1. `optimise()` - Main optimization function
2. `prepare_options()` - Build feasible options
3. `prepare_hedgerow_options()` - Hedgerow-specific
4. `prepare_watercourse_options()` - Watercourse-specific
5. PuLP solver logic
6. Greedy algorithm fallback

### Priority 2: Data Processing
1. `select_contract_size()` - Contract size logic
2. `build_tier_for_bank()` - Tier calculation
3. `split_paired_rows()` - Paired allocation handling
4. Trading rule application
5. Price lookup and proxy logic

### Priority 3: Location Services
1. `find_site()` - Location lookup
2. ArcGIS API integration
3. Neighbor calculation
4. Geometry handling

### Priority 4: Utilities
1. `sstr()`, `norm_name()` - String utilities (already in optimiser_core.py)
2. `is_hedgerow()`, `is_watercourse()` - Type checking
3. Data validation functions

## Testing Strategy

### Unit Tests
- Test individual functions in `optimiser_core.py`
- Test API endpoints in isolation
- Mock external dependencies (Attio API, ArcGIS)

### Integration Tests
- Test complete optimization flow
- Test backend data loading
- Test Attio integration

### End-to-End Tests
- Test widget → backend → Attio flow
- Test error handling
- Test edge cases

### Performance Tests
- Optimization speed
- API response times
- Concurrent job handling

## Deployment Strategy

### Development
1. Use `docker-compose up` for local stack
2. Backend on `http://localhost:8080`
3. Frontend via Attio development mode

### Staging
1. Deploy backend to staging environment
2. Deploy frontend to Attio staging workspace
3. Test with real data
4. Verify Attio integration

### Production
1. Deploy backend to production (AWS/GCP/Heroku)
2. Set up PostgreSQL (managed service)
3. Set up Redis (managed service)
4. Deploy frontend to Attio production
5. Configure monitoring and logging
6. Set up backups

## Known Issues & Limitations

1. **Incomplete Optimization Logic**
   - `optimiser_core.py` needs full extraction from `app.py`
   - Placeholder returns empty results

2. **No Backend Data Loading**
   - `get_default_backend_data()` returns empty
   - Need to implement Excel loading or database integration

3. **In-Memory Job Queue**
   - Jobs lost on server restart
   - No job persistence
   - Not suitable for production

4. **No Authentication**
   - Backend API is open
   - Need to add API keys or OAuth

5. **Limited Error Handling**
   - Basic error messages
   - Need more detailed diagnostics

## Next Steps

### Immediate (Required for MVP)
1. Extract optimization logic from `app.py` to `optimiser_core.py`
2. Implement backend data loading
3. Complete location service integration
4. Test end-to-end with real data

### Short-term (Production Ready)
1. Implement Redis job queue
2. Add authentication/authorization
3. Add comprehensive error handling
4. Set up logging and monitoring
5. Add integration tests

### Long-term (Enhancements)
1. Caching strategy for backend data
2. Batch quote processing
3. Historical quote tracking
4. Performance optimization
5. Advanced reporting features

## Success Metrics

- ✅ Backend API runs and passes tests
- ✅ Frontend widget structure complete
- ✅ Docker deployment infrastructure ready
- ⏳ Complete optimization produces correct results
- ⏳ Successfully saves to Attio records
- ⏳ Performance matches Streamlit app
- ⏳ User can complete full quote workflow

## References

- Original app: `app.py` (~5000 lines)
- Database module: `database.py` (PostgreSQL integration)
- Repository layer: `repo.py` (reference tables)
- Example backend: `data/HabitatBackend_WITH_STOCK.xlsx`
- Attio SDK docs: https://docs.attio.com
- FastAPI docs: https://fastapi.tiangolo.com

## Contact

For questions or issues:
- GitHub Issues: [repository]
- Developer: [contact info]

---

**Last Updated**: 2025-10-20
**Status**: Initial implementation complete, core logic extraction pending
