# Streamlit Promoter Form - Quick Start Guide

## Overview

**Single Streamlit app** with login page for all promoters. Each promoter logs in with their name and password from the `introducers` database table.

## Key Features

✅ **Single app deployment** - One app for all promoters  
✅ **Database authentication** - Username and password from introducers table  
✅ **Automatic tracking** - Submissions tagged with logged-in promoter  
✅ **Simple deployment** - Just one Streamlit instance needed  
✅ **Dynamic access** - Any promoter in the introducers table can login  

## Quick Start

### Run the App

```bash
./run_promoter_app.sh
# Or manually:
streamlit run promoter_app.py --server.port 8502
```

Access at: http://localhost:8502

### Login

**How it works:**
- **Username:** From `name` column in `introducers` table
- **Password:** From `password` column in `introducers` table

The app dynamically loads all promoters from the database.

## Features

### Login Page

✅ Shows available promoters from database  
✅ Simple username/password authentication  
✅ Password hint displayed  
✅ Clear error messages  

### Quote Form (After Login)

✅ **Single-page form** with clean, modern UI  
✅ **Promoter badge** shows who is logged in  
✅ **File upload** for BNG metric (.xlsx files)  
✅ **Form validation** (email, location, consent)  
✅ **Metric reading** using existing metric_reader module  
✅ **Quote calculation** (simplified for now)  
✅ **Threshold logic** (< £20k = auto-quote, ≥ £20k = manual review)  
✅ **Database persistence** with promoter tracking  
✅ **Logout button** in sidebar  

### Database Tracking

All submissions include:
- `promoter_name`: Logged-in promoter (e.g., "EPT")
- `client_name`: From email or form
- `reference_number`: Auto-generated or from form
- `total_cost`: Calculated quote
- All other standard submission fields

Query submissions by promoter:
```sql
SELECT 
    id, submission_date, client_name, 
    promoter_name, total_cost, site_location
FROM submissions 
WHERE promoter_name = 'EPT'
ORDER BY submission_date DESC;
```

## How Promoters Are Loaded

The app queries the database for available promoters:

```sql
SELECT DISTINCT 
    name,
    password,
    discount_type,
    discount_value
FROM introducers 
WHERE name IS NOT NULL 
AND name != ''
ORDER BY name
```

**Database Schema:**
```
introducers table:
- name (TEXT) - Promoter username
- password (TEXT) - Promoter password
- discount_type (TEXT) - Discount type (e.g., 'no_discount', 'tier_up')
- discount_value (NUMERIC) - Discount value
```

