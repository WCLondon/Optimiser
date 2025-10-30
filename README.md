# BNG Optimiser - Standalone

A Streamlit application for optimizing Biodiversity Net Gain (BNG) unit allocation across multiple habitat banks.

## 🚀 What's New - Performance & Architecture Refactoring

The BNG Optimiser has been refactored for better performance and scalability:

- **⚡ 60-80% faster** page loads through strategic caching
- **🔄 Optional FastAPI backend** for background job processing
- **📦 Docker containers** for easy deployment
- **☁️ Cloud-ready** with deployment guides for Cloud Run and Fly.io

**See [QUICKSTART.md](QUICKSTART.md) for getting started with the new architecture.**

**See [REFACTORING_GUIDE.md](REFACTORING_GUIDE.md) for detailed architecture documentation.**

**Note**: All improvements are **backward compatible**. The app works exactly as before, just faster!

## Features

### Core Functionality
- **Location-based Optimization**: Find optimal BNG unit allocations based on target site location (LPA/NCA)
- **Multi-bank Support**: Search across multiple habitat banks for best pricing and availability
- **Habitat Matching**: Intelligent matching of demand and supply habitats following trading rules
- **Pricing Tiers**: Automatic tier calculation (local/adjacent/far) based on geographic proximity
- **Manual Quote Adjustments**: Remove optimizer-generated allocations and add manual entries for area, hedgerow, and watercourse habitats with paired habitat support
- **Client Reports**: Generate professional client-facing reports and email templates

### Performance Optimizations (New!)
- **Smart Caching**: Geocoding, ArcGIS queries, and reference data cached for faster response
- **Connection Pooling**: Efficient database connection management
- **Non-blocking UI**: Optional backend for heavy computations without blocking the interface

### Database & Admin Features
- **PostgreSQL Database**: Persistent data storage with transaction support and automatic retries
- **Automatic Data Tracking**: All submissions and optimization results saved automatically
- **Admin Dashboard**: Secure password-protected dashboard for viewing historical data
- **Advanced Filtering**: Filter submissions by date, client, LPA, NCA, or reference number
- **Data Export**: Export submissions and allocation details to CSV
- **Summary Statistics**: View total submissions, revenue, and top clients/LPAs
- **JSONB Storage**: Efficient native JSON storage for complex data
- **Connection Pooling**: Managed database connections for optimal performance

See [DATABASE_FEATURE.md](DATABASE_FEATURE.md) for database feature documentation, [POSTGRESQL_MIGRATION.md](POSTGRESQL_MIGRATION.md) for migration guide, and [MANUAL_QUOTE_ADJUSTMENT_GUIDE.md](MANUAL_QUOTE_ADJUSTMENT_GUIDE.md) for the manual quote adjustment feature.


## Requirements

- Python 3.8+
- Streamlit 1.37+
- PostgreSQL 12+ (for production deployment)
- See `requirements.txt` for full dependencies

## Installation

1. Clone the repository:
```bash
git clone https://github.com/WCLondon/Optimiser.git
cd Optimiser
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Configure database and authentication:
Create `.streamlit/secrets.toml`:
```toml
[database]
url = "postgresql://user:password@host:port/database"

[auth]
username = "your_username"
password = "your_password"

[admin]
password = "admin_password"
```

## Usage

### Running the Application

```bash
streamlit run app.py
```

The app will open in your default web browser at `http://localhost:8501`

### Basic Workflow

1. **Login**: Use your credentials (default: WC0323 / Wimborne)

2. **Load Backend**: Upload or use the example backend Excel file containing:
   - Banks data
   - Pricing information
   - Habitat catalog
   - Stock availability
   - Trading rules

3. **Locate Site**: Enter postcode or address to determine target LPA/NCA

4. **Enter Demand**: Add habitat units needed for your development

5. **Optimize**: Run the optimizer to find best allocation across banks

6. **Review Results**: View allocation details, costs, and selected banks

7. **Generate Report**: Create client-facing report with email template

8. **Automatic Save**: Submission automatically saved to database when generating report

### Admin Dashboard

1. Switch to "Admin Dashboard" mode in the sidebar
2. Enter admin password (default: WCAdmin2024)
3. View, filter, and export historical submissions
4. Access detailed allocation breakdowns

## Project Structure

```
Optimiser/
├── app.py                          # Main Streamlit application
├── database.py                     # Database module for submissions tracking (PostgreSQL)
├── db.py                           # Database connection management (SQLAlchemy)
├── requirements.txt                # Python dependencies
├── secrets.toml.example            # Example secrets configuration
├── test_database_validation.py     # Validation tests for database module
├── .gitignore                      # Git ignore rules
├── data/                           # Example backend data
│   └── HabitatBackend_WITH_STOCK.xlsx
└── docs/
    ├── DATABASE_FEATURE.md         # Database feature documentation
    ├── POSTGRESQL_MIGRATION.md     # PostgreSQL migration guide
    ├── MANUAL_ENTRIES_FEATURE.md   # Manual entries documentation
    ├── IMPLEMENTATION_SUMMARY.md   # Implementation details
    ├── PAIRED_ALLOCATION_FIX.md    # Paired allocation documentation
    └── UI_MOCKUP.md                # UI design reference
```

## Key Features Explained

### Location-Based Tiers
- **Local**: Target site within same LPA or NCA as bank
- **Adjacent**: Target site in neighboring LPA/NCA
- **Far**: All other locations

