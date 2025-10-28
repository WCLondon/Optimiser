-- Fix Corrupted Customer Data from Reverse Sync
-- This script cleans up data that was corrupted when Attio synced back to Supabase
-- It extracts proper values from JSONB string representations in TEXT columns

-- Step 1: Clean up TEXT columns that have JSONB string representations
UPDATE customers
SET 
    -- Fix client_name if it contains JSONB representation
    client_name = CASE
        WHEN client_name LIKE '{%' THEN 
            -- Extract full_name from JSONB string
            COALESCE(
                (client_name::jsonb)->>'full_name',
                TRIM(COALESCE((client_name::jsonb)->>'first_name', '') || ' ' || COALESCE((client_name::jsonb)->>'last_name', '')),
                'Unknown'
            )
        WHEN client_name IS NULL OR client_name = '' THEN
            COALESCE(
                (personal_name->>'full_name'),
                TRIM(COALESCE(first_name, '') || ' ' || COALESCE(last_name, '')),
                'Unknown'
            )
        ELSE client_name
    END,
    
    -- Fix first_name if it contains JSONB representation
    first_name = CASE
        WHEN first_name LIKE '{%' THEN (first_name::jsonb)->>'first_name'
        WHEN first_name IS NULL AND personal_name IS NOT NULL THEN personal_name->>'first_name'
        ELSE first_name
    END,
    
    -- Fix last_name if it contains JSONB representation  
    last_name = CASE
        WHEN last_name LIKE '{%' OR last_name LIKE '[%' THEN 
            COALESCE(
                (CASE WHEN last_name LIKE '[%' THEN last_name::jsonb->0 ELSE last_name::jsonb END)->>'last_name',
                (CASE WHEN last_name LIKE '[%' THEN last_name::jsonb->0 ELSE last_name::jsonb END)->>'email_address'
            )
        WHEN last_name IS NULL AND personal_name IS NOT NULL THEN personal_name->>'last_name'
        ELSE last_name
    END,
    
    -- Fix email if it contains array representation
    email = CASE
        WHEN email LIKE '[%' THEN 
            -- Extract first email from array
            CASE 
                WHEN email::jsonb->0->>'email_address' IS NOT NULL 
                THEN email::jsonb->0->>'email_address'
                ELSE NULL
            END
        WHEN email LIKE '{%' THEN (email::jsonb)->>'email_address'
        WHEN email IS NULL AND email_addresses IS NOT NULL AND jsonb_array_length(email_addresses) > 0 THEN
            email_addresses->0->>'email_address'
        ELSE email
    END,
    
    -- Fix mobile_number if it contains array/object representation
    mobile_number = CASE
        WHEN mobile_number LIKE '[%' THEN 
            CASE 
                WHEN mobile_number::jsonb->0->>'original_phone_number' IS NOT NULL 
                THEN mobile_number::jsonb->0->>'original_phone_number'
                WHEN mobile_number::jsonb->0->>'phone_number' IS NOT NULL
                THEN mobile_number::jsonb->0->>'phone_number'
                ELSE NULL
            END
        WHEN mobile_number LIKE '{%' THEN 
            COALESCE(
                (mobile_number::jsonb)->>'original_phone_number',
                (mobile_number::jsonb)->>'phone_number'
            )
        WHEN mobile_number IS NULL AND phone_numbers IS NOT NULL AND jsonb_array_length(phone_numbers) > 0 THEN
            phone_numbers->0->>'original_phone_number'
        ELSE mobile_number
    END,
    
    -- Fix company_name if it contains array representation
    company_name = CASE
        WHEN company_name LIKE '[%' THEN 
            -- Extract first company from array
            CASE 
                WHEN company_name::jsonb->0 IS NOT NULL 
                THEN company_name::jsonb->>0
                ELSE NULL
            END
        WHEN company_name IS NULL AND companies IS NOT NULL AND jsonb_array_length(companies) > 0 THEN
            companies->>0
        ELSE company_name
    END

WHERE 
    -- Only update rows that have corrupted data
    client_name LIKE '{%' OR client_name LIKE '[%' OR
    first_name LIKE '{%' OR first_name LIKE '[%' OR
    last_name LIKE '{%' OR last_name LIKE '[%' OR
    email LIKE '[%' OR email LIKE '{%' OR
    mobile_number LIKE '[%' OR mobile_number LIKE '{%' OR
    company_name LIKE '[%' OR
    -- Or rows where TEXT is null but JSONB has data
    (client_name IS NULL AND personal_name IS NOT NULL) OR
    (email IS NULL AND email_addresses IS NOT NULL AND jsonb_array_length(email_addresses) > 0) OR
    (mobile_number IS NULL AND phone_numbers IS NOT NULL AND jsonb_array_length(phone_numbers) > 0) OR
    (company_name IS NULL AND companies IS NOT NULL AND jsonb_array_length(companies) > 0);

-- Step 2: Now rebuild JSONB columns from the cleaned TEXT columns
-- This ensures consistency
UPDATE customers
SET 
    personal_name = jsonb_build_object(
        'first_name', COALESCE(first_name, ''),
        'last_name', COALESCE(last_name, ''),
        'full_name', COALESCE(NULLIF(TRIM(COALESCE(first_name, '') || ' ' || COALESCE(last_name, '')), ''), client_name, 'Unknown')
    ),
    
    email_addresses = CASE
        WHEN email IS NOT NULL AND email != '' AND email ~ '^[^@]+@[^@]+\.[^@]+$' THEN
            jsonb_build_array(jsonb_build_object('email_address', email))
        ELSE '[]'::jsonb
    END,
    
    phone_numbers = CASE
        WHEN mobile_number IS NOT NULL AND mobile_number != '' THEN
            jsonb_build_array(jsonb_build_object(
                'original_phone_number', mobile_number,
                'country_code', 'GB'
            ))
        ELSE '[]'::jsonb
    END,
    
    companies = CASE
        WHEN company_name IS NOT NULL AND company_name != '' THEN
            jsonb_build_array(company_name)
        ELSE '[]'::jsonb
    END;

-- Step 3: Verify the cleanup
-- Show sample of cleaned records
SELECT 
    id,
    client_name,
    first_name,
    last_name,
    email,
    mobile_number,
    company_name,
    personal_name,
    email_addresses,
    phone_numbers,
    companies
FROM customers
ORDER BY id DESC
LIMIT 10;
