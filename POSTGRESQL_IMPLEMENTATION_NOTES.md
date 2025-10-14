# PostgreSQL Implementation Notes

## Overview

This document contains technical implementation notes for the PostgreSQL migration of the SubmissionsDB module.

## Data Type Mapping

### SQLite → PostgreSQL

| SQLite Type | PostgreSQL Type | Notes |
|------------|----------------|-------|
| `INTEGER PRIMARY KEY AUTOINCREMENT` | `SERIAL PRIMARY KEY` | Auto-incrementing integer |
| `TEXT` (timestamps) | `TIMESTAMP` | ISO format stored as native timestamp |
| `TEXT` (JSON) | `JSONB` | Binary JSON with indexing support |
| `TEXT` (arrays) | `TEXT[]` | Native array type |
| `REAL` | `FLOAT` | Floating point numbers |
| `TEXT` (strings) | `TEXT` | Text strings |
| `INTEGER` | `INTEGER` | Integer values |

### JSONB Fields

The following fields are stored as JSONB in PostgreSQL:
- `demand_habitats`: Array of demand habitat objects from DataFrame
- `manual_hedgerow_entries`: Array of manual hedgerow entry objects
- `manual_watercourse_entries`: Array of manual watercourse entry objects
- `allocation_results`: Array of allocation result objects from DataFrame

**Conversion:** DataFrames are converted using `df.to_json(orient='records')` then parsed with `json.loads()` before storing.

### Array Fields

The following fields are stored as TEXT[] arrays:
- `lpa_neighbors`: List of LPA strings
- `nca_neighbors`: List of NCA strings
- `banks_used`: List of bank key strings

**Conversion:** Python lists are passed directly to SQLAlchemy, which handles the conversion to PostgreSQL arrays.

## Query Differences

### Parameterized Queries

**SQLite (old):**
```python
cursor.execute("SELECT * FROM submissions WHERE id = ?", (submission_id,))
```

**PostgreSQL (new):**
```python
conn.execute(text("SELECT * FROM submissions WHERE id = :id"), {"id": submission_id})
```

### Case-Insensitive Search

**SQLite:** Uses `LIKE` (case-sensitive on some collations)
**PostgreSQL:** Uses `ILIKE` (always case-insensitive)

```sql
-- Old
WHERE client_name LIKE ?

-- New
WHERE client_name ILIKE :client_name
```

### Returning Clause

PostgreSQL supports `RETURNING` for getting auto-generated IDs:

```sql
INSERT INTO submissions (...) VALUES (...) RETURNING id
```

This is more efficient than using `cursor.lastrowid`.

## Transaction Management

### Explicit Transactions

All write operations use explicit transaction management:

```python
with engine.connect() as conn:
    trans = conn.begin()
    try:
        # Perform operations
        trans.commit()
    except Exception as e:
        trans.rollback()
        raise
```

### Automatic Retries

Write operations are decorated with `@retry`:

```python
@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=1, max=10),
    retry=retry_if_exception_type((Exception,)),
    reraise=True
)
def store_submission(...):
    # Implementation
```

**Retry Parameters:**
- Maximum attempts: 3
- Wait time: Exponential backoff (1s, 2s, 4s, ...)
- Min wait: 1 second
- Max wait: 10 seconds

## Connection Pooling

### SQLAlchemy Engine Configuration

```python
create_engine(
    db_url,
    pool_pre_ping=True,      # Verify connections before use
    pool_size=5,             # Keep 5 connections in pool
    max_overflow=10,         # Allow up to 10 additional connections
    pool_recycle=3600,       # Recycle connections after 1 hour
    echo=False,              # Set to True for SQL debugging
)
```

### Connection Management

- Connections are automatically managed by SQLAlchemy
- `with engine.connect() as conn:` ensures proper cleanup
- No need for explicit connection closing in most cases
- Pool handles connection reuse and cleanup

## Indexes

### Automatically Created Indexes

1. **submissions table:**
   - `idx_submissions_date`: On `submission_date DESC` for sorting
   - `idx_submissions_client`: On `client_name` for filtering
   - `idx_submissions_lpa`: On `target_lpa` for filtering
   - `idx_submissions_nca`: On `target_nca` for filtering

2. **allocation_details table:**
   - `idx_allocation_details_submission`: On `submission_id` for joins

3. **introducers table:**
   - `idx_introducers_name`: On `name` for lookups

### Adding Custom Indexes

To add indexes for JSONB fields if needed:

