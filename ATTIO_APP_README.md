# BNG Optimiser - Attio App

A complete migration of the BNG Optimiser from Streamlit to an Attio App, providing seamless quote optimization directly within Attio record pages.

## Overview

This project consists of three main components:

1. **Backend (FastAPI)**: REST API server that handles optimization logic
2. **Frontend (Attio App SDK)**: React-based widget that integrates with Attio
3. **Integration**: Connects to Attio's Assert Record API for data persistence

## Architecture

```
┌─────────────────┐
│  Attio Record   │
│     Page        │
└────────┬────────┘
         │
         │ Widget embedded
         ▼
┌─────────────────┐      HTTP/REST      ┌──────────────┐
│  Quote Widget   │ ──────────────────► │   FastAPI    │
│   (React/SDK)   │                     │   Backend    │
└─────────────────┘                     └──────┬───────┘
         │                                     │
         │ Save results                        │ Optimization
         │                                     │ Logic
         ▼                                     │
┌─────────────────┐                           │
│  Attio Assert   │◄──────────────────────────┘
│  Record API     │
└─────────────────┘
```

## Features

### Backend API

- **POST /run**: Start a quote optimization job
  - Accepts demand (habitat units), location, and options
  - Returns a job_id for status tracking
  - Runs optimization in background

- **GET /status/{job_id}**: Poll job status
  - Returns current status (pending/running/completed/failed)
  - Includes progress messages and results

- **POST /save**: Save results to Attio
  - Uses Assert Record endpoint for idempotent writes
  - Maps quote data to Attio schema

### Frontend Widget

- **Form inputs**: Habitat selection, units, location (postcode/address)
- **Run Quote button**: Triggers optimization
- **Progress display**: Shows real-time status and logs
- **Results panel**: Displays allocation details and costs
- **Save to Attio**: Persists results to record

### Attio Integration

- **Record Widget**: Loads on record pages, reads recordId from context
- **Assert Record**: Idempotent upsert of quote data
- **Scopes**: 
  - `records:read` - Read record data
  - `records:write` - Write quote results
  - `object-configuration:read` - Read object schemas

## Installation

### Prerequisites

- Node.js 18+ (for frontend)
- Python 3.11+ (for backend)
- Docker (optional, for containerized deployment)
- Attio developer account
- PostgreSQL (if using database features)

### Backend Setup

1. Navigate to backend directory:
```bash
cd backend
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Configure environment variables:
```bash
cp .env.example .env
# Edit .env with your settings:
# - ATTIO_API_KEY: Your Attio API key
# - DATABASE_URL: PostgreSQL connection string (if using database)
```

4. Run the server:
```bash
uvicorn main:app --host 0.0.0.0 --port 8080 --reload
```

The API will be available at `http://localhost:8080`

### Frontend Setup

1. Navigate to frontend directory:
```bash
cd frontend
```

2. Install dependencies:
```bash
npm install
```

3. Configure Attio app:
- Edit `attio.json` to match your requirements
- Update widget settings (backend URL)

4. Development mode:
```bash
npm run dev
```

5. Build for production:
```bash
npm run build
```

6. Deploy to Attio:
```bash
npm run deploy
```

### Docker Deployment

For production deployment using Docker:

1. Build backend image:
```bash
cd backend
docker build -t bng-optimiser-backend .
```

2. Run backend container:
```bash
docker run -d -p 8080:8080 \
  -e ATTIO_API_KEY=your_key \
  -e DATABASE_URL=your_db_url \
  --name bng-backend \
  bng-optimiser-backend
```

Alternatively, use docker-compose (see `docker-compose.yml`).

## Configuration

### Backend Environment Variables

| Variable | Description | Required | Default |
|----------|-------------|----------|---------|
| `ATTIO_API_KEY` | Attio API authentication key | Yes | - |
| `ATTIO_API_URL` | Attio API base URL | No | `https://api.attio.com/v2` |
| `DATABASE_URL` | PostgreSQL connection string | No | - |
| `PORT` | Backend server port | No | `8080` |
| `REDIS_URL` | Redis URL for job queue | No | - |

### Widget Settings

Configure these in the Attio app dashboard:

- **Backend URL**: URL where your FastAPI backend is hosted
- **Enable iframe mode**: Toggle between native SDK and iframe widget

## Usage

### Using the Widget

1. **Install the app** in your Attio workspace
2. **Add the widget** to a record page:
   - Go to a record page (e.g., Project, Company, or custom object)
   - Click "Add widget"
   - Select "BNG Quote Optimizer"
3. **Enter demand**:
   - Select habitats from dropdown
   - Enter required units
   - Add/remove rows as needed
4. **Set location**:
   - Enter postcode or address
   - Widget will determine LPA/NCA automatically
5. **Run quote**:
   - Click "Run Quote"
   - Monitor progress in real-time
   - View results when complete
