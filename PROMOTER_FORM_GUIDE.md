# Promoter Form Feature - Implementation Guide

## Overview

This feature adds a simple, URL-based quote request form for promoters. Each promoter gets their own URL (e.g., `/EPT`, `/Arbtech`) where they can submit BNG metric files and receive instant quotes or manual reviews.

## Key Features

- **Zero-friction submissions**: Single-page HTML form with minimal fields
- **Automatic quote generation**: Quotes under £20,000 generate and return PDF immediately
- **Manual review path**: Quotes ≥£20,000 trigger email notification to reviewers
- **Secure file storage**: All uploads stored in private Supabase buckets with signed URLs
- **Full audit trail**: Every submission saved to database with metadata

## Architecture

### Components

1. **FastAPI Routes** (`backend/promoter_routes.py`)
   - GET `/{promoter_slug}`: Display form
   - POST `/{promoter_slug}`: Process submission

2. **HTML Templates** (`backend/templates/`)
   - `promoter_form.html`: Main form
   - `thank_you.html`: Manual review confirmation page

3. **Storage** (`backend/storage.py`)
   - Supabase storage integration
   - File upload/download with signed URLs

4. **Optimizer Integration** (`backend/optimizer.py`)
   - Reads BNG metric files
   - Runs optimizer logic
   - Returns allocation results and totals

5. **PDF Generation** (`backend/pdf_generator.py`)
   - Creates professional quote PDFs
   - Includes all relevant details and pricing

6. **Email Service** (`backend/email_service.py`)
   - Sends review notifications
   - Includes submission details and metric download link

7. **Database** (`promoter_submissions` table)
   - Stores all submissions
   - Tracks status and file paths
   - Maintains audit trail

## Database Schema

```sql
CREATE TABLE promoter_submissions (
    id SERIAL PRIMARY KEY,
    created_at TIMESTAMP NOT NULL,
    promoter_slug TEXT NOT NULL,
    contact_email TEXT NOT NULL,
    site_address TEXT,
    site_postcode TEXT,
    client_reference TEXT,
    notes TEXT,
    target_lpa TEXT,
    target_nca TEXT,
    target_lat FLOAT,
    target_lon FLOAT,
    metric_file_path TEXT NOT NULL,
    metric_file_size_bytes INTEGER,
    pdf_file_path TEXT,
    pdf_file_size_bytes INTEGER,
    quote_total_gbp FLOAT NOT NULL,
    admin_fee_gbp FLOAT,
    total_with_admin_gbp FLOAT,
    status TEXT NOT NULL,
    auto_quoted BOOLEAN DEFAULT FALSE,
    manual_review BOOLEAN DEFAULT FALSE,
    emailed BOOLEAN DEFAULT FALSE,
    error_occurred BOOLEAN DEFAULT FALSE,
    error_message TEXT,
    reviewer_email TEXT,
    allocation_results JSONB,
    ip_address TEXT,
    user_agent TEXT,
    consent_given BOOLEAN NOT NULL
);
```

## Configuration

### Environment Variables

Required variables in `.env`:

```bash
# Database
DATABASE_URL=postgresql://user:pass@host:port/db

# Supabase
SUPABASE_URL=https://xxx.supabase.co
SUPABASE_KEY=your-key
SUPABASE_METRICS_BUCKET=promoter-metrics
SUPABASE_PDFS_BUCKET=promoter-pdfs

# Thresholds
AUTO_QUOTE_THRESHOLD=20000.0

# Email
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your-email@example.com
SMTP_PASSWORD=your-password
REVIEWER_EMAILS=reviewer@example.com

# Quote settings
VAT_RATE=0.20
QUOTE_VALIDITY_DAYS=30
```

### Supabase Storage Setup

1. Create two storage buckets:
   - `promoter-metrics` (private)
   - `promoter-pdfs` (private)

2. Set bucket permissions:
   - Allow authenticated service role to upload/download
   - Block public access
   - Enable RLS (Row Level Security)

## Deployment

### 1. Database Migration

```bash
psql $DATABASE_URL < promoter_submissions_schema.sql
```

### 2. Install Dependencies

```bash
cd backend
pip install -r requirements.txt
```

### 3. Configure Environment

```bash
cp .env.example .env
# Edit .env with your values
```

### 4. Run Backend