```sql
-- Index on a specific JSONB field
CREATE INDEX idx_demand_habitats_gin ON submissions USING GIN (demand_habitats);

-- Index for specific JSONB key
CREATE INDEX idx_allocation_bank ON submissions 
USING GIN ((allocation_results -> 'BANK_KEY'));
```

## Schema Initialization

### Idempotent Schema Creation

All `CREATE TABLE` and `CREATE INDEX` statements use `IF NOT EXISTS` to ensure idempotency:

```sql
CREATE TABLE IF NOT EXISTS submissions (...);
CREATE INDEX IF NOT EXISTS idx_submissions_date ON submissions(...);
```

This allows the application to:
- Run multiple times without errors
- Work with existing databases
- Support rolling deployments

### Foreign Key Constraints

Foreign keys include `ON DELETE CASCADE`:

```sql
FOREIGN KEY (submission_id) REFERENCES submissions(id) ON DELETE CASCADE
```

This ensures:
- Automatic cleanup of child records
- Referential integrity
- No orphaned allocation_details records

## Read Operations

### Using pandas.read_sql_query

All read operations use `pandas.read_sql_query` for consistency:

```python
engine = self._get_connection()
with engine.connect() as conn:
    df = pd.read_sql_query(query, conn, params=params)
return df
```

**Note:** Pandas automatically handles PostgreSQL array and JSONB types, converting them to Python types.

### Row Mapping

When fetching single rows, use `row._mapping` to convert to dict:

```python
result = conn.execute(text("SELECT * FROM submissions WHERE id = :id"), {"id": id})
row = result.fetchone()
if row:
    return dict(row._mapping)
```

## Data Migration Considerations

### Array Handling

When migrating from SQLite:
- SQLite arrays are stored as JSON strings: `'["LPA1", "LPA2"]'`
- PostgreSQL arrays are native: `{"LPA1", "LPA2"}`
- Migration requires parsing JSON strings and storing as arrays

### JSONB Handling

When migrating from SQLite:
- SQLite JSONB is stored as JSON strings
- PostgreSQL JSONB is binary format
- Migration requires parsing JSON strings and storing as JSONB
- No changes to application code needed (handled automatically)

### Timestamp Handling

When migrating from SQLite:
- SQLite stores ISO format strings: `'2024-01-15T10:30:00'`
- PostgreSQL stores native timestamps
- Migration should parse ISO strings to datetime objects
- Use: `datetime.fromisoformat(sqlite_timestamp)`

## Error Handling

### Common Errors

1. **Connection Errors:**
   - Caught by retry decorator
   - Up to 3 retry attempts
   - Exponential backoff between retries

2. **Transaction Errors:**
   - Automatic rollback on exceptions
   - Original exception re-raised after rollback
   - No partial commits

3. **Schema Errors:**
   - Typically occur on first run if database doesn't exist
   - Should be caught and logged with clear error message
   - User should create database before running app

### Health Checks

The `db_healthcheck()` method provides basic connectivity testing:

```python
db = SubmissionsDB()
if db.db_healthcheck():
    print("✓ Database is accessible")
else:
    print("✗ Database connection failed")
```

## Performance Considerations

### Query Optimization

1. **Use Indexes:** All common filter fields are indexed
2. **Limit Results:** Use `LIMIT` clause for large result sets
3. **Parameterized Queries:** Always use parameters to enable query plan caching
4. **Connection Pooling:** Reuse connections for better performance

### Bulk Operations

For inserting many records, consider using batch operations:

```python
# Instead of multiple individual inserts
for row in large_dataframe.iterrows():
    conn.execute(...)  # Slow

# Use bulk insert
conn.execute(text("INSERT INTO ... VALUES ..."), 
             [{"col1": val1, "col2": val2} for ... in ...])  # Faster
```

Current implementation uses individual inserts for allocation_details, which is acceptable for typical submission sizes (< 100 rows).

### JSONB Queries

If you need to query JSONB fields frequently:

```sql
-- Query JSONB field
SELECT * FROM submissions WHERE demand_habitats @> '[{"habitat": "Grassland"}]'::jsonb;

-- Extract JSONB key
SELECT allocation_results->>'BANK_KEY' FROM submissions;

-- Add GIN index for JSONB queries
CREATE INDEX idx_demand_habitats_gin ON submissions USING GIN (demand_habitats);
```

## Security Considerations

### SQL Injection Prevention

All queries use parameterized statements:

```python
# Safe - parameterized
conn.execute(text("SELECT * FROM submissions WHERE id = :id"), {"id": user_input})

# NEVER do this - vulnerable to SQL injection
conn.execute(text(f"SELECT * FROM submissions WHERE id = {user_input}"))
```

