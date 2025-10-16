# Quick Start Guide - Supabase Migration

This guide helps you quickly migrate from Excel-based backend to Supabase Postgres.

## Prerequisites

- Supabase account (or any PostgreSQL database)
- Existing Excel workbook with reference data
- Python 3.8+ with pip

## Step-by-Step Setup

### 1. Set Up Database Tables

**Option A: Using Supabase Dashboard**
1. Go to your Supabase project
2. Navigate to SQL Editor
3. Copy contents of `supabase_schema.sql`
4. Execute the SQL script
5. Verify tables were created in Table Editor

**Option B: Using Command Line**
```bash
psql -h your-host -U your-user -d your-database -f supabase_schema.sql
```

### 2. Import Your Excel Data

```bash
# Install dependencies if needed
pip install pandas openpyxl sqlalchemy psycopg2-binary streamlit

# Run the import script
python import_excel_to_supabase.py path/to/your/HabitatBackend.xlsx
```

The script will:
- Connect to your database (using secrets.toml)
- Import all sheets to corresponding tables
- Verify the import was successful

### 3. Configure Database Connection

Create or update `.streamlit/secrets.toml`:

```toml
[database]
# For Supabase, use the connection string from:
# Project Settings > Database > Connection String > URI
url = "postgresql://postgres:[YOUR-PASSWORD]@db.[PROJECT-REF].supabase.co:5432/postgres"

[auth]
username = "WC0323"
password = "Wimborne"

[admin]
password = "WCAdmin2024"
```

**Finding your Supabase connection string:**
1. Go to Project Settings
2. Click on "Database" in sidebar
3. Find "Connection String" section
4. Copy the URI format
5. Replace `[YOUR-PASSWORD]` with your actual database password

### 4. Install Updated Dependencies

```bash
pip install -r requirements.txt
```

This will install:
- `sqlalchemy>=2.0` - Database toolkit
- `psycopg[binary]>=3.1` - PostgreSQL driver
- `tenacity>=8.0` - Retry logic

Note: `openpyxl` and `xlsxwriter` are no longer needed!

### 5. Run the Application

```bash
streamlit run app.py
```

### 6. Verify Everything Works

1. **Check Admin Dashboard**
   - Switch to "Admin Dashboard" mode
   - Enter admin password
   - Check "Reference Tables Status" section
   - All tables should show ✅ with row counts

2. **Test Optimizer**
   - Switch back to "Optimiser" mode
   - Try creating a quote
   - Verify habitats load correctly
   - Run optimization

## Troubleshooting

### "Failed to load reference tables from database"

**Check database connection:**
```bash
python -c "from db import DatabaseConnection; print('✓ Connected' if DatabaseConnection.db_healthcheck() else '✗ Failed')"
```

**Common fixes:**
- Verify database URL in secrets.toml
- Check database password is correct
- Ensure Supabase project is not paused
- Check firewall/network connectivity

### "Table X is empty or missing"

**Verify tables exist:**
```bash
python -c "from repo import check_required_tables_not_empty; print(check_required_tables_not_empty())"
```

**Common fixes:**
- Run `supabase_schema.sql` to create tables
- Re-run `import_excel_to_supabase.py` to import data
- Check table names are quoted correctly: `"Banks"` not `Banks`

### Import script fails

**Common issues:**
- Excel file path is incorrect
- Sheet names don't match (case-sensitive)
- Missing pandas or openpyxl: `pip install pandas openpyxl`
- Database connection string wrong

### "No module named 'psycopg'"

```bash
pip install psycopg[binary]
```

### "No module named 'sqlalchemy'"

```bash
pip install sqlalchemy>=2.0
```

## Validation Checklist

- [ ] Database tables created (run supabase_schema.sql)
- [ ] Excel data imported (run import script)
- [ ] Database URL configured in secrets.toml
- [ ] Dependencies installed (pip install -r requirements.txt)
- [ ] App starts without errors (streamlit run app.py)
- [ ] Admin Dashboard shows all tables populated
- [ ] Optimizer can load habitats
- [ ] Can create and optimize quotes
- [ ] Can save quotes to database

## What Changed?

### Before (Excel)
```python
# Upload Excel file through UI
uploaded = st.file_uploader("Upload .xlsx")
backend = load_backend(uploaded.getvalue())
```

### After (Supabase)
```python
# Load from database (cached for 10 minutes)
backend = load_backend()  # Uses repo.fetch_all_reference_tables()
```

### Benefits
- ✅ Faster loading (cached + indexed queries)
- ✅ Centralized data management
- ✅ No file uploads needed
- ✅ Automatic validation
- ✅ Better error messages
- ✅ Multi-user support

## Performance

- **First load**: ~2-3 seconds (fetches from database)
- **Subsequent loads**: Instant (cached for 10 minutes)
- **Database queries**: Optimized with indexes
- **Connection pooling**: Built-in with SQLAlchemy

## Next Steps

Once everything is working:
1. Remove old Excel files (no longer needed)
2. Set up regular backups of Supabase database
3. Consider setting up staging/production environments
4. Review Row Level Security policies in Supabase

## Need Help?

- Check `SUPABASE_MIGRATION.md` for detailed documentation
- Review `supabase_schema.sql` for table structures
- Look at `repo.py` for data access layer
- Check Supabase logs for database errors

## Support

For issues:
1. Check Admin Dashboard for table status
2. Verify database connection with healthcheck
3. Review application logs
4. Contact administrator

---

**Migration completed successfully?** 🎉

You can now delete:
- Old Excel backend files
- `openpyxl` and `xlsxwriter` packages (optional)
- Any Excel-related documentation
