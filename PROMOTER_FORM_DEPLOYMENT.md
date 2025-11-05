# Promoter Form Deployment Guide

## Quick Start

This guide covers deploying the promoter form feature alongside the existing BNG Optimiser application.

## Prerequisites

- PostgreSQL database (with Supabase or standalone)
- Supabase project with Storage enabled
- SMTP server for email notifications
- Python 3.11+
- Nginx or similar reverse proxy (recommended)

## Step 1: Database Setup

### 1.1 Run Migration

```bash
# Connect to your database
psql $DATABASE_URL

# Run the schema creation script
\i promoter_submissions_schema.sql

# Verify table was created
\dt promoter_submissions
```

### 1.2 Verify Indexes

```bash
# Check indexes
\di promoter_submissions*
```

Expected indexes:
- `idx_promoter_submissions_promoter`
- `idx_promoter_submissions_created`
- `idx_promoter_submissions_status`
- `idx_promoter_submissions_email`

## Step 2: Supabase Storage Setup

### 2.1 Create Storage Buckets

In your Supabase dashboard:

1. Navigate to Storage
2. Create bucket: `promoter-metrics`
   - Private
   - File size limit: 15 MB
   - Allowed MIME types: `application/vnd.openxmlformats-officedocument.spreadsheetml.sheet`

3. Create bucket: `promoter-pdfs`
   - Private
   - File size limit: 10 MB
   - Allowed MIME types: `application/pdf`

### 2.2 Set Bucket Policies

For `promoter-metrics`:
```sql
-- Allow service role to upload and read
CREATE POLICY "Service role can upload metrics"
ON storage.objects FOR INSERT
TO service_role
WITH CHECK (bucket_id = 'promoter-metrics');

CREATE POLICY "Service role can read metrics"
ON storage.objects FOR SELECT
TO service_role
USING (bucket_id = 'promoter-metrics');
```

For `promoter-pdfs`:
```sql
-- Allow service role to upload and read
CREATE POLICY "Service role can upload PDFs"
ON storage.objects FOR INSERT
TO service_role
WITH CHECK (bucket_id = 'promoter-pdfs');

CREATE POLICY "Service role can read PDFs"
ON storage.objects FOR SELECT
TO service_role
USING (bucket_id = 'promoter-pdfs');
```

## Step 3: Environment Configuration

### 3.1 Backend Configuration

Create `/backend/.env`:

```bash
# Database
DATABASE_URL=postgresql://user:password@host:5432/database

# Supabase
SUPABASE_URL=https://xxxxx.supabase.co
SUPABASE_KEY=your-service-role-key-here  # Use service_role key, not anon key!
SUPABASE_METRICS_BUCKET=promoter-metrics
SUPABASE_PDFS_BUCKET=promoter-pdfs

# Auto-quote threshold (£20,000 default)
AUTO_QUOTE_THRESHOLD=20000.0

# Email Configuration
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your-email@gmail.com
SMTP_PASSWORD=your-app-specific-password
SMTP_FROM_EMAIL=quotes@wildcapital.co.uk
SMTP_FROM_NAME=Wild Capital BNG Quotes

# Reviewer emails (comma-separated, no spaces)
REVIEWER_EMAILS=reviewer1@wildcapital.co.uk,reviewer2@wildcapital.co.uk

# Quote settings
VAT_RATE=0.20
QUOTE_VALIDITY_DAYS=30

# Redis (for job queue)
REDIS_HOST=redis
REDIS_PORT=6379
REDIS_DB=0
CACHE_TTL=43200
```

### 3.2 SMTP Setup (Gmail Example)

If using Gmail:

1. Enable 2-factor authentication
2. Generate an "App Password":
   - Go to Google Account settings
   - Security → 2-Step Verification → App passwords
   - Create password for "Mail"
3. Use the generated password as `SMTP_PASSWORD`

## Step 4: Install Dependencies

```bash
cd backend
pip install -r requirements.txt
```

## Step 5: Run Backend Server

### Development

```bash
cd backend
uvicorn app:app --reload --host 0.0.0.0 --port 8000
```

### Production

Using systemd service:

Create `/etc/systemd/system/bng-backend.service`:

```ini
[Unit]
Description=BNG Optimiser Backend API
After=network.target

[Service]
Type=simple
User=www-data
WorkingDirectory=/opt/optimiser/backend
Environment="PATH=/opt/optimiser/venv/bin"
ExecStart=/opt/optimiser/venv/bin/uvicorn app:app --host 0.0.0.0 --port 8000 --workers 4
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Enable and start:

```bash
sudo systemctl enable bng-backend
sudo systemctl start bng-backend
sudo systemctl status bng-backend
```

## Step 6: Configure Nginx

### 6.1 Create Nginx Configuration

Create `/etc/nginx/sites-available/bng-promoter`:

```nginx
# Rate limiting zone
limit_req_zone $binary_remote_addr zone=promoter_limit:10m rate=10r/m;

