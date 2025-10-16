# Migration from Excel to Supabase

## Overview

The BNG Optimiser has been refactored to use Supabase Postgres tables instead of Excel uploads for reference/config data. This change provides better performance, scalability, and data management capabilities.

## What Changed

### Before (Excel-based)
- Users uploaded an Excel workbook (.xlsx) containing reference tables
- Data was loaded via `pd.read_excel()` on each session
- Dependencies: `openpyxl`, `xlsxwriter`
- No centralized data management
- Manual updates required for each user

### After (Supabase-based)
- Reference data is stored in Supabase Postgres tables
- Data is loaded via SQLAlchemy Core with caching
- Dependencies: `sqlalchemy`, `psycopg[binary]`, `tenacity`
- Centralized data management
- Single source of truth for all users

## Architecture

### Repository Layer (`repo.py`)
New module that handles all database access for reference tables:
- `fetch_banks()` - Load Banks table
- `fetch_pricing()` - Load Pricing table
- `fetch_habitat_catalog()` - Load HabitatCatalog table
- `fetch_stock()` - Load Stock table
- `fetch_distinctiveness_levels()` - Load DistinctivenessLevels table
- `fetch_srm()` - Load SRM (Strategic Resource Multipliers) table
- `fetch_trading_rules()` - Load TradingRules table (optional)
- `fetch_all_reference_tables()` - Load all tables at once

### Caching Strategy
- **Engine caching**: `@st.cache_resource` for SQLAlchemy engine (persists across reruns)
- **Data caching**: `@st.cache_data(ttl=600)` for reference tables (10-minute cache)
- Reduces database load and improves performance

### Error Handling
- Validates reference tables on startup in Optimiser mode
- Admin Dashboard shows status of each table
- Clear error messages if tables are missing or empty

## Database Schema

All reference tables follow the same schema as Excel tabs:

### Banks Table
```sql
CREATE TABLE "Banks" (
    bank_id TEXT PRIMARY KEY,
    bank_name TEXT NOT NULL,
    lpa_name TEXT,
    nca_name TEXT,
    postcode TEXT,
    address TEXT,
    lat FLOAT,
    lon FLOAT
);
```

### Pricing Table
```sql
CREATE TABLE "Pricing" (
    bank_id TEXT NOT NULL,
    habitat_name TEXT NOT NULL,
    contract_size TEXT NOT NULL,
    tier TEXT NOT NULL,
    price FLOAT NOT NULL,
    broader_type TEXT,
    distinctiveness_name TEXT
);
```

### HabitatCatalog Table
```sql
CREATE TABLE "HabitatCatalog" (
    habitat_name TEXT NOT NULL UNIQUE,
    broader_type TEXT NOT NULL,
    distinctiveness_name TEXT NOT NULL,
    "UmbrellaType" TEXT  -- "area", "hedgerow", or "watercourse"
);
```

### Stock Table
```sql
CREATE TABLE "Stock" (
    bank_id TEXT NOT NULL,
    habitat_name TEXT NOT NULL,
    stock_id TEXT NOT NULL,
    quantity_available FLOAT NOT NULL DEFAULT 0,
    available_excl_quotes FLOAT,
    quoted FLOAT DEFAULT 0
);
```

### DistinctivenessLevels Table
```sql
CREATE TABLE "DistinctivenessLevels" (
    distinctiveness_name TEXT NOT NULL UNIQUE,
    level_value FLOAT NOT NULL
);
```

### SRM Table
```sql
CREATE TABLE "SRM" (
    tier TEXT NOT NULL UNIQUE,
    multiplier FLOAT NOT NULL
);
```

### TradingRules Table (Optional)
```sql
CREATE TABLE "TradingRules" (
    rule_name TEXT NOT NULL,
    rule_value TEXT,
    description TEXT
);
```

## Setup Instructions

### 1. Set Up Supabase Database

Run the schema creation script:
```bash
psql -f supabase_schema.sql
```

Or execute the SQL directly in Supabase SQL Editor.

### 2. Migrate Excel Data to Supabase

Use the provided Python script to import Excel data:

```python
import pandas as pd
from sqlalchemy import create_engine

# Read Excel file
excel_file = "path/to/HabitatBackend.xlsx"

# Connect to Supabase
engine = create_engine("postgresql://user:pass@host:5432/database")

# Import each sheet
sheets = ["Banks", "Pricing", "HabitatCatalog", "Stock", 
          "DistinctivenessLevels", "SRM", "TradingRules"]

for sheet_name in sheets:
    try:
        df = pd.read_excel(excel_file, sheet_name=sheet_name)
        df.to_sql(sheet_name, engine, if_exists='append', index=False)
        print(f"✓ Imported {sheet_name}: {len(df)} rows")
    except Exception as e:
        print(f"✗ Error importing {sheet_name}: {e}")
```

### 3. Configure Application

Update `.streamlit/secrets.toml`:
```toml
[database]
url = "postgresql://user:password@host:5432/database"

[auth]
username = "WC0323"
password = "Wimborne"

[admin]
password = "WCAdmin2024"
```

### 4. Install Dependencies

```bash
pip install -r requirements.txt
```

Required packages:
- `sqlalchemy>=2.0` - Database ORM
- `psycopg[binary]>=3.1` - PostgreSQL driver
- `tenacity>=8.0` - Retry logic for database operations

### 5. Run Application

```bash
streamlit run app.py
```

## Migration Checklist

- [ ] Create Supabase database and tables (run `supabase_schema.sql`)
- [ ] Import Excel data to Supabase tables
- [ ] Configure database connection in `.streamlit/secrets.toml`
- [ ] Install updated dependencies (`pip install -r requirements.txt`)
- [ ] Test reference table loading in Admin Dashboard
- [ ] Verify optimizer functionality with real data
- [ ] Remove old Excel files (no longer needed)

## Admin Dashboard Features

The Admin Dashboard now shows:
- **Reference Tables Status**: Shows which tables are populated
- **Table Row Counts**: Displays number of records in each table
- **Error Messages**: Alerts if required tables are empty
- **Submissions Tracking**: (existing functionality)
- **Promoter Management**: (existing functionality)

## Troubleshooting

### "Failed to load reference tables from database"
- Check database connection string in secrets.toml
- Verify Supabase database is running
- Ensure tables exist and are populated

### "Table X is empty or missing"
- Run `supabase_schema.sql` to create tables
- Import data from Excel using migration script
- Check table names are quoted correctly ("Banks" not Banks)

### Import errors with pandas
- Ensure pandas can read your Excel file
- Check sheet names match exactly
- Verify column names in Excel match database schema

## Benefits

1. **Performance**: Database queries with indexes are faster than Excel parsing
2. **Caching**: 10-minute cache reduces database load
3. **Scalability**: Centralized data management for multiple users
4. **Reliability**: ACID transactions and data integrity
5. **Flexibility**: Easy to update data without redeploying app
6. **Security**: Row-level security policies in Supabase
7. **Auditing**: Timestamps on all records (created_at, updated_at)

## Rollback Plan

If needed to rollback to Excel:
1. Keep old Excel files backed up
2. Revert to previous commit before migration
3. Reinstall `openpyxl` and `xlsxwriter`
4. Upload Excel file through UI

However, the new system is designed to be backward-compatible - the data structure and columns match exactly.

## Support

For issues or questions:
- Check Admin Dashboard for table status
- Review Supabase logs for connection errors
- Verify secrets.toml configuration
- Contact system administrator

## Future Enhancements

Potential improvements:
- Admin UI for editing reference tables
- Bulk import/export functionality
- Version control for reference data
- Automated data validation
- API endpoints for external integrations
