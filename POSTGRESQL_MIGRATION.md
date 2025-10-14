# PostgreSQL Migration Guide

This document provides instructions for migrating from SQLite to PostgreSQL.

## Overview

The SubmissionsDB module has been refactored to use PostgreSQL via SQLAlchemy Core, providing:
- Persistent data storage across app redeploys
- Transactional integrity with automatic retries
- Better performance and scalability
- JSONB support for efficient JSON storage
- Connection pooling and health checks

## Prerequisites

1. **PostgreSQL Database**: You need access to a PostgreSQL database (version 12+)
   - Can be hosted on services like AWS RDS, Google Cloud SQL, Heroku Postgres, etc.
   - Or self-hosted PostgreSQL instance

2. **Python Dependencies**: Already included in requirements.txt
   - sqlalchemy >= 2.0
   - psycopg[binary] >= 3.1
   - tenacity >= 8.0

## Migration Steps

### 1. Set Up PostgreSQL Database

Create a new database for the application:

```sql
CREATE DATABASE optimiser_db;
CREATE USER optimiser_user WITH PASSWORD 'secure_password';
GRANT ALL PRIVILEGES ON DATABASE optimiser_db TO optimiser_user;
```

### 2. Configure Streamlit Secrets

Create or update `.streamlit/secrets.toml` with your database connection string:

```toml
[database]
url = "postgresql://optimiser_user:secure_password@localhost:5432/optimiser_db"

[auth]
username = "WC0323"
password = "Wimborne"

[admin]
password = "WCAdmin2024"
```

**Connection String Format:**
```
postgresql://[username]:[password]@[host]:[port]/[database]
```

**Examples:**
- Local: `postgresql://user:pass@localhost:5432/optimiser_db`
- AWS RDS: `postgresql://user:pass@mydb.abc123.us-east-1.rds.amazonaws.com:5432/optimiser_db`
- Heroku: Use the DATABASE_URL from Heroku dashboard

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Initialize Database Schema

The schema will be automatically created on first run when you start the application:

```bash
streamlit run app.py
```

The `_init_database()` method is idempotent, so it's safe to run multiple times.

### 5. Verify Connection

Use the health check method to verify database connectivity:

```python
from database import SubmissionsDB

db = SubmissionsDB()
if db.db_healthcheck():
    print("✓ Database connection successful")
else:
    print("✗ Database connection failed")
```

## Data Migration (Optional)

If you have existing SQLite data to migrate:

### Option 1: Export/Import via CSV

1. **Export from SQLite:**
```python
import sqlite3
import pandas as pd

# Connect to old SQLite database
conn = sqlite3.connect('submissions.db')

# Export submissions
submissions_df = pd.read_sql_query("SELECT * FROM submissions", conn)
submissions_df.to_csv('submissions_export.csv', index=False)

# Export allocation details
allocations_df = pd.read_sql_query("SELECT * FROM allocation_details", conn)
allocations_df.to_csv('allocations_export.csv', index=False)

# Export introducers
introducers_df = pd.read_sql_query("SELECT * FROM introducers", conn)
introducers_df.to_csv('introducers_export.csv', index=False)

conn.close()
```

2. **Import to PostgreSQL:**
```python
from database import SubmissionsDB
import pandas as pd
import json

db = SubmissionsDB()
engine = db._get_connection()

# Note: You may need to manually adjust data types for JSONB and array fields
# This is a simplified example and may need customization

# Read exported data
submissions_df = pd.read_csv('submissions_export.csv')
allocations_df = pd.read_csv('allocations_export.csv')
introducers_df = pd.read_csv('introducers_export.csv')

# Import into PostgreSQL (adjust as needed)
# You'll need to handle JSON/array conversions for PostgreSQL
```

### Option 2: Fresh Start

If historical data is not critical, simply start fresh with the new PostgreSQL database.

## Database Schema

### Tables Created

1. **submissions**: Main submissions table with JSONB fields for complex data
2. **allocation_details**: Normalized allocation data with foreign key to submissions
3. **introducers**: Promoter/introducer management

### Key Differences from SQLite