Tiers affect unit multipliers and pricing.

### Paired Allocations
Some habitats (e.g., Orchard) use "paired" allocations combining:
- Primary habitat (e.g., Orchard)
- Secondary habitat (cheapest eligible area habitat)

Mixing ratios and pricing calculated automatically.

### Stock Management
- Real-time stock tracking
- Quote reservation options
- Automatic availability checking

### Manual Additions
After optimization, you can manually add:
- Hedgerow units
- Watercourse units

These integrate seamlessly into final reports and costs.

## Configuration

### Database Configuration (PostgreSQL)

Create `.streamlit/secrets.toml` with your PostgreSQL connection:

```toml
[database]
url = "postgresql://username:password@host:port/database"

[auth]
username = "WC0323"
password = "Wimborne"

[admin]
password = "WCAdmin2024"
```

**Connection String Examples:**
- Local: `postgresql://user:pass@localhost:5432/optimiser_db`
- AWS RDS: `postgresql://user:pass@mydb.abc123.us-east-1.rds.amazonaws.com:5432/optimiser_db`
- Heroku: Use DATABASE_URL from Heroku dashboard

**For detailed migration instructions**, see [POSTGRESQL_MIGRATION.md](POSTGRESQL_MIGRATION.md)

### Backend Data Format
The backend Excel file must contain these sheets:
- **Banks**: Bank details (name, location, coordinates)
- **Pricing**: Price per unit by bank, habitat, tier, contract size
- **HabitatCatalog**: Habitat definitions and trading rules
- **Stock**: Available units per bank and habitat
- **DistinctivenessLevels**: Distinctiveness categories
- **SRM**: Strategic Resource Multipliers
- **TradingRules** (optional): Custom trading rules

### Optimization Modes
- **PuLP Solver** (if installed): Optimal mathematical solution
- **Greedy Algorithm** (fallback): Fast heuristic solution

## Security Notes

- Default passwords should be changed in production
- Never commit `.streamlit/secrets.toml` to version control
- Admin dashboard requires separate authentication
- No sensitive data exposed in client-facing reports
- Use SSL/TLS for PostgreSQL connections in production

## Troubleshooting

### Common Issues

**"No backend loaded"**
- Upload a valid backend Excel file or enable "Use example backend"

**"No pricing rows found"**
- Check that Pricing sheet has data for selected contract size
- Verify habitat names match between demand and catalog

**"Optimization failed"**
- Check stock availability
- Verify trading rules allow requested allocations
- Review diagnostics section for details

**"Database connection errors"**
- Verify PostgreSQL is running and accessible
- Check database URL in `.streamlit/secrets.toml`
- Ensure firewall allows connections to PostgreSQL port
- Test with `db_healthcheck()` method

**"Database not saving"**
- Verify database credentials are correct
- Check PostgreSQL user has necessary permissions
- Review Streamlit logs for error messages
- Ensure database schema is initialized

### Getting Help

- Check [QUICKSTART.md](QUICKSTART.md) for quick start guide
- Review [REFACTORING_GUIDE.md](REFACTORING_GUIDE.md) for architecture details
- Check [POSTGRESQL_MIGRATION.md](POSTGRESQL_MIGRATION.md) for database setup
- Review [DATABASE_FEATURE.md](DATABASE_FEATURE.md) for feature documentation
- Check the diagnostics section in the app
- Review Streamlit logs for detailed error messages
- Test database connectivity with validation script: `python test_database_validation.py`

## Deployment

### Local Development

**Frontend only** (simple):
```bash
pip install -r requirements.txt
streamlit run app.py
```

**Full stack** (with backend + worker + Redis):
```bash
# Start all services with Docker Compose
make dev

# Or manually
docker compose up -d

# View logs
make dev-logs
```

**Access**:
- Frontend: http://localhost:8501
- Backend API: http://localhost:8000
- API Docs: http://localhost:8000/docs

### Production Deployment

**Cloud Run (Google Cloud)**:
```bash
# Configure
export PROJECT_ID=your-gcp-project
export REGION=europe-west2

# Deploy
make deploy-cloudrun-backend PROJECT_ID=$PROJECT_ID
make deploy-cloudrun-frontend PROJECT_ID=$PROJECT_ID
```

See [CLOUDRUN_DEPLOYMENT.md](CLOUDRUN_DEPLOYMENT.md) for complete guide.

**Fly.io**:
```bash
# Deploy backend
flyctl deploy --config fly.backend.toml

# Deploy frontend
flyctl deploy --config fly.frontend.toml
```

See [FLY_DEPLOYMENT.md](FLY_DEPLOYMENT.md) for complete guide.

### Architecture Options

1. **Frontend Only**: Deploy just `app.py` - get caching benefits without microservices
2. **Hybrid**: Frontend + optional backend for heavy computations
3. **Full Microservices**: Frontend + Backend + Workers for maximum scalability

See [REFACTORING_GUIDE.md](REFACTORING_GUIDE.md) for architecture details and migration paths.

## License

[Add your license information here]

## Contact

Wild Capital - [contact information]

## Version History

### v9.14 (Current)
- Added database tracking for all submissions
- Implemented secure admin dashboard
- Added data export functionality
- Enhanced filtering and search capabilities

### v9.13
- Added "Start New Quote" functionality
- Improved map refresh behavior
- Enhanced state management

### v9.12
- Fixed map display issues
- Improved UI responsiveness
- Enhanced error handling

See git history for complete changelog.
