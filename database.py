"""
Database module for BNG Optimiser submissions tracking.
Uses PostgreSQL via SQLAlchemy for persistent storage of all form submissions and optimization results.
"""

import json
from datetime import datetime
from typing import Dict, List, Optional, Any, Union
from decimal import Decimal
import pandas as pd
import numpy as np
from sqlalchemy import text, Table, MetaData, Column, Integer, String, Float, DateTime, ForeignKey, Index, ARRAY, Text
from sqlalchemy.dialects.postgresql import JSONB
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from db import DatabaseConnection


def sanitize_for_db(value: Any) -> Any:
    """
    Sanitize a value for database insertion.
    
    Converts:
    - numpy numeric types to native Python types
    - Decimal to float
    - Ensures proper JSON serialization
    - Handles None values
    
    Args:
        value: Value to sanitize
    
    Returns:
        Sanitized value ready for database insertion
    """
    if value is None:
        return None
    
    # Check for NaN/inf in regular floats first (np.nan is actually a Python float)
    if isinstance(value, float):
        if np.isnan(value) or np.isinf(value):
            return None
        return value
    
    # Convert numpy types to native Python types
    if isinstance(value, (np.integer, np.int64, np.int32)):
        return int(value)
    elif isinstance(value, (np.floating, np.float64, np.float32)):
        # Check for NaN or inf
        if np.isnan(value) or np.isinf(value):
            return None
        return float(value)
    elif isinstance(value, np.bool_):
        return bool(value)
    
    # Convert Decimal to float
    elif isinstance(value, Decimal):
        return float(value)
    
    # Handle lists recursively
    elif isinstance(value, list):
        return [sanitize_for_db(item) for item in value]
    
    # Handle dicts recursively
    elif isinstance(value, dict):
        return {key: sanitize_for_db(val) for key, val in value.items()}
    
    return value


