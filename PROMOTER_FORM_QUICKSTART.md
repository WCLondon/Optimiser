# Quick Setup Guide for Promoter Form Feature

## Prerequisites Checklist

✅ Supabase database credentials (provided)  
⬜ Supabase Storage buckets created  
⬜ Supabase service role key obtained  
⬜ SMTP credentials configured  
⬜ Reviewer email addresses identified  

## Step 1: Database Migration (Required)

The `promoter_submissions` table needs to be created in your Supabase database.

### Option A: Using psql (Recommended)

```bash
# Using the provided credentials
psql "postgresql+psycopg://postgres.faasgsdpkfedgahzbamg:WjIBfesRmhVtEc31@aws-1-eu-north-1.pooler.supabase.com:6543/postgres" \
  -f promoter_submissions_schema.sql
```

### Option B: Using Supabase SQL Editor

1. Log into Supabase Dashboard: https://supabase.com/dashboard
2. Select your project: `faasgsdpkfedgahzbamg`
3. Go to **SQL Editor**
4. Copy and paste the contents of `promoter_submissions_schema.sql`
5. Click **Run**

### Verify Migration

```sql
-- Check table exists
SELECT table_name FROM information_schema.tables 
WHERE table_name = 'promoter_submissions';

-- Check columns
SELECT column_name, data_type 
FROM information_schema.columns 
WHERE table_name = 'promoter_submissions';

-- Check indexes
SELECT indexname FROM pg_indexes 
WHERE tablename = 'promoter_submissions';
```

Expected indexes:
- `promoter_submissions_pkey`
- `idx_promoter_submissions_promoter`
- `idx_promoter_submissions_created`
- `idx_promoter_submissions_status`
- `idx_promoter_submissions_email`

## Step 2: Supabase Storage Setup (Required)

### 2.1 Get Service Role Key

1. Log into Supabase Dashboard
2. Go to **Settings** → **API**
3. Copy the **service_role** key (NOT the anon key!)
4. Update `backend/.env`:
   ```bash
   SUPABASE_KEY=eyJhbGciOi...your-service-role-key
   ```

### 2.2 Create Storage Buckets

#### Method 1: Using Supabase Dashboard

1. Go to **Storage** in Supabase Dashboard
2. Create bucket: `promoter-metrics`
   - Name: `promoter-metrics`
   - Public: **No** (keep private)
   - Allowed MIME types: `application/vnd.openxmlformats-officedocument.spreadsheetml.sheet`
   - File size limit: 15 MB

3. Create bucket: `promoter-pdfs`
   - Name: `promoter-pdfs`
   - Public: **No** (keep private)
   - Allowed MIME types: `application/pdf`
   - File size limit: 10 MB

#### Method 2: Using SQL

```sql
-- Create metrics bucket
INSERT INTO storage.buckets (id, name, public, file_size_limit, allowed_mime_types)
VALUES (
  'promoter-metrics',
  'promoter-metrics',
  false,
  15728640,  -- 15 MB
  ARRAY['application/vnd.openxmlformats-officedocument.spreadsheetml.sheet']
);

-- Create PDFs bucket
INSERT INTO storage.buckets (id, name, public, file_size_limit, allowed_mime_types)
VALUES (
  'promoter-pdfs',
  'promoter-pdfs',
  false,
  10485760,  -- 10 MB
  ARRAY['application/pdf']
);
```

### 2.3 Set Bucket Policies

Run in Supabase SQL Editor:

```sql
-- Policies for promoter-metrics bucket
CREATE POLICY "Service role full access to metrics"
ON storage.objects FOR ALL
TO service_role
USING (bucket_id = 'promoter-metrics')
WITH CHECK (bucket_id = 'promoter-metrics');

-- Policies for promoter-pdfs bucket
CREATE POLICY "Service role full access to pdfs"
ON storage.objects FOR ALL
TO service_role
USING (bucket_id = 'promoter-pdfs')
WITH CHECK (bucket_id = 'promoter-pdfs');
```

## Step 3: Email Configuration (Required)

Update `backend/.env` with your SMTP settings.

### For Gmail:

1. Enable 2-factor authentication on your Google account
2. Go to: https://myaccount.google.com/apppasswords
3. Generate an "App Password" for Mail
4. Update `.env`:
   ```bash
   SMTP_HOST=smtp.gmail.com
   SMTP_PORT=587
   SMTP_USER=your-email@gmail.com
   SMTP_PASSWORD=xxxx-xxxx-xxxx-xxxx  # 16-character app password
   SMTP_FROM_EMAIL=quotes@wildcapital.co.uk
   REVIEWER_EMAILS=reviewer1@wildcapital.co.uk,reviewer2@wildcapital.co.uk
   ```

### For Other SMTP Providers:

Update accordingly based on your provider's settings.

## Step 4: Verify Backend Configuration