### Connection String Security

- Never hardcode database credentials
- Use Streamlit secrets for configuration
- Never commit secrets.toml to version control
- Use environment variables in production

### SSL/TLS

For production deployments, enable SSL:

```toml
[database]
url = "postgresql://user:pass@host:5432/db?sslmode=require"
```

Options:
- `sslmode=disable`: No SSL (development only)
- `sslmode=require`: Require SSL but don't verify certificate
- `sslmode=verify-ca`: Require SSL and verify CA
- `sslmode=verify-full`: Require SSL and verify hostname

## Testing

### Unit Testing

For unit testing, consider:
1. Using a test database instance
2. Using database transactions that rollback after tests
3. Mocking the database connection for fast tests

### Integration Testing

For integration testing:
1. Use Docker PostgreSQL container
2. Run schema initialization
3. Test all CRUD operations
4. Verify transaction handling
5. Test retry mechanisms with artificial failures

### Validation Script

Use `test_database_validation.py` to verify:
- Correct imports
- Method signatures
- Class structure
- No syntax errors

## Monitoring and Logging

### Connection Monitoring

Monitor connection pool usage:

```python
engine = DatabaseConnection.get_engine()
pool = engine.pool
print(f"Pool size: {pool.size()}")
print(f"Checked out: {pool.checkedout()}")
print(f"Overflow: {pool.overflow()}")
```

### Query Logging

Enable SQLAlchemy echo for debugging:

```python
create_engine(db_url, echo=True)  # Logs all SQL queries
```

### Error Logging

All errors are logged and re-raised:

```python
import logging
logger = logging.getLogger(__name__)
logger.error(f"Database error: {e}")
```

## Maintenance

### Database Backups

Regular backups are critical:

```bash
# Daily backup
pg_dump -U optimiser_user optimiser_db > backup_$(date +%Y%m%d).sql

# Automated backup script
0 2 * * * /usr/bin/pg_dump -U optimiser_user optimiser_db | gzip > /backups/optimiser_$(date +\%Y\%m\%d).sql.gz
```

### Database Vacuum

PostgreSQL requires periodic vacuuming:

```sql
-- Analyze tables for query optimization
ANALYZE submissions;
ANALYZE allocation_details;

-- Full vacuum (requires exclusive lock)
VACUUM FULL submissions;

-- Enable auto-vacuum (recommended)
ALTER TABLE submissions SET (autovacuum_enabled = true);
```

### Index Maintenance

Monitor and rebuild indexes if needed:

```sql
-- Check index size
SELECT indexname, pg_size_pretty(pg_relation_size(indexname::regclass))
FROM pg_indexes WHERE tablename = 'submissions';

-- Rebuild index if needed
REINDEX INDEX idx_submissions_date;
```

## Future Enhancements

Potential improvements for future versions:

1. **Alembic Migrations:** Add database migration management
2. **Read Replicas:** Support read-only replicas for scaling
3. **Async Operations:** Use asyncpg for async database operations
4. **Caching:** Add Redis cache for frequently accessed data
5. **Partitioning:** Partition submissions table by date for large datasets
6. **Materialized Views:** Add pre-computed views for complex queries
7. **Full-Text Search:** Add PostgreSQL full-text search for text fields
8. **Audit Logging:** Track all changes with triggers or audit tables

## Troubleshooting

### Common Issues and Solutions

1. **"relation does not exist"**
   - Solution: Run `_init_database()` or restart app
   
2. **"column does not exist"**
   - Solution: Schema mismatch, drop and recreate tables
   
3. **"permission denied"**
   - Solution: Grant permissions: `GRANT ALL ON SCHEMA public TO user;`
   
4. **"too many connections"**
   - Solution: Reduce pool_size or increase max_connections in PostgreSQL
   
5. **"SSL connection required"**
   - Solution: Add `?sslmode=require` to connection string or disable SSL requirement

### Debug Mode

Enable debug logging:

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

This will show:
- All SQL queries
- Connection pool events
- Transaction boundaries
- Retry attempts

## References

- [SQLAlchemy Core Documentation](https://docs.sqlalchemy.org/en/20/core/)
- [PostgreSQL Documentation](https://www.postgresql.org/docs/)
- [psycopg3 Documentation](https://www.psycopg.org/psycopg3/docs/)
- [Tenacity Documentation](https://tenacity.readthedocs.io/)
- [Pandas SQL Documentation](https://pandas.pydata.org/docs/reference/api/pandas.read_sql_query.html)
