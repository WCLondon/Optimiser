# Supabase Setup Guide for BNG Optimiser

## Quick Setup for Supabase PostgreSQL

### Step 1: Get Your Supabase Connection Details

You need the following information from your Supabase project:

1. **Host**: Found in your Supabase project settings (Database → Connection Info)
   - Usually looks like: `db.xxxxxxxxxxxxx.supabase.co`
   
2. **Database Name**: Usually `postgres` (default)

3. **Username**: Usually `postgres` (default)

4. **Password**: The password you provided: `#EYeCqUUpHq8EVX`

5. **Port**: Usually `5432` (default for PostgreSQL)

### Step 2: Get Your Connection String from Supabase

**Option A: Use Supabase Dashboard (Recommended)**

1. Go to your Supabase project dashboard
2. Click on **Settings** (gear icon) in the sidebar
3. Click on **Database**
4. Scroll down to **Connection string**
5. Select **URI** format
6. Copy the connection string - it will look like:
   ```
   postgresql://postgres:[YOUR-PASSWORD]@db.xxxxxxxxxxxxx.supabase.co:5432/postgres
   ```
7. Replace `[YOUR-PASSWORD]` with: `#EYeCqUUpHq8EVX`

**Option B: Find Connection Details Manually**

If you see the connection details separately:
1. Host: `db.xxxxxxxxxxxxx.supabase.co`
2. Database: `postgres`
3. Port: `5432`
4. User: `postgres`
5. Password: `#EYeCqUUpHq8EVX`

Then build the URL as:
```
postgresql://postgres:#EYeCqUUpHq8EVX@db.xxxxxxxxxxxxx.supabase.co:5432/postgres
```

**Note:** The `#` character in the password needs to be URL-encoded as `%23`:
```
postgresql://postgres:%23EYeCqUUpHq8EVX@db.xxxxxxxxxxxxx.supabase.co:5432/postgres
```

### Step 3: Create the secrets.toml File

1. **Create the directory** (if it doesn't exist):
   ```bash
   mkdir -p .streamlit
   ```

2. **Create the file** `.streamlit/secrets.toml` with this content:

   ```toml
   [database]
   # Replace the URL below with your actual Supabase connection string
   # Remember to URL-encode the # character in your password as %23
   url = "postgresql://postgres:%23EYeCqUUpHq8EVX@db.xxxxxxxxxxxxx.supabase.co:5432/postgres"
   
   [auth]
   username = "WC0323"
   password = "Wimborne"
   
   [admin]
   password = "WCAdmin2024"
   ```

3. **Replace** `db.xxxxxxxxxxxxx.supabase.co` with your actual Supabase host

### Step 4: Find Your Supabase Host

To find your Supabase host:

1. Go to https://supabase.com/dashboard
2. Select your project
3. Go to **Settings** → **Database**
4. Look for **Connection Info** section
5. The **Host** field will show something like: `db.abcdefghijklmnop.supabase.co`

### Step 5: Example Configuration

Here's a complete example (replace with your actual values):

```toml
[database]
url = "postgresql://postgres:%23EYeCqUUpHq8EVX@db.abcdefghijklmnop.supabase.co:5432/postgres"

[auth]
username = "WC0323"
password = "Wimborne"

[admin]
password = "WCAdmin2024"
```

### Important Notes

1. **URL Encoding**: The `#` character in your password (`#EYeCqUUpHq8EVX`) must be encoded as `%23` in the connection URL
   - Wrong: `postgresql://postgres:#EYeCqUUpHq8EVX@...`
   - Correct: `postgresql://postgres:%23EYeCqUUpHq8EVX@...`

2. **Port**: Supabase uses port `5432` (standard PostgreSQL port)

3. **SSL**: Supabase requires SSL connections, but this is handled automatically by psycopg

4. **Database Name**: The default database name is `postgres`

### Troubleshooting

**Error: "Failed to read database URL from secrets"**
- Make sure `.streamlit/secrets.toml` exists
- Check that the file is in the correct location (same directory as `app.py`)

**Error: "Connection refused" or "could not connect"**
- Verify your Supabase host is correct
- Check that your project is active (not paused)
- Ensure you're using the correct password with URL encoding

**Error: "password authentication failed"**
- Double-check your password
- Ensure the `#` is encoded as `%23`
- Verify you're using the correct username (usually `postgres`)

### Testing Your Connection

Once configured, test the connection by running:

```bash
python -c "from database import SubmissionsDB; db = SubmissionsDB(); print('✓ Connected!' if db.db_healthcheck() else '✗ Connection failed')"
```

Or simply start the app:

```bash
streamlit run app.py
```

If the connection is successful, the database schema will be created automatically on first run.

### Security Notes

- **Never commit** `.streamlit/secrets.toml` to Git (it's already in `.gitignore`)
- Keep your password secure
- Consider using environment variables for production deployments
- Rotate passwords regularly

## Need More Help?

If you're still having issues:

1. Check the Supabase documentation: https://supabase.com/docs/guides/database/connecting-to-postgres
2. Verify your project is active in the Supabase dashboard
3. Make sure you have the correct connection pooler settings (use "Transaction" mode for most cases)
4. Check if you need to enable connection pooling in Supabase (Settings → Database → Connection Pooling)

## Quick Reference: Common Connection String Formats

**Standard format:**
```
postgresql://username:password@host:port/database
```

**With URL-encoded password:**
```
postgresql://username:%23EYeCqUUpHq8EVX@host:port/database
```

**Supabase example:**
```
postgresql://postgres:%23EYeCqUUpHq8EVX@db.abcdefghijklmnop.supabase.co:5432/postgres
```

**With SSL mode (optional):**
```
postgresql://postgres:%23EYeCqUUpHq8EVX@db.abcdefghijklmnop.supabase.co:5432/postgres?sslmode=require
```