class SubmissionsDB:
    """Handle all database operations for submissions tracking."""
    
    def __init__(self, db_path: str = "submissions.db"):
        """
        Initialize database connection and create tables if needed.
        
        Note: db_path parameter is kept for backward compatibility but is ignored.
        Connection is managed through Streamlit secrets.
        """
        self.db_path = db_path  # Kept for backward compatibility
        self._conn = None
        self._init_database()
    
    def _get_connection(self):
        """Get database connection from the engine."""
        # Return the engine for compatibility, actual connections are managed by SQLAlchemy
        return DatabaseConnection.get_engine()
    
    def _init_database(self):
        """Create tables if they don't exist (idempotent schema initialization)."""
        engine = self._get_connection()
        
        # Use raw SQL for schema creation to ensure idempotency
        # Each DDL operation in its own transaction to prevent cascading failures
        
        # Main submissions table
        with engine.begin() as conn:
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS submissions (
                    id SERIAL PRIMARY KEY,
                    submission_date TIMESTAMP NOT NULL,
                    
                    -- Client details
                    client_name TEXT,
                    reference_number TEXT,
                    site_location TEXT,
                    
                    -- Location metadata
                    target_lpa TEXT,
                    target_nca TEXT,
                    target_lat FLOAT,
                    target_lon FLOAT,
                    lpa_neighbors TEXT[],
                    nca_neighbors TEXT[],
                    
                    -- Form inputs (demand)
                    demand_habitats JSONB,
                    
                    -- Optimization metadata
                    contract_size TEXT,
                    total_cost FLOAT,
                    admin_fee FLOAT,
                    total_with_admin FLOAT,
                    num_banks_selected INTEGER,
                    banks_used TEXT[],
                    
                    -- Manual entries
                    manual_hedgerow_entries JSONB,
                    manual_watercourse_entries JSONB,
                    manual_area_habitat_entries JSONB,
                    
                    -- Full allocation results (JSON)
                    allocation_results JSONB,
                    
                    -- User info
                    username TEXT,
                    
                    -- Promoter/Introducer info
                    promoter_name TEXT,
                    promoter_discount_type TEXT,
                    promoter_discount_value FLOAT
                )
            """))
        
        # Create indexes for submissions table
        with engine.begin() as conn:
            conn.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_submissions_date 
                ON submissions(submission_date DESC)
            """))
            conn.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_submissions_client 
                ON submissions(client_name)
            """))
            conn.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_submissions_lpa 
                ON submissions(target_lpa)
            """))
            conn.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_submissions_nca 
                ON submissions(target_nca)
            """))
        
        # Migrate submissions table to support 'no_discount' option
        # Drop and recreate the constraint if it exists with old values
        try:
            with engine.begin() as conn:
                conn.execute(text("""
                    DO $$
                    BEGIN
                        -- Drop old constraint if it exists
                        IF EXISTS (
                            SELECT 1 FROM pg_constraint 
                            WHERE conname = 'submissions_promoter_discount_type_check'
                        ) THEN
                            ALTER TABLE submissions DROP CONSTRAINT submissions_promoter_discount_type_check;
                        END IF;
                        
                        -- Add new constraint with 'no_discount' option
                        ALTER TABLE submissions ADD CONSTRAINT submissions_promoter_discount_type_check 
                        CHECK(promoter_discount_type IS NULL OR promoter_discount_type IN ('tier_up', 'percentage', 'no_discount'));
                    EXCEPTION
                        WHEN OTHERS THEN
                            -- Constraint doesn't exist or already updated, continue
                            NULL;
                    END $$;
                """))
        except Exception:
            # Table might not exist yet or constraint already correct
            pass
        
        # Add manual_area_habitat_entries column if it doesn't exist
        try:
            with engine.begin() as conn:
                conn.execute(text("""
                    DO $$
                    BEGIN
                        IF NOT EXISTS (
                            SELECT 1 FROM information_schema.columns 
                            WHERE table_name = 'submissions' 
                            AND column_name = 'manual_area_habitat_entries'
                        ) THEN
                            ALTER TABLE submissions ADD COLUMN manual_area_habitat_entries JSONB;
                        END IF;
                    END $$;
                """))
        except Exception:
            # Column might already exist
            pass
        
        # Drop the old view if it exists (replaced with physical table)
        try:
            with engine.begin() as conn:
                conn.execute(text("DROP VIEW IF EXISTS submissions_attio CASCADE;"))
        except Exception:
            pass
        
        # Create Attio-compatible physical table for StackSync integration
        # Physical table is required for PostgreSQL logical replication (realtime sync)
        # Converts JSONB to TEXT and adjusts types to match Attio schema
        try:
            with engine.begin() as conn:
                conn.execute(text("""
                    CREATE TABLE IF NOT EXISTS submissions_attio (
                        id INTEGER PRIMARY KEY,
                        submission_date DATE,
                        customer_id INTEGER,
                        client_name TEXT,
                        email TEXT,
                        mobile_number TEXT,
                        reference_number TEXT,
                        site_location JSONB,
                        target_lpa TEXT,
                        target_nca TEXT,
                        target_lat TEXT,
                        target_lon TEXT,
                        demand_habitats TEXT,
                        contract_size TEXT,
                        total_cost FLOAT,
                        total_with_admin FLOAT,
                        num_banks_selected INTEGER,
                        banks_selected TEXT,
                        watercourse_entries TEXT,
                        allocation_results TEXT,
                        promoter TEXT,
                        discount_type TEXT,
                        discount_value FLOAT
                    );
                """))
        except Exception:
            # Table might already exist
            pass
        
        # Add customer_id and client_name columns for Attio compatibility
        try:
            with engine.begin() as conn:
                conn.execute(text("""
                    DO $$
                    BEGIN
                        -- Add customer_id column if it doesn't exist (for proper relational linking)
                        IF NOT EXISTS (
                            SELECT 1 FROM information_schema.columns 
                            WHERE table_name = 'submissions_attio' AND column_name = 'customer_id'
                        ) THEN
                            ALTER TABLE submissions_attio ADD COLUMN customer_id INTEGER;
                        END IF;
                        
                        -- Add client_name column if it doesn't exist (for StackSync compatibility)
                        IF NOT EXISTS (
                            SELECT 1 FROM information_schema.columns 
                            WHERE table_name = 'submissions_attio' AND column_name = 'client_name'
                        ) THEN
                            ALTER TABLE submissions_attio ADD COLUMN client_name TEXT;
                        END IF;
                    END $$;
                """))
        except Exception:
            # Migration might fail if columns already exist
            pass
        
        # Add email and mobile_number columns to existing submissions_attio table if they don't exist
        try:
            with engine.begin() as conn:
                conn.execute(text("""
                    DO $$
                    BEGIN
                        IF NOT EXISTS (
                            SELECT 1 FROM information_schema.columns 
                            WHERE table_name = 'submissions_attio' AND column_name = 'email'
                        ) THEN
                            ALTER TABLE submissions_attio ADD COLUMN email TEXT;
                        END IF;
                        
                        IF NOT EXISTS (
                            SELECT 1 FROM information_schema.columns 
                            WHERE table_name = 'submissions_attio' AND column_name = 'mobile_number'
                        ) THEN
                            ALTER TABLE submissions_attio ADD COLUMN mobile_number TEXT;
                        END IF;
                    END $$;
                """))
        except Exception:
            # Columns might already exist or table might not exist yet
            pass
        
        # Create trigger function to automatically sync submissions to submissions_attio
        try:
            with engine.begin() as conn:
                conn.execute(text("""
                    CREATE OR REPLACE FUNCTION sync_to_attio() 
                    RETURNS TRIGGER AS $$
                    DECLARE
                        customer_email TEXT;
                        customer_mobile TEXT;
                    BEGIN
                        -- Fetch email and mobile from customers table if customer_id exists
                        IF NEW.customer_id IS NOT NULL THEN
                            SELECT email, mobile_number INTO customer_email, customer_mobile
                            FROM customers WHERE id = NEW.customer_id;
                        END IF;
                        
                        INSERT INTO submissions_attio (
                            id,
                            submission_date,
                            customer_id,
                            client_name,
                            email,
                            mobile_number,
                            reference_number,
                            site_location,
                            target_lpa,
                            target_nca,
                            target_lat,
                            target_lon,
                            demand_habitats,
                            contract_size,
                            total_cost,
                            total_with_admin,
                            num_banks_selected,
                            banks_selected,
                            watercourse_entries,
                            allocation_results,
                            promoter,
                            discount_type,
                            discount_value
                        ) VALUES (
                            NEW.id,
                            DATE(NEW.submission_date),
                            NEW.customer_id,
                            NEW.client_name,
                            customer_email,
                            customer_mobile,
                            NEW.reference_number,
                            jsonb_build_object(
                                'line_1', COALESCE(NEW.site_location, ''),
                                'line_2', '',
                                'line_3', '',
                                'line_4', '',
                                'locality', '',
                                'region', '',
                                'postcode', '',
                                'country_code', 'GB',
                                'latitude', NEW.target_lat,
                                'longitude', NEW.target_lon
                            ),
                            NEW.target_lpa,
                            NEW.target_nca,
                            CAST(NEW.target_lat AS TEXT),
                            CAST(NEW.target_lon AS TEXT),
                            COALESCE(NEW.demand_habitats::TEXT, ''),
                            NEW.contract_size,
                            NEW.total_cost,
                            NEW.total_with_admin,
                            NEW.num_banks_selected,
                            COALESCE(NEW.banks_used::TEXT, ''),
                            COALESCE(NEW.manual_watercourse_entries::TEXT, ''),
                            COALESCE(NEW.allocation_results::TEXT, ''),
                            COALESCE(NEW.promoter_name, ''),
                            NEW.promoter_discount_type,
                            NEW.promoter_discount_value
                        )
                        ON CONFLICT (id) DO UPDATE SET
                            submission_date = EXCLUDED.submission_date,
                            customer_id = EXCLUDED.customer_id,
                            client_name = EXCLUDED.client_name,
                            email = EXCLUDED.email,
                            mobile_number = EXCLUDED.mobile_number,
                            reference_number = EXCLUDED.reference_number,
                            site_location = EXCLUDED.site_location,
                            target_lpa = EXCLUDED.target_lpa,
                            target_nca = EXCLUDED.target_nca,
                            target_lat = EXCLUDED.target_lat,
                            target_lon = EXCLUDED.target_lon,
                            demand_habitats = EXCLUDED.demand_habitats,
                            contract_size = EXCLUDED.contract_size,
                            total_cost = EXCLUDED.total_cost,
                            total_with_admin = EXCLUDED.total_with_admin,
                            num_banks_selected = EXCLUDED.num_banks_selected,
                            banks_selected = EXCLUDED.banks_selected,
                            watercourse_entries = EXCLUDED.watercourse_entries,
                            allocation_results = EXCLUDED.allocation_results,
                            promoter = EXCLUDED.promoter,
                            discount_type = EXCLUDED.discount_type,
                            discount_value = EXCLUDED.discount_value;
                        RETURN NEW;
                    END;
                    $$ LANGUAGE plpgsql;
                """))
        except Exception:
            pass
        
        # Create trigger on submissions table to automatically sync to submissions_attio
        try:
            with engine.begin() as conn:
                conn.execute(text("""
                    DROP TRIGGER IF EXISTS submissions_to_attio_trigger ON submissions;
                    CREATE TRIGGER submissions_to_attio_trigger
                    AFTER INSERT OR UPDATE ON submissions
                    FOR EACH ROW EXECUTE FUNCTION sync_to_attio();
                """))
        except Exception:
            pass
        
        # Create trigger for delete operations
        try:
            with engine.begin() as conn:
                conn.execute(text("""
                    CREATE OR REPLACE FUNCTION delete_from_attio() 
                    RETURNS TRIGGER AS $$
                    BEGIN
                        DELETE FROM submissions_attio WHERE id = OLD.id;
                        RETURN OLD;
                    END;
                    $$ LANGUAGE plpgsql;
                    
                    DROP TRIGGER IF EXISTS submissions_to_attio_delete_trigger ON submissions;
                    CREATE TRIGGER submissions_to_attio_delete_trigger
                    AFTER DELETE ON submissions
                    FOR EACH ROW EXECUTE FUNCTION delete_from_attio();
                """))
        except Exception:
            pass
        
        # Backfill existing submissions into submissions_attio table
        try:
            with engine.begin() as conn:
                conn.execute(text("""
                    INSERT INTO submissions_attio (
                        id, submission_date, customer_id, client_name, email, mobile_number, reference_number,
                        site_location, target_lpa, target_nca, target_lat, target_lon,
                        demand_habitats, contract_size, total_cost, total_with_admin,
                        num_banks_selected, banks_selected, watercourse_entries,
                        allocation_results, promoter, discount_type, discount_value
                    )
                    SELECT 
                        s.id,
                        DATE(s.submission_date),
                        s.customer_id,
                        s.client_name,
                        c.email,
                        c.mobile_number,
                        s.reference_number,
                        jsonb_build_object(
                            'line_1', COALESCE(s.site_location, ''),
                            'line_2', '',
                            'line_3', '',
                            'line_4', '',
                            'locality', '',
                            'region', '',
                            'postcode', '',
                            'country_code', 'GB',
                            'latitude', s.target_lat,
                            'longitude', s.target_lon
                        ),
                        s.target_lpa,
                        s.target_nca,
                        CAST(s.target_lat AS TEXT),
                        CAST(s.target_lon AS TEXT),
                        COALESCE(s.demand_habitats::TEXT, ''),
                        s.contract_size,
                        s.total_cost,
                        s.total_with_admin,
                        s.num_banks_selected,
                        COALESCE(s.banks_used::TEXT, ''),
                        COALESCE(s.manual_watercourse_entries::TEXT, ''),
                        COALESCE(s.allocation_results::TEXT, ''),
                        COALESCE(s.promoter_name, ''),
                        s.promoter_discount_type,
                        s.promoter_discount_value
                    FROM submissions s
                    LEFT JOIN customers c ON s.customer_id = c.id
                    ON CONFLICT (id) DO NOTHING;
                """))
        except Exception:
            # Backfill may fail if data already exists or other issues
            pass
        
        # Allocations detail table (normalized)
        with engine.begin() as conn:
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS allocation_details (
                    id SERIAL PRIMARY KEY,
                    submission_id INTEGER NOT NULL,
                    
                    -- Allocation specifics
                    bank_key TEXT,
                    bank_name TEXT,
                    demand_habitat TEXT,
                    supply_habitat TEXT,
                    allocation_type TEXT,
                    tier TEXT,
                    units_supplied FLOAT,
                    unit_price FLOAT,
                    cost FLOAT,
                    
                    FOREIGN KEY (submission_id) REFERENCES submissions(id) ON DELETE CASCADE
                )
            """))
            
            # Create index for allocation_details
            conn.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_allocation_details_submission 
                ON allocation_details(submission_id)
            """))
            
            # Introducers/Promoters table
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS introducers (
                    id SERIAL PRIMARY KEY,
                    name TEXT NOT NULL UNIQUE,
                    discount_type TEXT NOT NULL CHECK(discount_type IN ('tier_up', 'percentage', 'no_discount')),
                    discount_value FLOAT NOT NULL,
                    created_date TIMESTAMP NOT NULL,
                    updated_date TIMESTAMP NOT NULL
                )
            """))
            
            # Migrate existing introducers table to support 'no_discount' option
            # Drop and recreate the constraint to add 'no_discount' option
            try:
                # Check if the constraint needs updating
                conn.execute(text("""
                    DO $$
                    BEGIN
                        -- Drop old constraint if it exists
                        IF EXISTS (
                            SELECT 1 FROM pg_constraint 
                            WHERE conname = 'introducers_discount_type_check'
                        ) THEN
                            ALTER TABLE introducers DROP CONSTRAINT introducers_discount_type_check;
                        END IF;
                        
                        -- Add new constraint with 'no_discount' option
                        ALTER TABLE introducers ADD CONSTRAINT introducers_discount_type_check 
                        CHECK(discount_type IN ('tier_up', 'percentage', 'no_discount'));
                    EXCEPTION
                        WHEN OTHERS THEN
                            -- Constraint doesn't exist or already updated, continue
                            NULL;
                    END $$;
                """))
            except Exception:
                # Table might not exist yet or constraint already correct
                pass
            
            # Create index for introducers
            conn.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_introducers_name 
                ON introducers(name)
            """))
            
            # Customers table
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS customers (
                    id SERIAL PRIMARY KEY,
                    client_name TEXT,
                    title TEXT,
                    first_name TEXT,
                    last_name TEXT,
                    company_name TEXT,
                    contact_person TEXT,
                    address TEXT,
                    email TEXT,
                    mobile_number TEXT,
                    created_date TIMESTAMP NOT NULL DEFAULT NOW(),
                    updated_date TIMESTAMP NOT NULL DEFAULT NOW()
                )
            """))
            
            # Remove NOT NULL constraint from client_name to allow Attio reverse sync
            conn.execute(text("""
                DO $$
                BEGIN
                    ALTER TABLE customers ALTER COLUMN client_name DROP NOT NULL;
                EXCEPTION
                    WHEN undefined_column THEN
                        -- Column doesn't exist yet, ignore
                        NULL;
                    WHEN others THEN
                        -- Constraint already removed or other issue, continue
                        NULL;
                END $$;
            """))
            
            # Drop the old constraint if it exists (it was causing issues with NULL values)
            conn.execute(text("""
                DO $$
                BEGIN
                    IF EXISTS (
                        SELECT 1 FROM pg_constraint 
                        WHERE conname = 'customers_unique_email_mobile'
                    ) THEN
                        ALTER TABLE customers DROP CONSTRAINT customers_unique_email_mobile;
                    END IF;
                END $$;
            """))
            
            # Add unique index for email when not NULL
            conn.execute(text("""
                DO $$
                BEGIN
                    IF NOT EXISTS (
                        SELECT 1 FROM pg_indexes 
                        WHERE indexname = 'customers_unique_email'
                    ) THEN
                        CREATE UNIQUE INDEX customers_unique_email ON customers(email) WHERE email IS NOT NULL;
                    END IF;
                END $$;
            """))
            
            # Add unique index for mobile when not NULL
            conn.execute(text("""
                DO $$
                BEGIN
                    IF NOT EXISTS (
                        SELECT 1 FROM pg_indexes 
                        WHERE indexname = 'customers_unique_mobile'
                    ) THEN
                        CREATE UNIQUE INDEX customers_unique_mobile ON customers(mobile_number) WHERE mobile_number IS NOT NULL;
                    END IF;
                END $$;
            """))
            
            # Add new columns to existing customers table if they don't exist
            conn.execute(text("""
                DO $$
                BEGIN
                    IF NOT EXISTS (
                        SELECT 1 FROM information_schema.columns 
                        WHERE table_name = 'customers' AND column_name = 'title'
                    ) THEN
                        ALTER TABLE customers ADD COLUMN title TEXT;
                    END IF;
                    IF NOT EXISTS (
                        SELECT 1 FROM information_schema.columns 
                        WHERE table_name = 'customers' AND column_name = 'first_name'
                    ) THEN
                        ALTER TABLE customers ADD COLUMN first_name TEXT;
                    END IF;
                    IF NOT EXISTS (
                        SELECT 1 FROM information_schema.columns 
                        WHERE table_name = 'customers' AND column_name = 'last_name'
                    ) THEN
                        ALTER TABLE customers ADD COLUMN last_name TEXT;
                    END IF;
                END $$;
            """))
            
            # CRITICAL DATA CLEANUP: Fix data corrupted during Attio sync attempts
            conn.execute(text("""
                DO $$
                BEGIN
                    -- Step 1: Extract data from JSONB columns back to TEXT (if JSONB columns exist)
                    IF EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'customers' AND column_name = 'personal_name') THEN
                        -- Extract first_name from personal_name JSONB if first_name is NULL
                        UPDATE customers 
                        SET first_name = personal_name->>'first_name'
                        WHERE first_name IS NULL AND personal_name IS NOT NULL AND personal_name->>'first_name' != '';
                        
                        -- Extract last_name from personal_name JSONB if last_name is NULL
                        UPDATE customers 
                        SET last_name = personal_name->>'last_name'
                        WHERE last_name IS NULL AND personal_name IS NOT NULL AND personal_name->>'last_name' != '';
                    END IF;
                    
                    IF EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'customers' AND column_name = 'email_addresses') THEN
                        -- Extract email from email_addresses JSONB array
                        UPDATE customers 
                        SET email = email_addresses->0->>'email_address'
                        WHERE email IS NULL AND email_addresses IS NOT NULL 
                        AND jsonb_array_length(email_addresses) > 0;
                    END IF;
                    
                    IF EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'customers' AND column_name = 'phone_numbers') THEN
                        -- Extract phone from phone_numbers JSONB array
                        UPDATE customers 
                        SET mobile_number = phone_numbers->0->>'original_phone_number'
                        WHERE mobile_number IS NULL AND phone_numbers IS NOT NULL 
                        AND jsonb_array_length(phone_numbers) > 0;
                    END IF;
                    
                    IF EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'customers' AND column_name = 'companies') THEN
                        -- Extract company from companies JSONB array
                        UPDATE customers 
                        SET company_name = companies->0
                        WHERE company_name IS NULL AND companies IS NOT NULL 
                        AND jsonb_array_length(companies) > 0;
                    END IF;
                    
                    -- Step 2: Clean up any JSON strings that got stored in TEXT columns
                    -- Fix last_name if it contains JSON
                    UPDATE customers 
                    SET last_name = TRIM(BOTH '"' FROM (last_name::jsonb->>'last_name'))
                    WHERE last_name LIKE '{%' AND last_name::text ~ '^\{.*\}$';
                    
                    -- Fix email if it contains JSON  
                    UPDATE customers 
                    SET email = TRIM(BOTH '"' FROM (email::jsonb->0->>'email_address'))
                    WHERE email LIKE '[{%' AND email::text ~ '^\[\{.*\}\]$';
                    
                    -- Step 3: Rebuild client_name from first_name and last_name
                    UPDATE customers 
                    SET client_name = TRIM(COALESCE(first_name, '') || ' ' || COALESCE(last_name, ''))
                    WHERE (client_name IS NULL OR client_name = '') 
                    AND (first_name IS NOT NULL OR last_name IS NOT NULL);
                    
                    -- Set client_name to 'Unknown' for completely empty records
                    UPDATE customers 
                    SET client_name = 'Unknown'
                    WHERE client_name IS NULL OR TRIM(client_name) = '';
                    
                    -- Step 4: Now drop the JSONB columns
                    IF EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'customers' AND column_name = 'personal_name') THEN
                        ALTER TABLE customers DROP COLUMN personal_name;
                    END IF;
                    IF EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'customers' AND column_name = 'email_addresses') THEN
                        ALTER TABLE customers DROP COLUMN email_addresses;
                    END IF;
                    IF EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'customers' AND column_name = 'phone_numbers') THEN
                        ALTER TABLE customers DROP COLUMN phone_numbers;
                    END IF;
                    IF EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'customers' AND column_name = 'companies') THEN
                        ALTER TABLE customers DROP COLUMN companies;
                    END IF;
                END $$;
            """))
            
            # Drop old trigger if it exists
            conn.execute(text("""
                DROP TRIGGER IF EXISTS sync_customer_attio_trigger ON customers;
                DROP FUNCTION IF EXISTS sync_customer_attio_fields();
            """))
            
            # Create simple trigger to populate client_name from first_name/last_name
            conn.execute(text(r"""
                CREATE OR REPLACE FUNCTION sync_customer_name() 
                RETURNS TRIGGER AS $$
                BEGIN
                    -- Auto-populate client_name if it's empty
                    IF NEW.client_name IS NULL OR NEW.client_name = '' THEN
                        IF NEW.first_name IS NOT NULL OR NEW.last_name IS NOT NULL THEN
                            NEW.client_name = TRIM(COALESCE(NEW.first_name, '') || ' ' || COALESCE(NEW.last_name, ''));
                            IF NEW.client_name = '' THEN
                                NEW.client_name = 'Unknown';
                            END IF;
                        ELSE
                            NEW.client_name = 'Unknown';
                        END IF;
                    END IF;
                    
                    -- Sync personal_name from first_name and last_name
                    -- Attio requires at least one of: first_name, last_name, or full_name
                    IF NEW.first_name IS NOT NULL OR NEW.last_name IS NOT NULL THEN
                        DECLARE
                            full_name_value TEXT;
                        BEGIN
                            full_name_value = TRIM(COALESCE(NEW.first_name, '') || ' ' || COALESCE(NEW.last_name, ''));
                            -- Ensure full_name is never just empty string
                            IF full_name_value = '' THEN
                                full_name_value = COALESCE(NEW.first_name, NEW.last_name, 'Unknown');
                            END IF;
                            
                            NEW.personal_name = jsonb_build_object(
                                'first_name', COALESCE(NEW.first_name, ''),
                                'last_name', COALESCE(NEW.last_name, ''),
                                'full_name', full_name_value
                            );
                        END;
                    ELSIF NEW.personal_name IS NOT NULL THEN
                        -- Sync back from personal_name to TEXT fields if they're null
                        IF NEW.first_name IS NULL THEN
                            NEW.first_name = NEW.personal_name->>'first_name';
                        END IF;
                        IF NEW.last_name IS NULL THEN
                            NEW.last_name = NEW.personal_name->>'last_name';
                        END IF;
                    END IF;
                    
                    -- Sync email_addresses from email
                    -- Only add if email is valid (basic validation: has @ and text on both sides)
                    IF NEW.email IS NOT NULL AND NEW.email != '' AND 
                       NEW.email ~ '^[^@]+@[^@]+\.[^@]+$' THEN
                        NEW.email_addresses = jsonb_build_array(
                            jsonb_build_object(
                                'email_address', NEW.email
                            )
                        );
                    ELSIF NEW.email_addresses IS NOT NULL AND jsonb_array_length(NEW.email_addresses) > 0 THEN
                        -- Sync back from email_addresses to email if email is null
                        -- Only extract if it's a valid email
                        DECLARE
                            extracted_email TEXT;
                        BEGIN
                            extracted_email = NEW.email_addresses->0->>'email_address';
                            IF extracted_email IS NOT NULL AND extracted_email != '' AND
                               extracted_email ~ '^[^@]+@[^@]+\.[^@]+$' THEN
                                IF NEW.email IS NULL OR NEW.email = '' THEN
                                    NEW.email = extracted_email;
                                END IF;
                            END IF;
                        END;
                    ELSE
                        NEW.email_addresses = '[]'::jsonb;
                    END IF;
                    
                    -- Sync phone_numbers from mobile_number
                    -- Attio requires: original_phone_number and country_code
                    IF NEW.mobile_number IS NOT NULL AND NEW.mobile_number != '' THEN
                        NEW.phone_numbers = jsonb_build_array(
                            jsonb_build_object(
                                'original_phone_number', NEW.mobile_number,
                                'country_code', 'GB'
                            )
                        );
                    ELSIF NEW.phone_numbers IS NOT NULL AND jsonb_array_length(NEW.phone_numbers) > 0 THEN
                        -- Sync back from phone_numbers to mobile_number if mobile_number is null
                        IF NEW.mobile_number IS NULL OR NEW.mobile_number = '' THEN
                            NEW.mobile_number = NEW.phone_numbers->0->>'original_phone_number';
                        END IF;
                    ELSE
                        NEW.phone_numbers = '[]'::jsonb;
                    END IF;
                    
                    -- Sync companies from company_name
                    IF NEW.company_name IS NOT NULL AND NEW.company_name != '' THEN
                        NEW.companies = jsonb_build_array(NEW.company_name);
                    ELSIF NEW.companies IS NOT NULL AND jsonb_array_length(NEW.companies) > 0 THEN
                        -- Sync back from companies to company_name if company_name is null
                        IF NEW.company_name IS NULL OR NEW.company_name = '' THEN
                            NEW.company_name = NEW.companies->0::text;
                            -- Remove quotes if present
                            NEW.company_name = TRIM(BOTH '"' FROM NEW.company_name);
                        END IF;
                    ELSE
                        NEW.companies = '[]'::jsonb;
                    END IF;
                    
                    RETURN NEW;
                END;
                $$ LANGUAGE plpgsql;
            """))
            
            # Create trigger on customers table
            conn.execute(text("""
                DROP TRIGGER IF EXISTS sync_customer_attio_fields_trigger ON customers;
                CREATE TRIGGER sync_customer_attio_fields_trigger
                BEFORE INSERT OR UPDATE ON customers
                FOR EACH ROW EXECUTE FUNCTION sync_customer_attio_fields();
            """))
            
            # Backfill Attio-compatible fields for existing customers
            conn.execute(text(r"""
                UPDATE customers SET
                    personal_name = jsonb_build_object(
                        'first_name', COALESCE(first_name, ''),
                        'last_name', COALESCE(last_name, ''),
                        'full_name', TRIM(COALESCE(first_name, '') || ' ' || COALESCE(last_name, ''))
                    ),
                    email_addresses = CASE 
                        WHEN email IS NOT NULL AND email != '' AND email ~ '^[^@]+@[^@]+\.[^@]+$' THEN
                            jsonb_build_array(
                                jsonb_build_object(
                                    'email_address', email
                                )
                            )
                        ELSE '[]'::jsonb
                    END,
                    phone_numbers = CASE 
                        WHEN mobile_number IS NOT NULL AND mobile_number != '' THEN
                            jsonb_build_array(
                                jsonb_build_object(
                                    'original_phone_number', mobile_number,
                                    'country_code', 'GB'
                                )
                            )
                        ELSE '[]'::jsonb
                    END,
                    companies = CASE 
                        WHEN company_name IS NOT NULL AND company_name != '' THEN
                            jsonb_build_array(company_name)
                        ELSE '[]'::jsonb
                    END
                WHERE personal_name IS NULL OR email_addresses IS NULL OR phone_numbers IS NULL OR companies IS NULL;
            """))
            
            # Create indexes for customers
            conn.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_customers_email 
                ON customers(email)
            """))
            conn.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_customers_mobile 
                ON customers(mobile_number)
            """))
            conn.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_customers_client_name 
                ON customers(client_name)
            """))
            
            # Add customer_id to submissions table if not exists
            conn.execute(text("""
                DO $$
                BEGIN
                    IF NOT EXISTS (
                        SELECT 1 FROM information_schema.columns 
                        WHERE table_name = 'submissions' AND column_name = 'customer_id'
                    ) THEN
                        ALTER TABLE submissions ADD COLUMN customer_id INTEGER;
                        ALTER TABLE submissions ADD CONSTRAINT fk_submissions_customer 
                        FOREIGN KEY (customer_id) REFERENCES customers(id) ON DELETE SET NULL;
                        CREATE INDEX idx_submissions_customer ON submissions(customer_id);
                    END IF;
                END $$;
            """))
            
            conn.commit()
    
    def close(self):
        """Close the database connection."""
        # Connection is managed by SQLAlchemy pool, no explicit close needed
        # This method is kept for backward compatibility
        pass
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        retry=retry_if_exception_type((Exception,)),
        reraise=True
    )
    def store_submission(self, 
                        client_name: str,
                        reference_number: str,
                        site_location: str,
                        target_lpa: str,
                        target_nca: str,
                        target_lat: Optional[float],
                        target_lon: Optional[float],
                        lpa_neighbors: List[str],
                        nca_neighbors: List[str],
                        demand_df: pd.DataFrame,
                        allocation_df: pd.DataFrame,
                        contract_size: str,
                        total_cost: float,
                        admin_fee: float,
                        manual_hedgerow_rows: List[Dict],
                        manual_watercourse_rows: List[Dict],
                        manual_area_habitat_rows: Optional[List[Dict]] = None,
                        username: str = "",
                        promoter_name: Optional[str] = None,
                        promoter_discount_type: Optional[str] = None,
                        promoter_discount_value: Optional[float] = None,
                        customer_id: Optional[int] = None) -> int:
        """
        Store a complete submission to the database.
        Returns the submission_id for reference.
        
        Uses transactions and automatic retry on transient failures.
        """
        engine = self._get_connection()
        
        # Prepare data
        submission_date = datetime.now()
        total_with_admin = float(total_cost) + float(admin_fee)
        
        # Banks used - ensure it's a proper list of strings
        banks_used = allocation_df["BANK_KEY"].unique().tolist() if not allocation_df.empty else []
        banks_used = [str(bank) for bank in banks_used]  # Ensure all are strings
        num_banks = len(banks_used)
        
        # Sanitize array fields - convert to JSON strings for JSONB columns
        lpa_neighbors_json = json.dumps([str(item) for item in lpa_neighbors]) if lpa_neighbors else json.dumps([])
        nca_neighbors_json = json.dumps([str(item) for item in nca_neighbors]) if nca_neighbors else json.dumps([])
        banks_used_json = json.dumps([str(bank) for bank in banks_used])
        
        # Convert DataFrames to JSON for JSONB storage
        # Sanitize to ensure all numpy/Decimal types are converted
        demand_habitats_json = json.loads(demand_df.to_json(orient='records')) if not demand_df.empty else []
        demand_habitats_json = sanitize_for_db(demand_habitats_json)
        
        allocation_results_json = json.loads(allocation_df.to_json(orient='records')) if not allocation_df.empty else []
        allocation_results_json = sanitize_for_db(allocation_results_json)
        
        # Sanitize manual entries
        manual_hedgerow_rows_clean = sanitize_for_db(manual_hedgerow_rows)
        manual_watercourse_rows_clean = sanitize_for_db(manual_watercourse_rows)
        manual_area_habitat_rows_clean = sanitize_for_db(manual_area_habitat_rows) if manual_area_habitat_rows else []
        
        # Sanitize numeric fields
        target_lat_clean = float(target_lat) if target_lat is not None else None
        target_lon_clean = float(target_lon) if target_lon is not None else None
        total_cost_clean = float(total_cost)
        admin_fee_clean = float(admin_fee)
        promoter_discount_value_clean = float(promoter_discount_value) if promoter_discount_value is not None else None
        
        with engine.connect() as conn:
            # Start transaction
            trans = conn.begin()
            try:
                # Insert main submission
                result = conn.execute(text("""
                    INSERT INTO submissions (
                        submission_date, client_name, reference_number, site_location,
                        target_lpa, target_nca, target_lat, target_lon,
                        lpa_neighbors, nca_neighbors, demand_habitats,
                        contract_size, total_cost, admin_fee, total_with_admin,
                        num_banks_selected, banks_used,
                        manual_hedgerow_entries, manual_watercourse_entries, manual_area_habitat_entries,
                        allocation_results, username,
                        promoter_name, promoter_discount_type, promoter_discount_value,
                        customer_id
                    ) VALUES (
                        :submission_date, :client_name, :reference_number, :site_location,
                        :target_lpa, :target_nca, :target_lat, :target_lon,
                        :lpa_neighbors, :nca_neighbors, :demand_habitats,
                        :contract_size, :total_cost, :admin_fee, :total_with_admin,
                        :num_banks_selected, :banks_used,
                        :manual_hedgerow_entries, :manual_watercourse_entries, :manual_area_habitat_entries,
                        :allocation_results, :username,
                        :promoter_name, :promoter_discount_type, :promoter_discount_value,
                        :customer_id
                    ) RETURNING id
                """), {
                    "submission_date": submission_date,
                    "client_name": client_name,
                    "reference_number": reference_number,
                    "site_location": site_location,
                    "target_lpa": target_lpa,
                    "target_nca": target_nca,
                    "target_lat": target_lat_clean,
                    "target_lon": target_lon_clean,
                    "lpa_neighbors": lpa_neighbors_json,  # JSONB
                    "nca_neighbors": nca_neighbors_json,  # JSONB
                    "demand_habitats": json.dumps(demand_habitats_json),  # JSONB
                    "contract_size": contract_size,
                    "total_cost": total_cost_clean,
                    "admin_fee": admin_fee_clean,
                    "total_with_admin": total_with_admin,
                    "num_banks_selected": num_banks,
                    "banks_used": banks_used_json,  # JSONB
                    "manual_hedgerow_entries": json.dumps(manual_hedgerow_rows_clean),  # JSONB
                    "manual_watercourse_entries": json.dumps(manual_watercourse_rows_clean),  # JSONB
                    "manual_area_habitat_entries": json.dumps(manual_area_habitat_rows_clean),  # JSONB
                    "allocation_results": json.dumps(allocation_results_json),  # JSONB
                    "username": username,
                    "promoter_name": promoter_name,
                    "promoter_discount_type": promoter_discount_type,
                    "promoter_discount_value": promoter_discount_value_clean,
                    "customer_id": customer_id
                })
                
                submission_id = result.fetchone()[0]
                
                # Insert allocation details
                if not allocation_df.empty:
                    for _, row in allocation_df.iterrows():
                        # Sanitize row data
                        row_dict = {
                            "submission_id": submission_id,
                            "bank_key": str(row.get("BANK_KEY", "")),
                            "bank_name": str(row.get("bank_name", "")),
                            "demand_habitat": str(row.get("demand_habitat", "")),
                            "supply_habitat": str(row.get("supply_habitat", "")),
                            "allocation_type": str(row.get("allocation_type", "")),
                            "tier": str(row.get("proximity", "")),
                            "units_supplied": float(sanitize_for_db(row.get("units_supplied", 0.0))),
                            "unit_price": float(sanitize_for_db(row.get("unit_price", 0.0))),
                            "cost": float(sanitize_for_db(row.get("cost", 0.0)))
                        }
                        
                        conn.execute(text("""
                            INSERT INTO allocation_details (
                                submission_id, bank_key, bank_name,
                                demand_habitat, supply_habitat, allocation_type,
                                tier, units_supplied, unit_price, cost
                            ) VALUES (
                                :submission_id, :bank_key, :bank_name,
                                :demand_habitat, :supply_habitat, :allocation_type,
                                :tier, :units_supplied, :unit_price, :cost
                            )
                        """), row_dict)
                
                # Commit transaction
                trans.commit()
                return submission_id
                
            except Exception as e:
                # Rollback on error
                trans.rollback()
                raise
    
    def get_all_submissions(self, limit: Optional[int] = None) -> pd.DataFrame:
        """Get all submissions as a DataFrame."""
        query = "SELECT * FROM submissions ORDER BY submission_date DESC"
        if limit:
            query += f" LIMIT {limit}"
        
        engine = self._get_connection()
        with engine.connect() as conn:
            df = pd.read_sql_query(query, conn)
        return df
    
    def get_submission_by_id(self, submission_id: int) -> Optional[Dict[str, Any]]:
        """Get a specific submission by ID."""
        engine = self._get_connection()
        with engine.connect() as conn:
            result = conn.execute(
                text("SELECT * FROM submissions WHERE id = :id"),
                {"id": submission_id}
            )
            row = result.fetchone()
            
            if row:
                # Convert row to dictionary
                return dict(row._mapping)
            return None
    
    def get_allocations_for_submission(self, submission_id: int) -> pd.DataFrame:
        """Get allocation details for a specific submission."""
        engine = self._get_connection()
        with engine.connect() as conn:
            df = pd.read_sql_query(
                "SELECT * FROM allocation_details WHERE submission_id = %(submission_id)s",
                conn,
                params={"submission_id": submission_id}
            )
        return df
    
    def filter_submissions(self,
                          start_date: Optional[str] = None,
                          end_date: Optional[str] = None,
                          client_name: Optional[str] = None,
                          lpa: Optional[str] = None,
                          nca: Optional[str] = None,
                          reference_number: Optional[str] = None) -> pd.DataFrame:
        """Filter submissions based on various criteria."""
        query = "SELECT * FROM submissions WHERE 1=1"
        params = {}
        
        if start_date:
            query += " AND submission_date >= %(start_date)s"
            params["start_date"] = start_date
        
        if end_date:
            query += " AND submission_date <= %(end_date)s"
            params["end_date"] = end_date
        
        if client_name:
            query += " AND client_name ILIKE %(client_name)s"
            params["client_name"] = f"%{client_name}%"
        
        if lpa:
            query += " AND target_lpa ILIKE %(lpa)s"
            params["lpa"] = f"%{lpa}%"
        
        if nca:
            query += " AND target_nca ILIKE %(nca)s"
            params["nca"] = f"%{nca}%"
        
        if reference_number:
            query += " AND reference_number ILIKE %(reference_number)s"
            params["reference_number"] = f"%{reference_number}%"
        
        query += " ORDER BY submission_date DESC"
        
        engine = self._get_connection()
        with engine.connect() as conn:
            df = pd.read_sql_query(query, conn, params=params)
        return df
    
    def export_to_csv(self, df: pd.DataFrame, filename: str = "submissions_export.csv") -> bytes:
        """Export DataFrame to CSV bytes for download."""
        return df.to_csv(index=False).encode('utf-8')
    
    def get_summary_stats(self) -> Dict[str, Any]:
        """Get summary statistics about submissions."""
        engine = self._get_connection()
        with engine.connect() as conn:
            # Total submissions
            result = conn.execute(text("SELECT COUNT(*) FROM submissions"))
            total_submissions = result.fetchone()[0]
            
            # Total revenue
            result = conn.execute(text("SELECT SUM(total_with_admin) FROM submissions"))
            total_revenue = result.fetchone()[0] or 0.0
            
            # Most common LPAs
            result = conn.execute(text("""
                SELECT target_lpa, COUNT(*) as count 
                FROM submissions 
                WHERE target_lpa IS NOT NULL AND target_lpa != ''
                GROUP BY target_lpa 
                ORDER BY count DESC 
                LIMIT 5
            """))
            top_lpas = result.fetchall()
            
            # Most common clients
            result = conn.execute(text("""
                SELECT client_name, COUNT(*) as count 
                FROM submissions 
                WHERE client_name IS NOT NULL AND client_name != ''
                GROUP BY client_name 
                ORDER BY count DESC 
                LIMIT 5
            """))
            top_clients = result.fetchall()
            
            return {
                "total_submissions": total_submissions,
                "total_revenue": total_revenue,
                "top_lpas": top_lpas,
                "top_clients": top_clients
            }
    
    # ================= Introducers/Promoters CRUD =================
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        retry=retry_if_exception_type((Exception,)),
        reraise=True
    )
    def add_introducer(self, name: str, discount_type: str, discount_value: float) -> int:
        """Add a new introducer/promoter."""
        engine = self._get_connection()
        
        now = datetime.now()
        
        with engine.connect() as conn:
            trans = conn.begin()
            try:
                result = conn.execute(text("""
                    INSERT INTO introducers (name, discount_type, discount_value, created_date, updated_date)
                    VALUES (:name, :discount_type, :discount_value, :created_date, :updated_date)
                    RETURNING id
                """), {
                    "name": name,
                    "discount_type": discount_type,
                    "discount_value": discount_value,
                    "created_date": now,
                    "updated_date": now
                })
                
                introducer_id = result.fetchone()[0]
                trans.commit()
                return introducer_id
            except Exception as e:
                trans.rollback()
                raise
    
    def get_all_introducers(self) -> List[Dict[str, Any]]:
        """Get all introducers."""
        engine = self._get_connection()
        with engine.connect() as conn:
            result = conn.execute(text("SELECT * FROM introducers ORDER BY name"))
            rows = result.fetchall()
            
            return [dict(row._mapping) for row in rows]
    
    def get_introducer_by_name(self, name: str) -> Optional[Dict[str, Any]]:
        """Get an introducer by name."""
        engine = self._get_connection()
        with engine.connect() as conn:
            result = conn.execute(
                text("SELECT * FROM introducers WHERE name = :name"),
                {"name": name}
            )
            row = result.fetchone()
            
            if row:
                return dict(row._mapping)
            return None
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        retry=retry_if_exception_type((Exception,)),
        reraise=True
    )
    def update_introducer(self, introducer_id: int, name: str, discount_type: str, discount_value: float):
        """Update an existing introducer."""
        engine = self._get_connection()
        
        now = datetime.now()
        
        with engine.connect() as conn:
            trans = conn.begin()
            try:
                conn.execute(text("""
                    UPDATE introducers 
                    SET name = :name, discount_type = :discount_type, 
                        discount_value = :discount_value, updated_date = :updated_date
                    WHERE id = :id
                """), {
                    "name": name,
                    "discount_type": discount_type,
                    "discount_value": discount_value,
                    "updated_date": now,
                    "id": introducer_id
                })
                
                trans.commit()
            except Exception as e:
                trans.rollback()
                raise
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        retry=retry_if_exception_type((Exception,)),
        reraise=True
    )
    def delete_introducer(self, introducer_id: int):
        """Delete an introducer."""
        engine = self._get_connection()
        
        with engine.connect() as conn:
            trans = conn.begin()
            try:
                conn.execute(
                    text("DELETE FROM introducers WHERE id = :id"),
                    {"id": introducer_id}
                )
                
                trans.commit()
            except Exception as e:
                trans.rollback()
                raise
    
    # ================= Customers CRUD =================
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        retry=retry_if_exception_type((Exception,)),
        reraise=True
    )
    def add_customer(self, client_name: str, title: Optional[str] = None,
                     first_name: Optional[str] = None, last_name: Optional[str] = None,
                     company_name: Optional[str] = None, contact_person: Optional[str] = None,
                     address: Optional[str] = None, email: Optional[str] = None,
                     mobile_number: Optional[str] = None) -> int:
        """
        Add a new customer or return existing customer with same email/mobile.
        
        Args:
            client_name: Display name for the customer (required)
            first_name: Customer's first name (required for Attio sync)
            last_name: Customer's last name (required for Attio sync)
            title: Title (Mr, Mrs, etc.)
            company_name: Company name
            contact_person: Contact person name
            address: Customer address
            email: Email address (required for Attio sync)
            mobile_number: Mobile phone number
            
        Returns:
            Customer ID
            
        Raises:
            ValueError: If first_name or last_name is missing
        """
        # Validate required fields for Attio sync
        if not first_name or not first_name.strip():
            raise ValueError("First name is required for customer records")
        if not last_name or not last_name.strip():
            raise ValueError("Last name is required for customer records")
        
        engine = self._get_connection()
        
        now = datetime.now()
        
        with engine.connect() as conn:
            trans = conn.begin()
            try:
                # Check if customer exists with same email or mobile
                if email or mobile_number:
                    result = conn.execute(text("""
                        SELECT id FROM customers 
                        WHERE (email = :email AND email IS NOT NULL) 
                           OR (mobile_number = :mobile AND mobile_number IS NOT NULL)
                        LIMIT 1
                    """), {"email": email, "mobile": mobile_number})
                    existing = result.fetchone()
                    if existing:
                        trans.rollback()
                        return existing[0]
                
                # Insert new customer
                result = conn.execute(text("""
                    INSERT INTO customers (client_name, title, first_name, last_name, 
                                          company_name, contact_person, address, 
                                          email, mobile_number, created_date, updated_date)
                    VALUES (:client_name, :title, :first_name, :last_name,
                           :company_name, :contact_person, :address,
                           :email, :mobile_number, :created_date, :updated_date)
                    RETURNING id
                """), {
                    "client_name": client_name,
                    "title": title,
                    "first_name": first_name,
                    "last_name": last_name,
                    "company_name": company_name,
                    "contact_person": contact_person,
                    "address": address,
                    "email": email,
                    "mobile_number": mobile_number,
                    "created_date": now,
                    "updated_date": now
                })
                
                customer_id = result.fetchone()[0]
                trans.commit()
                return customer_id
            except Exception as e:
                trans.rollback()
                raise
    
    def get_customer_by_id(self, customer_id: int) -> Optional[Dict[str, Any]]:
        """Get a customer by ID."""
        engine = self._get_connection()
        with engine.connect() as conn:
            result = conn.execute(
                text("SELECT * FROM customers WHERE id = :id"),
                {"id": customer_id}
            )
            row = result.fetchone()
            return dict(row._mapping) if row else None
    
    def get_customer_by_contact(self, email: Optional[str] = None, 
                                mobile_number: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Get a customer by email or mobile number."""
        engine = self._get_connection()
        with engine.connect() as conn:
            result = conn.execute(text("""
                SELECT * FROM customers 
                WHERE (email = :email AND email IS NOT NULL) 
                   OR (mobile_number = :mobile AND mobile_number IS NOT NULL)
                LIMIT 1
            """), {"email": email, "mobile": mobile_number})
            row = result.fetchone()
            return dict(row._mapping) if row else None
    
    def get_all_customers(self) -> List[Dict[str, Any]]:
        """Get all customers."""
        engine = self._get_connection()
        with engine.connect() as conn:
            result = conn.execute(text("SELECT * FROM customers ORDER BY created_date DESC"))
            rows = result.fetchall()
            return [dict(row._mapping) for row in rows]
    
    def update_customer(self, customer_id: int, client_name: Optional[str] = None,
                       title: Optional[str] = None, first_name: Optional[str] = None,
                       last_name: Optional[str] = None, company_name: Optional[str] = None,
                       contact_person: Optional[str] = None, address: Optional[str] = None,
                       email: Optional[str] = None, mobile_number: Optional[str] = None):
        """Update a customer."""
        engine = self._get_connection()
        
        with engine.connect() as conn:
            trans = conn.begin()
            try:
                # Build dynamic update query
                updates = []
                params = {"id": customer_id, "updated_date": datetime.now()}
                
                if client_name is not None:
                    updates.append("client_name = :client_name")
                    params["client_name"] = client_name
                if title is not None:
                    updates.append("title = :title")
                    params["title"] = title
                if first_name is not None:
                    updates.append("first_name = :first_name")
                    params["first_name"] = first_name
                if last_name is not None:
                    updates.append("last_name = :last_name")
                    params["last_name"] = last_name
                if company_name is not None:
                    updates.append("company_name = :company_name")
                    params["company_name"] = company_name
                if contact_person is not None:
                    updates.append("contact_person = :contact_person")
                    params["contact_person"] = contact_person
                if address is not None:
                    updates.append("address = :address")
                    params["address"] = address
                if email is not None:
                    updates.append("email = :email")
                    params["email"] = email
                if mobile_number is not None:
                    updates.append("mobile_number = :mobile_number")
                    params["mobile_number"] = mobile_number
                
                updates.append("updated_date = :updated_date")
                
                if updates:
                    query = f"UPDATE customers SET {', '.join(updates)} WHERE id = :id"
                    conn.execute(text(query), params)
                    trans.commit()
                else:
                    trans.rollback()
            except Exception as e:
                trans.rollback()
                raise
    
    def populate_customers_from_submissions(self) -> tuple[int, list[str]]:
        """
        Populate customers table from existing submissions.
        Creates a customer record for each unique client_name in submissions
        that doesn't already have a customer record.
        Returns tuple of (number of customers created, list of error messages).
        """
        engine = self._get_connection()
        errors = []
        
        # Get distinct client names from all submissions
        with engine.connect() as conn:
            result = conn.execute(text("""
                SELECT DISTINCT client_name 
                FROM submissions 
                WHERE client_name IS NOT NULL 
                  AND client_name != ''
                ORDER BY client_name
            """))
            client_names = [row[0] for row in result.fetchall()]
        
        created_count = 0
        for client_name in client_names:
            try:
                # Use a fresh connection with transaction for each customer
                with engine.connect() as conn:
                    with conn.begin():
                        # Check if customer already exists with this name
                        check_result = conn.execute(text("""
                            SELECT id FROM customers WHERE client_name = :client_name LIMIT 1
                        """), {"client_name": client_name})
                        
                        existing_customer = check_result.fetchone()
                        
                        if existing_customer:
                            # Customer already exists, but update submissions that don't have customer_id set
                            customer_id = existing_customer[0]
                            conn.execute(text("""
                                UPDATE submissions 
                                SET customer_id = :customer_id 
                                WHERE client_name = :client_name AND customer_id IS NULL
                            """), {
                                "customer_id": customer_id,
                                "client_name": client_name
                            })
                        else:
                            # Create customer record
                            now = datetime.now()
                            insert_result = conn.execute(text("""
                                INSERT INTO customers (client_name, created_date, updated_date)
                                VALUES (:client_name, :created_date, :updated_date)
                                RETURNING id
                            """), {
                                "client_name": client_name,
                                "created_date": now,
                                "updated_date": now
                            })
                            
                            customer_id = insert_result.fetchone()[0]
                            
                            # Update submissions with this client_name to link to the new customer
                            conn.execute(text("""
                                UPDATE submissions 
                                SET customer_id = :customer_id 
                                WHERE client_name = :client_name AND customer_id IS NULL
                            """), {
                                "customer_id": customer_id,
                                "client_name": client_name
                            })
                            
                            created_count += 1
                    # Transaction auto-commits on successful exit from 'with conn.begin()'
                    
            except Exception as e:
                errors.append(f"Error processing '{client_name}': {str(e)}")
        
        return created_count, errors
    
    # ================= Quote/Requote Methods =================
    
    def get_next_revision_number(self, base_reference: str) -> str:
        """
        Get the next revision number for a reference.
        E.g., for BNG01234, returns BNG01234.1 if no revisions exist,
        or BNG01234.2 if BNG01234.1 exists, etc.
        """
        engine = self._get_connection()
        
        # Strip any existing revision suffix
        base_ref = base_reference.split('.')[0]
        
        with engine.connect() as conn:
            result = conn.execute(text("""
                SELECT reference_number FROM submissions
                WHERE reference_number LIKE :pattern
                ORDER BY reference_number DESC
            """), {"pattern": f"{base_ref}%"})
            
            rows = result.fetchall()
            
            if not rows:
                # No existing references, return base.1
                return f"{base_ref}.1"
            
            # Find the highest revision number
            max_revision = 0
            for row in rows:
                ref = row[0]
                if '.' in ref:
                    try:
                        revision = int(ref.split('.')[-1])
                        max_revision = max(max_revision, revision)
                    except ValueError:
                        pass
            
            return f"{base_ref}.{max_revision + 1}"
    
    def get_quotes_by_reference_base(self, base_reference: str) -> pd.DataFrame:
        """Get all quotes with a given base reference (including revisions)."""
        engine = self._get_connection()
        base_ref = base_reference.split('.')[0]
        
        with engine.connect() as conn:
            df = pd.read_sql_query(
                "SELECT * FROM submissions WHERE reference_number LIKE %(pattern)s ORDER BY reference_number",
                conn,
                params={"pattern": f"{base_ref}%"}
            )
        return df
    
    def create_requote_from_submission(self, submission_id: int, new_demand_df: Optional[pd.DataFrame] = None) -> int:
        """
        Create a requote from an existing submission.
        Copies the submission with a new revision suffix on the reference number.
        If new_demand_df is provided, uses it; otherwise copies the original demand.
        Returns the new submission ID.
        """
        engine = self._get_connection()
        
        with engine.begin() as conn:
            # Get original submission
            result = conn.execute(
                text("SELECT * FROM submissions WHERE id = :id"),
                {"id": submission_id}
            )
            original = result.fetchone()
            
            if not original:
                raise ValueError(f"Submission {submission_id} not found")
            
            original_dict = dict(original._mapping)
            
            # Get next revision number
            new_reference = self.get_next_revision_number(original_dict["reference_number"])
            
            # Prepare data for new submission
            submission_date = datetime.now()
            
            # Use new demand if provided, otherwise use original
            if new_demand_df is not None and not new_demand_df.empty:
                demand_habitats_json = json.loads(new_demand_df.to_json(orient='records'))
                demand_habitats_json = sanitize_for_db(demand_habitats_json)
            else:
                demand_habitats_json = original_dict["demand_habitats"]
            
            # Insert new submission
            result = conn.execute(text("""
                INSERT INTO submissions (
                    submission_date, client_name, reference_number, site_location,
                    target_lpa, target_nca, target_lat, target_lon,
                    lpa_neighbors, nca_neighbors, demand_habitats,
                    contract_size, total_cost, admin_fee, total_with_admin,
                    num_banks_selected, banks_used,
                    manual_hedgerow_entries, manual_watercourse_entries,
                    allocation_results, username,
                    promoter_name, promoter_discount_type, promoter_discount_value,
                    customer_id
                ) VALUES (
                    :submission_date, :client_name, :reference_number, :site_location,
                    :target_lpa, :target_nca, :target_lat, :target_lon,
                    :lpa_neighbors, :nca_neighbors, :demand_habitats,
                    :contract_size, :total_cost, :admin_fee, :total_with_admin,
                    :num_banks_selected, :banks_used,
                    :manual_hedgerow_entries, :manual_watercourse_entries,
                    :allocation_results, :username,
                    :promoter_name, :promoter_discount_type, :promoter_discount_value,
                    :customer_id
                ) RETURNING id
            """), {
                "submission_date": submission_date,
                "client_name": original_dict["client_name"],
                "reference_number": new_reference,
                "site_location": original_dict["site_location"],
                "target_lpa": original_dict["target_lpa"],
                "target_nca": original_dict["target_nca"],
                "target_lat": original_dict["target_lat"],
                "target_lon": original_dict["target_lon"],
                "lpa_neighbors": json.dumps(original_dict["lpa_neighbors"]) if isinstance(original_dict["lpa_neighbors"], list) else original_dict["lpa_neighbors"],
                "nca_neighbors": json.dumps(original_dict["nca_neighbors"]) if isinstance(original_dict["nca_neighbors"], list) else original_dict["nca_neighbors"],
                "demand_habitats": json.dumps(demand_habitats_json) if isinstance(demand_habitats_json, list) else demand_habitats_json,
                "contract_size": original_dict["contract_size"],
                "total_cost": original_dict["total_cost"],
                "admin_fee": original_dict["admin_fee"],
                "total_with_admin": original_dict["total_with_admin"],
                "num_banks_selected": original_dict["num_banks_selected"],
                "banks_used": json.dumps(original_dict["banks_used"]) if isinstance(original_dict["banks_used"], list) else original_dict["banks_used"],
                "manual_hedgerow_entries": json.dumps(original_dict["manual_hedgerow_entries"]) if isinstance(original_dict["manual_hedgerow_entries"], list) else original_dict["manual_hedgerow_entries"],
                "manual_watercourse_entries": json.dumps(original_dict["manual_watercourse_entries"]) if isinstance(original_dict["manual_watercourse_entries"], list) else original_dict["manual_watercourse_entries"],
                "allocation_results": json.dumps(original_dict["allocation_results"]) if isinstance(original_dict["allocation_results"], list) else original_dict["allocation_results"],
                "username": original_dict["username"],
                "promoter_name": original_dict.get("promoter_name"),
                "promoter_discount_type": original_dict.get("promoter_discount_type"),
                "promoter_discount_value": original_dict.get("promoter_discount_value"),
                "customer_id": original_dict.get("customer_id")
            })
            
            new_submission_id = result.fetchone()[0]
            
            # Copy allocation details
            conn.execute(text("""
                INSERT INTO allocation_details (
                    submission_id, bank_key, bank_name,
                    demand_habitat, supply_habitat, allocation_type,
                    tier, units_supplied, unit_price, cost
                )
                SELECT :new_submission_id, bank_key, bank_name,
                       demand_habitat, supply_habitat, allocation_type,
                       tier, units_supplied, unit_price, cost
                FROM allocation_details
                WHERE submission_id = :original_submission_id
            """), {
                "new_submission_id": new_submission_id,
                "original_submission_id": submission_id
            })
            
            return new_submission_id
    
    def db_healthcheck(self) -> bool:
        """
        Perform a basic connectivity test to the database.
        
        Returns:
            True if the database is accessible, False otherwise
        """
        return DatabaseConnection.db_healthcheck()