```bash
# Development
uvicorn app:app --reload --host 0.0.0.0 --port 8000

# Production
uvicorn app:app --host 0.0.0.0 --port 8000 --workers 4
```

## Usage

### Accessing the Form

Navigate to: `http://your-domain/{promoter_slug}`

Examples:
- `http://localhost:8000/EPT`
- `http://localhost:8000/Arbtech`
- `https://optimiser.wildcapital.co.uk/MyPromoter`

### Form Fields

**Required:**
- Contact Email
- BNG Metric File (.xlsx)
- Consent checkbox
- At least one of: Site Address OR Postcode

**Optional:**
- Client Reference
- Notes

### Submission Flow

#### Auto-Quote (< £20,000)

1. User submits form
2. System uploads metric to storage
3. Optimizer processes metric
4. PDF quote generated
5. Submission saved to database
6. PDF returned as download

#### Manual Review (≥ £20,000)

1. User submits form
2. System uploads metric to storage
3. Optimizer processes metric
4. Submission saved to database
5. Email sent to reviewers with:
   - Submission details
   - Quote total
   - Link to download metric
6. Thank you page displayed

## File Validation

- **Format**: Only `.xlsx` files accepted
- **Size**: Maximum 15 MB
- **Content**: Must be valid BNG metric format

## Security Features

- File uploads validated (type, size)
- Private storage buckets
- Signed URLs with expiration
- Rate limiting (recommended: implement at nginx/CDN level)
- IP address logging
- User agent tracking
- HTTPS required in production

## Testing

### Manual Testing Checklist

1. **Form Display**
   - [ ] Form loads at `/{promoter_slug}`
   - [ ] All fields render correctly
   - [ ] Validation messages work

2. **File Upload**
   - [ ] Valid .xlsx file uploads successfully
   - [ ] Invalid file types rejected
   - [ ] Oversized files rejected

3. **Auto-Quote Path**
   - [ ] Submit with total < £20k
   - [ ] PDF downloads automatically
   - [ ] Submission saved in database
   - [ ] Files stored in Supabase

4. **Manual Review Path**
   - [ ] Submit with total ≥ £20k
   - [ ] Thank you page displays
   - [ ] Email sent to reviewers
   - [ ] Metric link works in email
   - [ ] Submission saved in database

5. **Validation**
   - [ ] Email required
   - [ ] Address OR postcode required
   - [ ] Consent required
   - [ ] File required

### Integration Testing

```python
# Test auto-quote submission
response = client.post(
    "/EPT",
    data={
        "contact_email": "test@example.com",
        "site_postcode": "SW1A 1AA",
        "consent": "on"
    },
    files={"metric_file": ("test.xlsx", metric_content)}
)
assert response.status_code == 200
assert response.headers["content-type"] == "application/pdf"
```

## Monitoring

### Key Metrics

- Submission volume by promoter
- Auto-quote vs manual review ratio
- Average quote totals
- File upload success rate
- Email delivery rate
- Error rate

### Database Queries

```sql
-- Submissions by promoter
SELECT promoter_slug, COUNT(*) 
FROM promoter_submissions 
GROUP BY promoter_slug;

-- Auto-quote rate
SELECT 
    COUNT(*) FILTER (WHERE auto_quoted) as auto_quotes,
    COUNT(*) FILTER (WHERE manual_review) as manual_reviews,
    COUNT(*) as total
FROM promoter_submissions;

-- Recent errors
SELECT * FROM promoter_submissions 
WHERE error_occurred = TRUE 
ORDER BY created_at DESC 
LIMIT 10;
```

## Troubleshooting

### Common Issues

1. **File upload fails**
   - Check Supabase credentials
   - Verify bucket names
   - Check bucket permissions

2. **Email not sending**
   - Verify SMTP credentials
   - Check reviewer email list
   - Check spam folder

3. **PDF generation fails**
   - Check reportlab installation
   - Verify allocation_results format
   - Check file permissions

4. **Database errors**
   - Run migration script
   - Check DATABASE_URL
   - Verify table exists

## Future Enhancements

Out of scope for this PR but planned:

- Admin dashboard for viewing submissions
- Promoter authentication/whitelisting
- CRM integration
- Address auto-lookup/enrichment
- Multi-language support
- Custom branding per promoter

## Support

For issues or questions:
- Check logs in backend console
- Review database for submission records
- Verify environment configuration
- Contact development team