6. **Save to Attio**:
   - Click "Save to Attio" to persist results
   - Data is saved to the current record

### API Usage

You can also use the backend API directly:

```bash
# Start a quote job
curl -X POST http://localhost:8080/run \
  -H "Content-Type: application/json" \
  -d '{
    "demand": [
      {"habitat_name": "Grassland - Other neutral grassland", "units": 10.5}
    ],
    "location": {
      "postcode": "SW1A 1AA"
    }
  }'

# Response: {"job_id": "abc-123", "status": "pending", "message": "Job started"}

# Check status
curl http://localhost:8080/status/abc-123

# Response: {"job_id": "abc-123", "status": "completed", "result": {...}}
```

## Development

### Backend Development

The backend is structured as follows:

```
backend/
├── main.py              # FastAPI app, endpoints
├── optimiser_core.py    # Core optimization logic
├── requirements.txt     # Python dependencies
├── Dockerfile          # Container definition
└── .env.example        # Environment template
```

Key functions:
- `run_quote(payload)`: Pure function that runs optimization
- `process_quote_job()`: Background task handler
- `map_quote_to_attio_record()`: Maps results to Attio schema

### Frontend Development

The frontend uses the Attio App SDK:

```
frontend/
├── src/
│   ├── index.tsx              # Main app entry
│   └── components/
│       └── QuoteWidget.tsx    # Main widget component
├── package.json
├── attio.json                 # App manifest
└── tsconfig.json
```

Key components:
- `QuoteWidget`: Main React component
- Form state management with React hooks
- API communication with fetch
- Real-time polling for job status

### Testing

Backend tests (create these):
```bash
cd backend
pytest tests/
```

Frontend tests:
```bash
cd frontend
npm test
```

## Data Mapping

### Quote Results → Attio Record

The backend maps quote results to Attio records as follows:

| Quote Field | Attio Field | Type |
|-------------|-------------|------|
| `total_cost` | `total_cost` | Number |
| `contract_size` | `contract_size` | String |
| `allocations` | `allocations_json` | JSON |
| `summary` | `summary` | JSON |
| - | `quote_date` | DateTime |

Customize the mapping in `map_quote_to_attio_record()` function.

## Attio Setup

### 1. Create Developer Account

1. Go to Attio Developer Portal
2. Create a new app
3. Note your API key

### 2. Configure App

1. Upload `attio.json` manifest
2. Set required scopes:
   - `records:read`
   - `records:write`
   - `object-configuration:read`

### 3. Install App

1. Install in your workspace
2. Configure widget settings (backend URL)
3. Add widget to record pages

### 4. Create Custom Objects (Optional)

If you want to store quotes as separate objects:

1. Create "Quote" object in Attio
2. Add attributes:
   - `total_cost` (Number)
   - `contract_size` (Text)
   - `allocations_json` (Text/JSON)
   - `quote_date` (Date)
   - Relationship to source record (Company, Project, etc.)

## Troubleshooting

### Backend Issues

**Server won't start:**
- Check Python version (3.11+)
- Verify all dependencies installed
- Check port 8080 is available

**Optimization fails:**
- Check backend data is properly loaded
- Verify demand format is correct
- Review logs for specific errors

**Database connection errors:**
- Verify DATABASE_URL is correct
- Check PostgreSQL is running
- Ensure database exists

### Frontend Issues

**Widget not loading:**
- Check backend URL is correct and accessible
- Verify Attio app is installed
- Check browser console for errors

**CORS errors:**
- Ensure backend CORS is configured
- Check backend URL uses HTTPS in production

**Job polling timeout:**
- Increase polling duration
- Check backend job is actually running
- Review backend logs

### Attio Integration Issues

**Assert Record fails:**
- Verify API key is correct
- Check scopes are granted
- Review Attio object schema matches mapping

**Record not saving:**
- Check record_id is valid
- Verify object type exists
- Review API response errors

## Migration from Streamlit

This app maintains the same core logic as the original Streamlit app but with:

1. **Decoupled architecture**: UI and logic are separate
2. **REST API**: Can be used by multiple clients
3. **Job queue**: Async processing for better UX
4. **Attio integration**: Native integration with Attio data model

The core `optimise()` function from `app.py` needs to be fully extracted to `optimiser_core.py` for complete functionality.

## Roadmap

- [ ] Complete extraction of optimization logic from app.py
- [ ] Add Redis-based job queue for production
- [ ] Implement caching for backend data (Banks, Pricing, etc.)
- [ ] Add authentication/authorization for backend API
- [ ] Create iframe fallback widget
- [ ] Add comprehensive test coverage
- [ ] Performance optimization
- [ ] Enhanced error handling and logging
- [ ] Support for batch quote processing

## License

[Specify your license]

## Support

For issues and questions:
- GitHub Issues: [repository URL]
- Email: [contact email]

## Contributing

[Contribution guidelines if applicable]