If the query fails (e.g., table doesn't exist), it falls back to default promoters:
- ETP
- Arbtech
- Cypher

## Adding New Promoters

### Step 1: Add password column (if not exists)

If the `introducers` table doesn't have a password column yet, run:

```sql
-- Add password column
ALTER TABLE introducers 
ADD COLUMN IF NOT EXISTS password TEXT;

-- Set default passwords for existing records
UPDATE introducers 
SET password = name || '1' 
WHERE password IS NULL OR password = '';
```

### Step 2: Add new promoter

```sql
-- Add a new promoter with password
INSERT INTO introducers (
    name,
    password,
    discount_type,
    discount_value
) VALUES (
    'NewPromoter',
    'secure_password_here',
    'no_discount',
    0
);
```

Then the promoter can login with:
- Username: `NewPromoter`
- Password: `secure_password_here`

## Testing

### Test Login Flow

✅ **Single-page form** with clean, modern UI  
✅ **File upload** for BNG metric (.xlsx files)  
✅ **Form validation** (email, location, consent)  
✅ **Metric reading** using existing metric_reader module  
✅ **Quote calculation** (simplified for now)  
✅ **Threshold logic** (< £20k = auto-quote, ≥ £20k = manual review)  
✅ **Database persistence** using existing SubmissionsDB  
✅ **Success/error handling** with clear messaging  

### Form Fields

**Required:**
- Contact Email
- BNG Metric File (.xlsx)
- Consent checkbox
- At least one of: Site Address OR Postcode

**Optional:**
- Client Reference
- Additional Notes

### User Flow

1. **User visits form** (e.g., EPT form at localhost:8502)
2. **Fills in details** and uploads metric file
3. **Submits form**
4. **System processes:**
   - Reads metric file
   - Calculates quote total
   - Saves to database
   - Applies threshold logic
5. **User sees result:**
   - Auto-quote (< £20k): Success message + PDF download button (placeholder for now)
   - Manual review (≥ £20k): Success message + "team will contact you" notice

## Database Integration

Submissions are saved using the existing `SubmissionsDB` class:

- Table: `submissions` (existing table)
- Fields populated:
  - `client_name`: Derived from email
  - `reference_number`: Auto-generated or from form
  - `site_location`: Address or postcode
  - `demand_habitats`: Parsed from metric
  - `total_cost`: Calculated quote total
  - `allocation_results`: Full metric data
  - `promoter_name`: From command line argument

Query submissions:
```sql
SELECT 
    id, submission_date, client_name, 
    promoter_name, total_cost, site_location
FROM submissions 
WHERE promoter_name = 'EPT'
ORDER BY submission_date DESC;
```

## Testing

### Test with Sample Data
1. **Start the app:**
   ```bash
   ./run_promoter_app.sh
   ```

2. **Login page should appear**
   - Shows list of available promoters
   - Has username and password fields
   - Shows example (EPT → EPT1)

3. **Test login:**
   - Username: `EPT`
   - Password: `EPT1`
   - Should see success message and redirect to form

4. **Test invalid login:**
   - Username: `WrongName`
   - Password: `wrong`
   - Should see error message with hint

### Test Quote Submission

1. **After successful login, fill in form:**
   - Email: test@example.com
   - Postcode: SW1A 1AA
   - Upload: Any BNG metric .xlsx file
   - Check consent box

2. **Submit and verify:**
   - Should see success message
   - Check database:
     ```sql
     SELECT * FROM submissions 
     WHERE promoter_name = 'EPT' 
     ORDER BY submission_date DESC LIMIT 1;
     ```
   - Verify promoter_name is "EPT"

### Test Logout

1. Click "🚪 Logout" button in sidebar
2. Should redirect to login page
3. Session should be cleared

## Deployment

### Single Instance Deployment

Since this is now **one app for all promoters**, you only need one deployment:

#### Option 1: Streamlit Cloud

1. Deploy to Streamlit Cloud
2. Get URL: `bng-promoters.streamlit.app`
3. Share with all promoters
4. Each logs in with their credentials

#### Option 2: Self-Hosted (Systemd)

`/etc/systemd/system/bng-promoter-app.service`:
```ini
[Unit]
Description=BNG Promoter Quote System
After=network.target

[Service]
Type=simple
User=www-data
WorkingDirectory=/opt/optimiser
ExecStart=/opt/optimiser/venv/bin/streamlit run promoter_app.py --server.port 8502
Restart=always

[Install]
WantedBy=multi-user.target
```

Enable and start:
```bash
sudo systemctl enable bng-promoter-app
sudo systemctl start bng-promoter-app
```

#### Option 3: Docker

```dockerfile
FROM python:3.11-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .

EXPOSE 8501
CMD ["streamlit", "run", "promoter_app.py", "--server.port", "8501"]
```

Run:
```bash
docker build -t bng-promoter-app .
docker run -p 8502:8501 -v ./secrets.toml:/app/.streamlit/secrets.toml bng-promoter-app
```

### Nginx Configuration

```nginx
server {
    listen 80;
    server_name promoters.bng-quotes.wildcapital.co.uk;
    
    location / {
        proxy_pass http://127.0.0.1:8502;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

All promoters access the same URL, just with different login credentials.

## Advantages of Single App with Login

### vs. Multiple Separate Apps

✅ **Simpler deployment** - One app instead of many  
✅ **Easier maintenance** - Update once, affects all promoters  
✅ **Better tracking** - All data in one place  
✅ **Lower resource usage** - One Streamlit instance instead of many  
✅ **Centralized updates** - Bug fixes benefit everyone immediately  

### vs. Public Form

✅ **Authentication** - Only authorized promoters can access  
✅ **Tracking** - Know which promoter submitted each quote  
✅ **Accountability** - Audit trail of who used the system  
✅ **Control** - Can disable promoters if needed  

## Security Considerations

### Current Implementation

⚠️ **Simple password scheme** - Name + "1" is easy to guess  
✅ **Database-driven users** - Promoter list from database  
✅ **Session management** - Streamlit handles sessions  
✅ **Logout capability** - Users can end their session  

### Recommendations for Production

1. **Stronger passwords:**
   ```python
   # Instead of name+1, use hashed passwords in database
   import hashlib
   password_hash = hashlib.sha256(password.encode()).hexdigest()
   ```

2. **Rate limiting:**
   - Limit login attempts per IP
   - Temporary lockout after failed attempts

3. **Password changes:**
   - Allow promoters to change passwords
   - Store hashed passwords in database

4. **Session timeout:**
   - Add automatic logout after inactivity
   - Configurable timeout period

5. **HTTPS only:**
   - Always use SSL/TLS in production
   - Never send passwords over plain HTTP

## Monitoring & Analytics

### Track Usage by Promoter

```sql
-- Submissions per promoter
SELECT 
    promoter_name,
    COUNT(*) as total_submissions,
    AVG(total_cost) as avg_quote,
    SUM(total_cost) as total_value
FROM submissions
WHERE promoter_name IS NOT NULL
GROUP BY promoter_name
ORDER BY total_submissions DESC;

-- Recent activity
SELECT 
    promoter_name,
    submission_date,
    client_name,
    total_cost
FROM submissions
WHERE promoter_name IS NOT NULL
ORDER BY submission_date DESC
LIMIT 20;

-- Top promoters this month
SELECT 
    promoter_name,
    COUNT(*) as submissions
FROM submissions
WHERE promoter_name IS NOT NULL
  AND submission_date >= DATE_TRUNC('month', CURRENT_DATE)
GROUP BY promoter_name
ORDER BY submissions DESC;
```

## Next Steps / TODOs

### Short Term (Testing Phase)

- [x] Basic form UI
- [x] File upload and validation
- [x] Metric reading integration
- [x] Database persistence
- [x] Threshold logic
- [ ] **Actual PDF generation** (currently placeholder)
- [ ] **Email notifications** for manual reviews
- [ ] **Location resolution** (LPA/NCA from postcode)
- [ ] **Full optimizer integration** (currently simplified)

### Medium Term (Enhancement)

- [ ] Per-promoter branding/config
- [ ] File storage (Supabase or local)
- [ ] Admin dashboard to view submissions
- [ ] Email templates customization
- [ ] Analytics/reporting

### Long Term (Production)

- [ ] Multi-tenancy support
- [ ] Promoter authentication
- [ ] Custom domains per promoter
- [ ] Advanced quote customization
- [ ] CRM integration

## Advantages of Streamlit Approach

1. **Quick to test** - No backend deployment needed
2. **Familiar tools** - Same Streamlit environment as main app
3. **Shared codebase** - Uses existing metric_reader, database, etc.
4. **Easy iteration** - Change and test quickly
5. **Low infrastructure** - Just need Streamlit + database

## Disadvantages to Consider

1. **Performance** - Streamlit has overhead per user
2. **Scaling** - May need multiple instances for high traffic
3. **State management** - Session state can be tricky
4. **Customization** - Limited compared to custom web framework
5. **URLs** - Can't do pretty URLs like `/EPT` easily

## When to Switch to FastAPI Version

Consider switching when:

- Need to handle > 100 concurrent users per promoter
- Want custom URLs (e.g., `/EPT` instead of subdomains)
- Need more control over caching and performance
- Want to integrate with external APIs more efficiently
- Require more complex workflows

The FastAPI version is already implemented in the `backend/` directory if needed later.

## Troubleshooting

### Form won't start

```bash
# Check if port is in use
lsof -i :8502

# Try different port
streamlit run promoter_app.py --server.port 8505 -- --promoter EPT
```

### Database errors

```bash
# Check database connection
python -c "from database import SubmissionsDB; db = SubmissionsDB(); print('DB OK')"

# Check .streamlit/secrets.toml exists with database URL
cat .streamlit/secrets.toml
```

### Metric reading fails

- Verify file is valid BNG metric .xlsx
- Check metric_reader.py is working
- Test with known good metric file

### File too large

- Current limit: 15 MB
- Increase in code: `MAX_FILE_SIZE_MB = 50`
- Also increase Streamlit limit in config

## Support

For issues:
1. Check terminal output for errors
2. Verify database connection
3. Test with sample metric file
4. Review Streamlit logs
5. Check `.streamlit/secrets.toml` configuration

## Summary

This Streamlit-based approach provides a **quick and easy way** to test the promoter form functionality with minimal infrastructure requirements. Each promoter gets their own app instance, and submissions are tracked in the existing database.

**To get started:** Just run `./run_ept.sh` and open http://localhost:8502!
