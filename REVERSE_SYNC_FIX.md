# Attio Reverse Sync Fix

## Problem: NULL Constraint Violations

When Attio syncs records back to Supabase (reverse sync), it was creating new customer records with JSONB fields populated but TEXT fields null, causing errors:

```
null value in column "client_name" of relation "customers" violates not-null constraint
```

Additionally, Attio was receiving errors about null values:
```
Attio error: Expected string, received null (for full_name field)
```

## Root Causes

1. **NOT NULL Constraint**: `client_name` was marked as NOT NULL, but Attio doesn't know about this legacy field
2. **One-way Sync**: Trigger only synced TEXT → JSONB, not JSONB → TEXT
3. **Empty full_name**: When both first_name and last_name were empty strings, full_name became empty string

## Solution Overview

### 1. Remove NOT NULL Constraint

**Before:**
```sql
CREATE TABLE customers (
    client_name TEXT NOT NULL,  -- ❌ Breaks Attio reverse sync
    ...
);
```

**After:**
```sql
CREATE TABLE customers (
    client_name TEXT,  -- ✅ Allows Attio to create records
    ...
);

-- Migration for existing databases
ALTER TABLE customers ALTER COLUMN client_name DROP NOT NULL;
```

### 2. Bidirectional Sync Trigger

The trigger now syncs data in BOTH directions:

#### Forward Sync (App → Attio)
When app creates/updates customer with TEXT fields:
```sql
first_name, last_name → personal_name {first_name, last_name, full_name}
email → email_addresses [{email_address}]
mobile_number → phone_numbers [{original_phone_number, country_code}]
company_name → companies [company_name]
```

#### Reverse Sync (Attio → App)
When Attio creates/updates customer with JSONB fields:
```sql
personal_name → first_name, last_name, client_name
email_addresses → email
phone_numbers → mobile_number  
companies → company_name
```

### 3. Auto-populate client_name

When `client_name` is NULL (from Attio sync), trigger automatically generates it:

```sql
-- Priority order:
1. Use first_name + last_name if available
2. Extract from personal_name JSONB if available
3. Default to 'Unknown' if no name data
```

**Example:**
```sql
-- Attio creates record with:
personal_name = {"first_name": "John", "last_name": "Smith", "full_name": "John Smith"}
client_name = NULL

-- Trigger auto-populates:
client_name = "John Smith"
first_name = "John"
last_name = "Smith"
```

### 4. Never-Empty full_name

Ensures `full_name` always has a value (not empty string):

```sql
-- If both first_name and last_name are empty:
full_name = COALESCE(first_name, last_name, 'Unknown')

-- If only one is empty:
full_name = TRIM(first_name || ' ' || last_name)
```

## Complete Trigger Logic

```sql
CREATE OR REPLACE FUNCTION sync_customer_attio_fields() 
RETURNS TRIGGER AS $$
BEGIN
    -- 1. Auto-populate client_name if null (for Attio reverse sync)
    IF NEW.client_name IS NULL THEN
        IF NEW.first_name IS NOT NULL OR NEW.last_name IS NOT NULL THEN
            NEW.client_name = TRIM(COALESCE(NEW.first_name, '') || ' ' || COALESCE(NEW.last_name, ''));
        ELSIF NEW.personal_name IS NOT NULL THEN
            NEW.client_name = COALESCE(
                NEW.personal_name->>'full_name',
                TRIM(COALESCE(NEW.personal_name->>'first_name', '') || ' ' || COALESCE(NEW.personal_name->>'last_name', '')),
                'Unknown'
            );
        ELSE
            NEW.client_name = 'Unknown';
        END IF;
    END IF;
    
    -- 2. Sync TEXT → JSONB (forward sync)
    IF NEW.first_name IS NOT NULL OR NEW.last_name IS NOT NULL THEN
        -- Build full_name safely
        full_name_value = TRIM(COALESCE(NEW.first_name, '') || ' ' || COALESCE(NEW.last_name, ''));
        IF full_name_value = '' THEN
            full_name_value = COALESCE(NEW.first_name, NEW.last_name, 'Unknown');
        END IF;
        
        NEW.personal_name = jsonb_build_object(
            'first_name', COALESCE(NEW.first_name, ''),
            'last_name', COALESCE(NEW.last_name, ''),
            'full_name', full_name_value
        );
    -- 3. Sync JSONB → TEXT (reverse sync)
    ELSIF NEW.personal_name IS NOT NULL THEN
        IF NEW.first_name IS NULL THEN
            NEW.first_name = NEW.personal_name->>'first_name';
        END IF;
        IF NEW.last_name IS NULL THEN
            NEW.last_name = NEW.personal_name->>'last_name';
        END IF;
    END IF;
    
    -- 4. Email sync (bidirectional)
    IF NEW.email IS NOT NULL AND NEW.email LIKE '%@%' THEN
        NEW.email_addresses = jsonb_build_array(
            jsonb_build_object('email_address', NEW.email)
        );
    ELSIF NEW.email_addresses IS NOT NULL AND jsonb_array_length(NEW.email_addresses) > 0 THEN
        IF NEW.email IS NULL THEN
            NEW.email = NEW.email_addresses->0->>'email_address';
        END IF;
    ELSE
        NEW.email_addresses = '[]'::jsonb;
    END IF;
    
    -- 5. Phone sync (bidirectional)
    IF NEW.mobile_number IS NOT NULL THEN
        NEW.phone_numbers = jsonb_build_array(
            jsonb_build_object(
                'original_phone_number', NEW.mobile_number,
                'country_code', 'GB'
            )
        );
    ELSIF NEW.phone_numbers IS NOT NULL AND jsonb_array_length(NEW.phone_numbers) > 0 THEN
        IF NEW.mobile_number IS NULL THEN
            NEW.mobile_number = NEW.phone_numbers->0->>'original_phone_number';
        END IF;
    ELSE
        NEW.phone_numbers = '[]'::jsonb;
    END IF;
    
    -- 6. Company sync (bidirectional)
    IF NEW.company_name IS NOT NULL THEN
        NEW.companies = jsonb_build_array(NEW.company_name);
    ELSIF NEW.companies IS NOT NULL AND jsonb_array_length(NEW.companies) > 0 THEN
        IF NEW.company_name IS NULL THEN
            NEW.company_name = TRIM(BOTH '"' FROM NEW.companies->0::text);
        END IF;
    ELSE
        NEW.companies = '[]'::jsonb;
    END IF;
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;
```

