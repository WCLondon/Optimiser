# Promoter Form Feature - README

## Overview

The Promoter Form feature provides a fast, zero-friction way for promoters to get BNG quotes through a simple URL-based form system. Each promoter has their own dedicated URL (e.g., `/EPT`, `/Arbtech`) that serves a clean, single-page form.

## Key Features

✅ **Ultra-simple submission flow** - One page, minimal fields, zero complexity  
✅ **Automatic threshold logic** - Quotes under £20,000 return instant PDF, quotes ≥£20,000 trigger manual review  
✅ **Secure file handling** - Private Supabase Storage with signed URLs  
✅ **Full audit trail** - Every submission tracked in database  
✅ **Professional PDFs** - Auto-generated quotes with branding and details  
✅ **Email notifications** - Reviewers notified for manual cases with metric download link  

## Quick Start

### For Development

1. **Install dependencies:**
   ```bash
   cd backend
   pip install -r requirements.txt
   ```

2. **Configure environment:**
   ```bash
   cp .env.example .env
   # Edit .env with your settings
   ```

3. **Run database migration:**
   ```bash
   psql $DATABASE_URL < ../promoter_submissions_schema.sql
   ```

4. **Start backend:**
   ```bash
   uvicorn app:app --reload --host 0.0.0.0 --port 8000
   ```

5. **Access form:**
   ```
   http://localhost:8000/EPT
   ```

### For Production

See [PROMOTER_FORM_DEPLOYMENT.md](PROMOTER_FORM_DEPLOYMENT.md) for detailed deployment instructions.

## How It Works

### User Journey

#### Auto-Quote Path (< £20,000)

```
User visits /{promoter} 
    → Fills form (email, location, metric file, consent)
    → Submits
    → System processes metric
    → Generates PDF quote
    → Returns PDF download immediately
    → Saves to database
```

#### Manual Review Path (≥ £20,000)

```
User visits /{promoter}
    → Fills form (email, location, metric file, consent)
    → Submits
    → System processes metric
    → Sends email to reviewers with metric link
    → Shows thank-you page
    → Saves to database
```

### Form Fields

**Required:**
- Contact Email
- BNG Metric File (.xlsx, max 15 MB)
- Consent checkbox
- At least one of: Site Address OR Postcode

**Optional:**
- Client Reference
- Additional Notes

### Technical Flow

1. **Form Display** (`GET /{promoter_slug}`)
   - Renders HTML form template
   - Promoter slug normalized (uppercase)

2. **Form Submission** (`POST /{promoter_slug}`)
   - Validates inputs
   - Uploads metric to Supabase Storage
   - Processes metric through optimizer
   - Calculates quote total
   - Applies threshold logic
   - Saves submission to database
   - Returns PDF or thank-you page

3. **Auto-Quote** (total < £20,000)
   - Generates professional PDF
   - Uploads PDF to Supabase Storage
   - Returns PDF as download
   - Sets status: `auto_quoted`

4. **Manual Review** (total ≥ £20,000)
   - Generates signed URL for metric (24h expiry)
   - Sends email to reviewers
   - Shows thank-you page
   - Sets status: `manual_review`

## Architecture

### Components

```
backend/
├── app.py                 # Main FastAPI application
├── promoter_routes.py     # Form routes and handlers
├── config.py              # Configuration management
├── database.py            # Database connection
├── storage.py             # Supabase Storage integration
├── optimizer.py           # BNG optimizer integration
├── pdf_generator.py       # PDF generation
├── email_service.py       # Email notifications
├── templates/
│   ├── promoter_form.html # Main form template
│   └── thank_you.html     # Manual review confirmation
└── test_promoter_routes.py # Smoke tests
```

### Database Schema

Table: `promoter_submissions`

Key fields:
- `id` - Auto-incrementing primary key
- `promoter_slug` - Promoter identifier (e.g., 'EPT')
- `contact_email` - Submitter's email
- `site_address` / `site_postcode` - Location
- `metric_file_path` - Storage path to uploaded file
- `pdf_file_path` - Storage path to generated PDF (auto-quotes only)
- `quote_total_gbp` - Calculated quote amount
- `status` - 'submitted', 'auto_quoted', 'manual_review', 'error'
- `auto_quoted` / `manual_review` - Boolean flags
- `allocation_results` - Full optimizer output (JSONB)

See `promoter_submissions_schema.sql` for full schema.

### Storage Buckets

- **promoter-metrics** - Private bucket for uploaded metric files
- **promoter-pdfs** - Private bucket for generated PDF quotes

Both buckets use signed URLs with expiration for secure access.

## Configuration

### Environment Variables

Required settings in `backend/.env`:

