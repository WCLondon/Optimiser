# PostgreSQL Quick Start Guide

This guide will help you quickly set up PostgreSQL for the BNG Optimiser application.

## Option 1: Local PostgreSQL (Development)

### Install PostgreSQL

**macOS:**
```bash
brew install postgresql@14
brew services start postgresql@14
```

**Ubuntu/Debian:**
```bash
sudo apt update
sudo apt install postgresql postgresql-contrib
sudo systemctl start postgresql
```

**Windows:**
Download and install from [postgresql.org](https://www.postgresql.org/download/windows/)

### Create Database

```bash
# Login as postgres user
sudo -u postgres psql

# Create database and user
CREATE DATABASE optimiser_db;
CREATE USER optimiser_user WITH PASSWORD 'your_secure_password';
GRANT ALL PRIVILEGES ON DATABASE optimiser_db TO optimiser_user;

# Grant schema permissions (PostgreSQL 15+)
\c optimiser_db
GRANT ALL ON SCHEMA public TO optimiser_user;

# Exit
\q
```

### Configure Secrets

Create `.streamlit/secrets.toml`:
```toml
[database]
url = "postgresql://optimiser_user:your_secure_password@localhost:5432/optimiser_db"

[auth]
username = "WC0323"
password = "Wimborne"

[admin]
password = "WCAdmin2024"
```

### Test Connection

```bash
# Test with psql
psql postgresql://optimiser_user:your_secure_password@localhost:5432/optimiser_db

# Or with Python
python -c "from database import SubmissionsDB; db = SubmissionsDB(); print('✓ Connected' if db.db_healthcheck() else '✗ Failed')"
```

## Option 2: Cloud PostgreSQL (Production)

### Supabase (Recommended for Quick Setup)

Supabase provides a free PostgreSQL database with a generous free tier.

1. **Create Supabase Project:**
   - Go to https://supabase.com
   - Sign up or log in
   - Click "New Project"
   - Enter project details and password
   - Wait for project to provision (~2 minutes)

2. **Get Connection Details:**
   - Go to **Settings** → **Database**
   - Find the **Connection Info** section
   - Note your **Host** (e.g., `db.xxxxxxxxxxxxx.supabase.co`)
   - Default **Database**: `postgres`
   - Default **User**: `postgres`
   - **Port**: `5432`
   - **Password**: The one you set during project creation

3. **Build Connection String:**
   ```
   postgresql://postgres:YOUR_PASSWORD@db.xxxxxxxxxxxxx.supabase.co:5432/postgres
   ```
   
   **Important:** If your password contains special characters like `#`, URL-encode them:
   - `#` → `%23`
   - `@` → `%40`
   - `$` → `%24`
   - `&` → `%26`
   
   Example with password `#EYeCqUUpHq8EVX`:
   ```
   postgresql://postgres:%23EYeCqUUpHq8EVX@db.xxxxxxxxxxxxx.supabase.co:5432/postgres
   ```

4. **Update secrets.toml:**
   ```toml
   [database]
   url = "postgresql://postgres:%23EYeCqUUpHq8EVX@db.xxxxxxxxxxxxx.supabase.co:5432/postgres"
   
   [auth]
   username = "WC0323"
   password = "Wimborne"
   
   [admin]
   password = "WCAdmin2024"
   ```

5. **Test Connection:**
   ```bash
   python -c "from database import SubmissionsDB; db = SubmissionsDB(); print('✓ Connected' if db.db_healthcheck() else '✗ Failed')"
   ```

**See [SUPABASE_SETUP.md](SUPABASE_SETUP.md) for detailed Supabase setup instructions.**

### AWS RDS

1. **Create RDS Instance:**
   - Go to AWS RDS Console
   - Click "Create database"
   - Choose PostgreSQL (version 14 or higher)
   - Select instance size (db.t3.micro for testing)
   - Set master username and password
   - Configure VPC and security groups
   - Create database

2. **Configure Security Group:**
   - Allow inbound traffic on port 5432 from your IP
   - For production, use VPC peering or private subnets

3. **Get Connection String:**
   - Endpoint: `mydb.abc123.us-east-1.rds.amazonaws.com`
   - Port: `5432`
   - Database: `postgres` (default) or create new database

4. **Update secrets.toml:**
   ```toml
   [database]
   url = "postgresql://username:password@mydb.abc123.us-east-1.rds.amazonaws.com:5432/optimiser_db"
   ```

### Google Cloud SQL

1. **Create Cloud SQL Instance:**
   ```bash
   gcloud sql instances create optimiser-db \
     --database-version=POSTGRES_14 \
     --tier=db-f1-micro \
     --region=us-central1
   ```

2. **Create Database:**
   ```bash
   gcloud sql databases create optimiser_db --instance=optimiser-db
   ```

3. **Create User:**
   ```bash
   gcloud sql users create optimiser_user \
     --instance=optimiser-db \
     --password=your_password
   ```

4. **Get Connection String:**
   - Use Cloud SQL Proxy for local development
   - Or use public IP with SSL

### Heroku Postgres

1. **Add Postgres Add-on:**
   ```bash
   heroku addons:create heroku-postgresql:mini
   ```

2. **Get Database URL:**
   ```bash
   heroku config:get DATABASE_URL
   ```

3. **Update secrets.toml:**
   ```toml
   [database]
   url = "postgresql://user:pass@ec2-XX-XX-XX-XX.compute-1.amazonaws.com:5432/dbname"
   ```

### DigitalOcean Managed Database

1. **Create Database Cluster** in DO Control Panel
2. **Download CA Certificate** (if using SSL)
3. **Get Connection String** from cluster details
4. **Update secrets.toml** with connection parameters

## Option 3: Docker PostgreSQL (Quick Setup)

### Run PostgreSQL Container

```bash
docker run --name optimiser-postgres \
  -e POSTGRES_USER=optimiser_user \
  -e POSTGRES_PASSWORD=secure_password \
  -e POSTGRES_DB=optimiser_db \
  -p 5432:5432 \
  -d postgres:14
```

### Configure Secrets

```toml
[database]
url = "postgresql://optimiser_user:secure_password@localhost:5432/optimiser_db"
```

### Manage Container

```bash
# Stop
docker stop optimiser-postgres

# Start
docker start optimiser-postgres

# View logs
docker logs optimiser-postgres

# Access psql
docker exec -it optimiser-postgres psql -U optimiser_user -d optimiser_db
```

## Verify Setup

### 1. Check PostgreSQL is Running

```bash
# Check if PostgreSQL is listening
netstat -an | grep 5432

# Or with lsof (macOS/Linux)
lsof -i :5432
```

### 2. Test Connection

```bash
# With psql
psql "postgresql://optimiser_user:password@localhost:5432/optimiser_db" -c "SELECT version();"

# With Python
python test_database_validation.py
```

### 3. Run Application

```bash
streamlit run app.py
```

## Common Issues

### Connection Refused

**Problem:** Can't connect to PostgreSQL

**Solutions:**
- Verify PostgreSQL is running: `systemctl status postgresql` (Linux) or `brew services list` (macOS)
- Check if port 5432 is open: `telnet localhost 5432`
- Review `postgresql.conf` for listen_addresses setting
- Check `pg_hba.conf` for authentication rules

### Authentication Failed

**Problem:** Password authentication failed

**Solutions:**
- Verify username and password in secrets.toml
- Check PostgreSQL user exists: `\du` in psql
- Review `pg_hba.conf` for authentication method (should be `md5` or `scram-sha-256`)
- Reload PostgreSQL after config changes: `pg_ctl reload`

### Database Does Not Exist

**Problem:** Database "optimiser_db" does not exist

**Solutions:**
- Create database: `createdb -U postgres optimiser_db`
- Or via psql: `CREATE DATABASE optimiser_db;`
- Verify database exists: `\l` in psql

### Permission Denied

**Problem:** Permission denied for schema public

**Solutions (PostgreSQL 15+):**
```sql
GRANT ALL ON SCHEMA public TO optimiser_user;
GRANT CREATE ON SCHEMA public TO optimiser_user;
```

## Security Best Practices

1. **Use Strong Passwords:** Generate with `openssl rand -base64 32`
2. **Limit Network Access:** Use firewall rules to restrict connections
3. **Enable SSL:** Add `?sslmode=require` to connection string
4. **Regular Backups:** Set up automated backups
5. **Monitor Connections:** Review logs regularly
6. **Rotate Credentials:** Change passwords periodically

## Performance Tuning

For better performance, adjust PostgreSQL settings:

```sql
-- Increase connection limit if needed
ALTER SYSTEM SET max_connections = 100;

-- Adjust shared buffers (25% of RAM)
ALTER SYSTEM SET shared_buffers = '256MB';

-- Reload configuration
SELECT pg_reload_conf();
```

## Backup and Restore

### Backup

```bash
# Full database backup
pg_dump -U optimiser_user -h localhost optimiser_db > backup.sql

# Compressed backup
pg_dump -U optimiser_user -h localhost optimiser_db | gzip > backup.sql.gz

# Backup with custom format (faster restore)
pg_dump -U optimiser_user -h localhost -Fc optimiser_db > backup.dump
```

### Restore

```bash
# From SQL file
psql -U optimiser_user -h localhost optimiser_db < backup.sql

# From compressed SQL
gunzip -c backup.sql.gz | psql -U optimiser_user -h localhost optimiser_db

# From custom format
pg_restore -U optimiser_user -h localhost -d optimiser_db backup.dump
```

## Next Steps

1. ✅ PostgreSQL installed and running
2. ✅ Database and user created
3. ✅ secrets.toml configured
4. ✅ Connection tested
5. 📋 Run application: `streamlit run app.py`
6. 📋 Set up automated backups
7. 📋 Configure monitoring
8. 📋 Review security settings

For more details, see [POSTGRESQL_MIGRATION.md](POSTGRESQL_MIGRATION.md)