```bash
cd backend

# Test configuration loading
python -c "from config import get_settings; s = get_settings(); print('✓ Config OK')"

# Test database connection (requires network access)
python -c "from database import get_db_engine; e = get_db_engine(); print('✓ Database OK')"

# Test storage (requires SUPABASE_KEY to be set)
python -c "from storage import SupabaseStorage; s = SupabaseStorage(); print('✓ Storage OK')"
```

## Step 5: Run Smoke Tests

```bash
cd backend
python test_promoter_routes.py
```

Expected output:
```
✓ App health check passed
✓ Form display test passed
✓ Multiple promoter slugs test passed
✓ Required fields test passed
✓ Validation messages test passed

All smoke tests completed!
```

## Step 6: Start Backend Server

### Development Mode

```bash
cd backend
uvicorn app:app --reload --host 0.0.0.0 --port 8000
```

### Access Forms

- EPT: http://localhost:8000/EPT
- Arbtech: http://localhost:8000/Arbtech
- Any promoter: http://localhost:8000/{PROMOTER_NAME}

## Step 7: Test End-to-End

### Manual Test Submission

1. Visit: http://localhost:8000/EPT
2. Fill in form:
   - Contact Email: test@example.com
   - Site Postcode: SW1A 1AA
   - Upload a test .xlsx file
   - Check consent box
3. Submit
4. Verify:
   - Form processes without errors
   - Check database for new record:
     ```sql
     SELECT * FROM promoter_submissions ORDER BY created_at DESC LIMIT 1;
     ```
   - Check Supabase Storage for uploaded metric file

## Configuration Checklist

✅ Database credentials configured (`backend/.env`)  
⬜ Database migration completed (`promoter_submissions` table exists)  
⬜ Supabase service role key added to `.env`  
⬜ Storage buckets created (`promoter-metrics`, `promoter-pdfs`)  
⬜ Storage bucket policies set  
⬜ SMTP credentials configured  
⬜ Reviewer emails configured  
⬜ Backend starts without errors  
⬜ Smoke tests pass  
⬜ Form loads in browser  
⬜ Test submission completes successfully  

## Troubleshooting

### Database Connection Issues

```bash
# Test connection directly
psql "postgresql+psycopg://postgres.faasgsdpkfedgahzbamg:WjIBfesRmhVtEc31@aws-1-eu-north-1.pooler.supabase.com:6543/postgres" -c "SELECT 1"
```

If this fails, check:
- Network connectivity
- Firewall rules
- Database password hasn't changed

### Storage Issues

Common issues:
- Using anon key instead of service role key
- Buckets don't exist
- Bucket policies not set
- Wrong bucket names in `.env`

### Email Issues

Test SMTP connection:
```python
import smtplib
server = smtplib.SMTP('smtp.gmail.com', 587)
server.starttls()
server.login('your-email@gmail.com', 'your-app-password')
print("✓ SMTP connection successful")
server.quit()
```

## Production Deployment

Once testing is complete locally, see [PROMOTER_FORM_DEPLOYMENT.md](PROMOTER_FORM_DEPLOYMENT.md) for:

- Systemd service configuration
- Nginx reverse proxy setup
- SSL certificate installation
- Rate limiting configuration
- Monitoring and logging setup

## Next Steps

1. ✅ Complete setup checklist above
2. Test with real BNG metric files
3. Verify email notifications work
4. Test PDF generation
5. Configure production environment
6. Set up monitoring and alerts
7. Deploy to production server

## Support

If you encounter issues:

1. Check backend logs: `journalctl -u bng-backend -f` (production) or terminal output (dev)
2. Verify database: `SELECT * FROM promoter_submissions;`
3. Check Supabase Storage: Dashboard → Storage
4. Review `.env` configuration
5. Run smoke tests: `python backend/test_promoter_routes.py`

## Quick Reference

### Database Connection String
```
postgresql+psycopg://postgres.faasgsdpkfedgahzbamg:WjIBfesRmhVtEc31@aws-1-eu-north-1.pooler.supabase.com:6543/postgres
```

### Supabase Project
```
Project ID: faasgsdpkfedgahzbamg
URL: https://faasgsdpkfedgahzbamg.supabase.co
```

### Storage Buckets
```
promoter-metrics (private, 15MB limit, .xlsx only)
promoter-pdfs (private, 10MB limit, .pdf only)
```

### Environment Variables Template
```bash
DATABASE_URL=postgresql+psycopg://postgres.faasgsdpkfedgahzbamg:WjIBfesRmhVtEc31@aws-1-eu-north-1.pooler.supabase.com:6543/postgres
SUPABASE_URL=https://faasgsdpkfedgahzbamg.supabase.co
SUPABASE_KEY=your-service-role-key-here
AUTO_QUOTE_THRESHOLD=20000.0
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your-email@gmail.com
SMTP_PASSWORD=your-app-password
REVIEWER_EMAILS=reviewer@wildcapital.co.uk
```
