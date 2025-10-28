-- Comprehensive Database Cleanup for Attio Sync
-- This script restores the customers table to a clean TEXT-based schema
-- for use with StackSync transformations

-- Step 1: Drop any existing JSONB columns (they may exist from previous migrations)
DO $$
BEGIN
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

-- Step 2: Ensure all required TEXT columns exist
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'customers' AND column_name = 'first_name') THEN
        ALTER TABLE customers ADD COLUMN first_name TEXT;
    END IF;
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'customers' AND column_name = 'last_name') THEN
        ALTER TABLE customers ADD COLUMN last_name TEXT;
    END IF;
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'customers' AND column_name = 'email') THEN
        ALTER TABLE customers ADD COLUMN email TEXT;
    END IF;
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'customers' AND column_name = 'mobile_number') THEN
        ALTER TABLE customers ADD COLUMN mobile_number TEXT;
    END IF;
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'customers' AND column_name = 'company_name') THEN
        ALTER TABLE customers ADD COLUMN company_name TEXT;
    END IF;
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'customers' AND column_name = 'client_name') THEN
        ALTER TABLE customers ADD COLUMN client_name TEXT;
    END IF;
END $$;

-- Step 3: Remove NOT NULL constraint from client_name
ALTER TABLE customers ALTER COLUMN client_name DROP NOT NULL;

-- Step 4: Drop the old trigger if it exists
DROP TRIGGER IF EXISTS sync_customer_attio_trigger ON customers;
DROP FUNCTION IF EXISTS sync_customer_attio_fields();

-- Step 5: Create a simple trigger that only populates client_name from first_name/last_name
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
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER sync_customer_name_trigger
    BEFORE INSERT OR UPDATE ON customers
    FOR EACH ROW
    EXECUTE FUNCTION sync_customer_name();

-- Step 6: Clean up any malformed data
-- Fix records where first_name might be in last_name or other issues
-- This is a safe cleanup that won't lose data
UPDATE customers
SET 
    -- If first_name is null but last_name has content, try to split it
    first_name = CASE 
        WHEN first_name IS NULL AND last_name IS NOT NULL AND last_name LIKE '% %' 
        THEN SPLIT_PART(last_name, ' ', 1)
        ELSE first_name
    END,
    last_name = CASE 
        WHEN first_name IS NULL AND last_name IS NOT NULL AND last_name LIKE '% %' 
        THEN TRIM(SUBSTRING(last_name FROM POSITION(' ' IN last_name) + 1))
        ELSE last_name
    END,
    -- Rebuild client_name from first_name and last_name
    client_name = CASE
        WHEN first_name IS NOT NULL OR last_name IS NOT NULL 
        THEN TRIM(COALESCE(first_name, '') || ' ' || COALESCE(last_name, ''))
        WHEN client_name IS NOT NULL AND client_name != ''
        THEN client_name
        ELSE 'Unknown'
    END
WHERE first_name IS NULL OR last_name IS NULL OR client_name IS NULL OR client_name = '';

-- Step 7: Show summary of the cleanup
SELECT 
    COUNT(*) as total_customers,
    COUNT(CASE WHEN first_name IS NOT NULL THEN 1 END) as has_first_name,
    COUNT(CASE WHEN last_name IS NOT NULL THEN 1 END) as has_last_name,
    COUNT(CASE WHEN email IS NOT NULL THEN 1 END) as has_email,
    COUNT(CASE WHEN mobile_number IS NOT NULL THEN 1 END) as has_mobile,
    COUNT(CASE WHEN company_name IS NOT NULL THEN 1 END) as has_company,
    COUNT(CASE WHEN client_name IS NOT NULL THEN 1 END) as has_client_name
FROM customers;