server {
    listen 80;
    server_name optimiser.wildcapital.co.uk;
    
    # Redirect to HTTPS
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name optimiser.wildcapital.co.uk;
    
    # SSL certificates
    ssl_certificate /etc/letsencrypt/live/optimiser.wildcapital.co.uk/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/optimiser.wildcapital.co.uk/privkey.pem;
    
    # SSL configuration
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;
    ssl_prefer_server_ciphers on;
    
    # Security headers
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;
    add_header Referrer-Policy "strict-origin-when-cross-origin" always;
    
    # Client body size limit (for file uploads)
    client_max_body_size 20M;
    
    # Promoter form routes (must come before main app)
    location ~ ^/(EPT|Arbtech|[A-Za-z0-9_-]+)$ {
        # Apply rate limiting
        limit_req zone=promoter_limit burst=5 nodelay;
        
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # Timeout for file uploads
        proxy_read_timeout 300s;
        proxy_connect_timeout 300s;
        proxy_send_timeout 300s;
    }
    
    # Main Streamlit app
    location / {
        proxy_pass http://127.0.0.1:8501;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # WebSocket support for Streamlit
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_read_timeout 86400;
    }
    
    # Backend API endpoints
    location /api/ {
        proxy_pass http://127.0.0.1:8000/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
    
    # Health check
    location /health {
        proxy_pass http://127.0.0.1:8000/health;
        access_log off;
    }
}
```

### 6.2 Enable Configuration

```bash
sudo ln -s /etc/nginx/sites-available/bng-promoter /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

## Step 7: SSL Certificate (Let's Encrypt)

```bash
sudo apt-get update
sudo apt-get install certbot python3-certbot-nginx
sudo certbot --nginx -d optimiser.wildcapital.co.uk
```

## Step 8: Testing

### 8.1 Test Form Access

```bash
curl -I https://optimiser.wildcapital.co.uk/EPT
# Should return 200 OK with HTML content
```

### 8.2 Test Database Connection

```bash
cd backend
python -c "from database import get_db_engine; engine = get_db_engine(); print('DB OK')"
```

### 8.3 Test Storage Connection

```bash
cd backend
python -c "from storage import SupabaseStorage; s = SupabaseStorage(); print('Storage OK')"
```

### 8.4 Run Smoke Tests

```bash
cd backend
python test_promoter_routes.py
```

## Step 9: Monitoring

### 9.1 Check Logs

```bash
# Backend logs
sudo journalctl -u bng-backend -f

# Nginx logs
sudo tail -f /var/log/nginx/access.log
sudo tail -f /var/log/nginx/error.log
```

### 9.2 Monitor Submissions

```sql
-- Recent submissions
SELECT 
    id, created_at, promoter_slug, contact_email, 
    quote_total_gbp, status 
FROM promoter_submissions 
ORDER BY created_at DESC 
LIMIT 10;

-- Submission statistics
SELECT 
    promoter_slug,
    COUNT(*) as total,
    SUM(CASE WHEN auto_quoted THEN 1 ELSE 0 END) as auto_quotes,
    SUM(CASE WHEN manual_review THEN 1 ELSE 0 END) as manual_reviews,
    AVG(quote_total_gbp) as avg_quote
FROM promoter_submissions 
GROUP BY promoter_slug;
```

## Step 10: Backup

### 10.1 Database Backup

```bash
# Backup submissions table
pg_dump -h host -U user -d database -t promoter_submissions > backup.sql

# Scheduled backup (cron)
0 2 * * * pg_dump -h host -U user -d database -t promoter_submissions > /backups/promoter_$(date +\%Y\%m\%d).sql
```

### 10.2 Storage Backup

Supabase Storage automatically handles backups, but you can also:

```python
# Script to backup all files
from storage import SupabaseStorage
import os

storage = SupabaseStorage()
# Download and backup files locally
# (Implementation depends on your backup strategy)
```

## Troubleshooting

### Issue: Form not loading

**Check:**
1. Nginx configuration correct?
2. Backend service running? `systemctl status bng-backend`
3. Port 8000 accessible? `netstat -tlnp | grep 8000`

### Issue: File upload fails

**Check:**
1. Nginx `client_max_body_size` set correctly
2. Supabase buckets exist and are accessible
3. Service role key (not anon key) used in config

### Issue: Email not sending

**Check:**
1. SMTP credentials correct
2. Firewall allows outbound SMTP (port 587)
3. Check backend logs for email errors

### Issue: Database errors

**Check:**
1. Migration ran successfully
2. Database URL correct
3. Table and indexes exist
4. Connection pooling working

## Security Checklist

- [ ] HTTPS enabled with valid certificate
- [ ] Rate limiting configured in Nginx
- [ ] File size limits enforced
- [ ] Private storage buckets
- [ ] Service role key (not anon key) for Supabase
- [ ] SMTP credentials secured
- [ ] Database connection string secured
- [ ] Firewall rules configured
- [ ] Regular backups enabled
- [ ] Monitoring and alerting set up

## Next Steps

1. Test with real BNG metric files
2. Monitor performance under load
3. Set up alerting for errors
4. Plan admin dashboard for viewing submissions
5. Consider CDN for static assets
6. Implement additional promoter-specific features