```bash
# Database
DATABASE_URL=postgresql://user:pass@host:port/db

# Supabase Storage
SUPABASE_URL=https://xxx.supabase.co
SUPABASE_KEY=your-service-role-key  # Important: Use service_role, not anon!

# Threshold
AUTO_QUOTE_THRESHOLD=20000.0  # £20,000 default

# Email
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your-email@example.com
SMTP_PASSWORD=your-password
REVIEWER_EMAILS=reviewer1@example.com,reviewer2@example.com

# Quote Settings
VAT_RATE=0.20
QUOTE_VALIDITY_DAYS=30
```

See `.env.example` for complete configuration options.

## Testing

### Run Smoke Tests

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
```

### Manual Testing

1. **Test form display:**
   ```bash
   curl http://localhost:8000/EPT
   ```

2. **Test with different promoters:**
   ```bash
   curl http://localhost:8000/Arbtech
   curl http://localhost:8000/TestPromoter
   ```

3. **Test form submission:**
   ```bash
   curl -X POST http://localhost:8000/EPT \
     -F "contact_email=test@example.com" \
     -F "site_postcode=SW1A 1AA" \
     -F "consent=on" \
     -F "metric_file=@test_metric.xlsx"
   ```

## Security

### File Upload Security

- ✅ File type validation (.xlsx only)
- ✅ File size limit (15 MB)
- ✅ Private storage buckets
- ✅ Signed URLs with expiration
- ✅ Virus scanning (recommended in production)

### Rate Limiting

Recommended Nginx configuration:
```nginx
limit_req_zone $binary_remote_addr zone=promoter_limit:10m rate=10r/m;
location ~ ^/(EPT|Arbtech) {
    limit_req zone=promoter_limit burst=5 nodelay;
    ...
}
```

### Data Privacy

- ✅ Minimal PII collected (email + location only)
- ✅ Consent checkbox required
- ✅ Secure storage (private buckets)
- ✅ IP address logged for audit
- ✅ HTTPS required in production

## Monitoring

### Key Metrics

```sql
-- Submissions by promoter
SELECT promoter_slug, COUNT(*) 
FROM promoter_submissions 
GROUP BY promoter_slug;

-- Auto-quote vs manual review ratio
SELECT 
    SUM(CASE WHEN auto_quoted THEN 1 ELSE 0 END) as auto_quotes,
    SUM(CASE WHEN manual_review THEN 1 ELSE 0 END) as manual_reviews
FROM promoter_submissions;

-- Recent errors
SELECT * FROM promoter_submissions 
WHERE error_occurred = TRUE 
ORDER BY created_at DESC 
LIMIT 10;
```

### Logs

```bash
# Backend logs
journalctl -u bng-backend -f

# Nginx access logs
tail -f /var/log/nginx/access.log
```

## Troubleshooting

### Common Issues

**1. Form not loading**
- Check backend service running
- Verify port 8000 accessible
- Check Nginx configuration

**2. File upload fails**
- Verify Supabase buckets exist
- Check service role key (not anon key)
- Verify bucket permissions

**3. Email not sending**
- Check SMTP credentials
- Verify firewall allows port 587
- Check reviewer email list

**4. Database errors**
- Verify migration ran successfully
- Check DATABASE_URL
- Test connection with: `psql $DATABASE_URL -c "SELECT 1"`

## API Reference

### GET /{promoter_slug}

Display the promoter quote request form.

**Parameters:**
- `promoter_slug` (path) - Promoter identifier (e.g., 'EPT', 'Arbtech')

**Response:** HTML form page

### POST /{promoter_slug}

Process a quote request submission.

**Parameters:**
- `promoter_slug` (path) - Promoter identifier
- `contact_email` (form, required) - Contact email
- `site_address` (form, optional) - Site address
- `site_postcode` (form, optional) - Site postcode
- `client_reference` (form, optional) - Client reference
- `notes` (form, optional) - Additional notes
- `metric_file` (file, required) - BNG metric Excel file
- `consent` (form, required) - Data sharing consent

**Response:** 
- Auto-quote: PDF download (application/pdf)
- Manual review: HTML thank-you page

## Acceptance Criteria

✅ Visiting /EPT or /Arbtech shows the same simple form  
✅ Submissions record the correct promoter_slug  
✅ Valid .xlsx with total £19,999 returns immediate PDF download  
✅ Valid .xlsx with total £20,000 shows thank-you screen and sends review email  
✅ All submissions appear in database with correct metadata  
✅ Metric files always stored  
✅ PDFs only for auto-quotes  
✅ Invalid input rejected with clear error messages  

## Future Enhancements

Out of scope for this PR:

- Admin listing UI for submissions
- Promoter authentication/whitelisting
- CRM integration
- Address auto-lookup/enrichment
- Multi-language support
- Custom branding per promoter
- Real-time quote status tracking

## Support

For issues or questions:

1. Check logs: `journalctl -u bng-backend -f`
2. Review database: `SELECT * FROM promoter_submissions ORDER BY created_at DESC LIMIT 10`
3. Verify configuration: `cat backend/.env`
4. Run smoke tests: `python backend/test_promoter_routes.py`
5. Contact development team

## License

Same as main BNG Optimiser project.