| Feature | SQLite | PostgreSQL |
|---------|--------|------------|
| Primary Keys | `INTEGER PRIMARY KEY AUTOINCREMENT` | `SERIAL PRIMARY KEY` |
| Timestamps | `TEXT` (ISO format) | `TIMESTAMP` |
| JSON Data | `TEXT` (JSON strings) | `JSONB` (native JSON) |
| Arrays | `TEXT` (JSON arrays) | `TEXT[]` (native arrays) |
| Case-sensitive search | `LIKE` | `ILIKE` |
| Transactions | Implicit | Explicit with retry |

## API Compatibility

All public methods maintain backward compatibility:
- Same method names
- Same parameters
- Same return types
- No breaking changes to existing code

The only change required is configuration (database connection string in secrets).

## Features

### Transaction Management

All write operations use explicit transactions with automatic rollback on errors:

```python
with engine.connect() as conn:
    trans = conn.begin()
    try:
        # Perform database operations
        trans.commit()
    except Exception as e:
        trans.rollback()
        raise
```

### Automatic Retries

Write operations automatically retry on transient failures (up to 3 attempts):

```python
@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=1, max=10),
    retry=retry_if_exception_type((Exception,)),
    reraise=True
)
def store_submission(...):
    # Implementation with automatic retry
```

### Connection Pooling

SQLAlchemy manages a connection pool with:
- Pool size: 5 connections
- Max overflow: 10 additional connections
- Pre-ping: Validates connections before use
- Recycle: Connections recycled after 1 hour

### Health Checks

Basic connectivity testing:

```python
db = SubmissionsDB()
is_healthy = db.db_healthcheck()
```

## Troubleshooting

### Connection Errors

**Error:** `Database URL not found in Streamlit secrets`

**Solution:** Ensure `.streamlit/secrets.toml` exists with `[database] url` configured

---

**Error:** `Connection refused`

**Solution:** 
- Verify PostgreSQL is running
- Check host/port in connection string
- Verify firewall rules allow connection

---

**Error:** `Authentication failed`

**Solution:**
- Verify username/password in connection string
- Check PostgreSQL user permissions

### Schema Errors

**Error:** `relation "submissions" does not exist`

**Solution:** Run the app once to initialize schema, or manually run:
```python
from database import SubmissionsDB
db = SubmissionsDB()
```

### Data Type Errors

**Error:** Type conversion errors for JSONB or arrays

**Solution:** The code handles conversion automatically, but if you're migrating data:
- JSON fields: Ensure valid JSON strings
- Array fields: Pass Python lists, not JSON strings

## Performance Considerations

### Indexes

The following indexes are automatically created:
- `idx_submissions_date`: For sorting by submission date
- `idx_submissions_client`: For filtering by client name
- `idx_submissions_lpa`: For filtering by LPA
- `idx_submissions_nca`: For filtering by NCA
- `idx_allocation_details_submission`: For joining allocations
- `idx_introducers_name`: For introducer lookups

### Query Optimization

- Use `ILIKE` for case-insensitive searches (PostgreSQL-specific)
- JSONB fields support efficient indexing (can be added if needed)
- Connection pooling reduces connection overhead

## Security Best Practices

1. **Never commit secrets.toml** to version control
2. **Use environment variables** for production deployments
3. **Rotate passwords** regularly
4. **Use SSL/TLS** for database connections in production
5. **Limit database user permissions** to only what's needed
6. **Enable PostgreSQL logging** for audit trails

## Production Deployment

For production environments:

1. **Use managed PostgreSQL** (AWS RDS, Google Cloud SQL, etc.)
2. **Enable SSL** in connection string:
   ```toml
   [database]
   url = "postgresql://user:pass@host:5432/db?sslmode=require"
   ```
3. **Set up backups** (automated via cloud provider)
4. **Monitor connections** and adjust pool size if needed
5. **Configure read replicas** for high-traffic scenarios

## Rollback Plan

If you need to rollback to SQLite:

1. Keep a backup of your SQLite database file
2. Checkout the previous version of the code before this migration
3. Restore the SQLite file
4. Remove PostgreSQL configuration from secrets

## Support

For issues or questions:
- Check error messages in Streamlit logs
- Verify PostgreSQL server logs
- Ensure all dependencies are installed
- Test database connectivity separately from the app

## Next Steps

After successful migration:
1. Test all CRUD operations
2. Verify data persistence across app restarts
3. Test admin dashboard functionality
4. Set up regular database backups
5. Monitor database performance
6. Consider additional indexes for specific queries if needed
