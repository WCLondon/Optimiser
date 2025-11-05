-- Schema for promoter_submissions table
-- This table tracks all submissions from the promoter form

CREATE TABLE IF NOT EXISTS promoter_submissions (
    id SERIAL PRIMARY KEY,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    
    -- Promoter identification
    promoter_slug TEXT NOT NULL,
    
    -- Contact and location
    contact_email TEXT NOT NULL,
    site_address TEXT,
    site_postcode TEXT,
    client_reference TEXT,
    notes TEXT,
    
    -- Geographic metadata (resolved from address/postcode)
    target_lpa TEXT,
    target_nca TEXT,
    target_lat FLOAT,
    target_lon FLOAT,
    
    -- File paths in Supabase storage
    metric_file_path TEXT NOT NULL,
    metric_file_size_bytes INTEGER,
    pdf_file_path TEXT,
    pdf_file_size_bytes INTEGER,
    
    -- Quote results
    quote_total_gbp FLOAT NOT NULL,
    admin_fee_gbp FLOAT,
    total_with_admin_gbp FLOAT,
    
    -- Status flags
    status TEXT NOT NULL DEFAULT 'submitted',
    auto_quoted BOOLEAN DEFAULT FALSE,
    manual_review BOOLEAN DEFAULT FALSE,
    emailed BOOLEAN DEFAULT FALSE,
    error_occurred BOOLEAN DEFAULT FALSE,
    error_message TEXT,
    
    -- Reviewer information
    reviewer_email TEXT,
    
    -- Allocation results (full optimization output)
    allocation_results JSONB,
    
    -- Request metadata
    ip_address TEXT,
    user_agent TEXT,
    
    -- Consent tracking
    consent_given BOOLEAN NOT NULL DEFAULT FALSE
);

-- Create indexes for efficient queries
CREATE INDEX IF NOT EXISTS idx_promoter_submissions_promoter ON promoter_submissions(promoter_slug);
CREATE INDEX IF NOT EXISTS idx_promoter_submissions_created ON promoter_submissions(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_promoter_submissions_status ON promoter_submissions(status);
CREATE INDEX IF NOT EXISTS idx_promoter_submissions_email ON promoter_submissions(contact_email);

-- Add check constraint for status values
ALTER TABLE promoter_submissions 
DROP CONSTRAINT IF EXISTS promoter_submissions_status_check;

ALTER TABLE promoter_submissions 
ADD CONSTRAINT promoter_submissions_status_check 
CHECK (status IN ('submitted', 'auto_quoted', 'manual_review', 'error'));

-- Add check constraint to ensure at least one of address or postcode is provided
ALTER TABLE promoter_submissions
DROP CONSTRAINT IF EXISTS promoter_submissions_location_check;

ALTER TABLE promoter_submissions
ADD CONSTRAINT promoter_submissions_location_check
CHECK (site_address IS NOT NULL OR site_postcode IS NOT NULL);