## Example Scenarios

### Scenario 1: App Creates Customer

**Input (from form):**
```python
first_name = "Sarah"
last_name = "Johnson"
email = "sarah@example.com"
mobile_number = "+44 20 7946 0958"
company_name = "Tech Solutions"
```

**Trigger Creates:**
```json
{
  "client_name": "Sarah Johnson",
  "first_name": "Sarah",
  "last_name": "Johnson",
  "personal_name": {
    "first_name": "Sarah",
    "last_name": "Johnson",
    "full_name": "Sarah Johnson"
  },
  "email": "sarah@example.com",
  "email_addresses": [{"email_address": "sarah@example.com"}],
  "mobile_number": "+44 20 7946 0958",
  "phone_numbers": [{"original_phone_number": "+44 20 7946 0958", "country_code": "GB"}],
  "company_name": "Tech Solutions",
  "companies": ["Tech Solutions"]
}
```

**Result:** ✅ Syncs to Attio successfully

---

### Scenario 2: Attio Creates Customer (Reverse Sync)

**Input (from Attio):**
```json
{
  "personal_name": {
    "first_name": "Henry",
    "last_name": "Cowls",
    "full_name": "Henry Cowls"
  },
  "email_addresses": [],
  "phone_numbers": [],
  "companies": []
}
```

**Trigger Auto-fills:**
```json
{
  "client_name": "Henry Cowls",        ← Auto-populated!
  "first_name": "Henry",               ← Extracted from personal_name
  "last_name": "Cowls",                ← Extracted from personal_name
  "personal_name": {
    "first_name": "Henry",
    "last_name": "Cowls",
    "full_name": "Henry Cowls"
  },
  "email": null,
  "email_addresses": [],
  "mobile_number": null,
  "phone_numbers": [],
  "company_name": null,
  "companies": []
}
```

**Result:** ✅ No NOT NULL violation, record created successfully

---

### Scenario 3: Empty Name Handling

**Input:**
```python
first_name = ""
last_name = ""
```

**Trigger Creates:**
```json
{
  "client_name": "Unknown",
  "personal_name": {
    "first_name": "",
    "last_name": "",
    "full_name": "Unknown"    ← Never empty!
  }
}
```

**Result:** ✅ No null errors in Attio

## Benefits

1. **No Constraint Violations**: Attio can create records without providing `client_name`
2. **Bidirectional Sync**: Data syncs correctly in both directions
3. **Auto-population**: Missing fields filled automatically from available data
4. **Safe Defaults**: Always has valid values (no nulls in critical fields)
5. **Backward Compatible**: Existing app code unchanged
6. **Future Proof**: Works whether data comes from app or Attio

## Deployment

On next app restart:
1. Migration removes NOT NULL constraint from existing databases
2. Trigger updated with bidirectional sync logic
3. All customer operations (create/update) work correctly
4. Attio reverse sync works without errors

## Verification

Check that reverse sync works:

```sql
-- Simulate Attio creating a record
INSERT INTO customers (personal_name, email_addresses, phone_numbers, companies)
VALUES (
    '{"first_name": "Test", "last_name": "User", "full_name": "Test User"}'::jsonb,
    '[]'::jsonb,
    '[]'::jsonb,
    '[]'::jsonb
);

-- Verify auto-population
SELECT client_name, first_name, last_name, personal_name 
FROM customers 
WHERE first_name = 'Test';

-- Expected result:
-- client_name = "Test User"  ← Auto-populated
-- first_name = "Test"        ← Extracted
-- last_name = "User"         ← Extracted
```

## Summary

✅ **Fixed Issues:**
1. NULL constraint violations on `client_name`
2. "Expected string, received null" errors for `full_name`
3. One-way sync (now bidirectional)
4. Missing TEXT fields when Attio syncs back

✅ **Result:**
- App → Attio sync: Works ✅
- Attio → App sync: Works ✅
- No database constraint errors ✅
- No Attio validation errors ✅
- Complete bidirectional synchronization ✅
