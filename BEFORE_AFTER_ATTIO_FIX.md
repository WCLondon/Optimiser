# Before vs After: Attio Data Structure Fix

## Visual Comparison

### ❌ BEFORE (Causing Errors)

```json
{
  "name": {                          ← WRONG: Should be "personal_name"
    "first_name": "John",
    "last_name": "Smith"             ← MISSING: Should include "full_name"
  },
  "email_addresses": [
    {
      "email_address": "john@example.com",
      "type": "work"                 ← WRONG: Attio doesn't expect "type"
    }
  ],
  "phone_numbers": [
    {
      "phone_number": "+44 7700",    ← WRONG: Should be "original_phone_number"
      "type": "mobile"               ← WRONG: Should be "country_code"
    }
  ],
  "companies": ["Acme Corp"]         ← CORRECT ✓
}
```

**Attio Errors:**
- ❌ `personal_name must be a dict with at least one of: first_name, last_name, full_name`
- ❌ `phone_numbers must be an array of dicts with: original_phone_number, country_code`
- ❌ `Invalid value passed to email_addresses`

---

### ✅ AFTER (Correct Format)

```json
{
  "personal_name": {                 ← CORRECT: Field name matches Attio
    "first_name": "John",
    "last_name": "Smith",
    "full_name": "John Smith"        ← CORRECT: Includes full_name
  },
  "email_addresses": [
    {
      "email_address": "john@example.com"  ← CORRECT: No "type" field
    }
  ],
  "phone_numbers": [
    {
      "original_phone_number": "+44 7700", ← CORRECT: Field name matches Attio
      "country_code": "GB"                 ← CORRECT: Uses country_code
    }
  ],
  "companies": ["Acme Corp"]         ← CORRECT ✓
}
```

**Attio Result:**
- ✅ No errors
- ✅ Sync successful
- ✅ Customer records appear in Attio CRM

---

## Key Changes Summary

| Field | Before | After | Attio Requirement |
|-------|--------|-------|-------------------|
| **Name** | `name: {first_name, last_name}` | `personal_name: {first_name, last_name, full_name}` | Must be called `personal_name` and include `full_name` |
| **Email** | `[{email_address, type}]` | `[{email_address}]` | No `type` field needed |
| **Phone** | `[{phone_number, type}]` | `[{original_phone_number, country_code}]` | Must use `original_phone_number` and `country_code` |
| **Companies** | `[company_name]` | `[company_name]` | Already correct ✓ |

---

## Database Trigger Changes

### Before (Incorrect)
```sql
-- Wrong field name
NEW.name = jsonb_build_object(
    'first_name', COALESCE(NEW.first_name, ''),
    'last_name', COALESCE(NEW.last_name, '')
    -- Missing full_name
);

-- Wrong structure
NEW.phone_numbers = jsonb_build_array(
    jsonb_build_object(
        'phone_number', NEW.mobile_number,  -- Wrong field name
        'type', 'mobile'                    -- Wrong field
    )
);

-- Unnecessary field
NEW.email_addresses = jsonb_build_array(
    jsonb_build_object(
        'email_address', NEW.email,
        'type', 'work'                      -- Remove this
    )
);
```

### After (Correct)
```sql
-- Correct field name and includes full_name
NEW.personal_name = jsonb_build_object(
    'first_name', COALESCE(NEW.first_name, ''),
    'last_name', COALESCE(NEW.last_name, ''),
    'full_name', TRIM(COALESCE(NEW.first_name, '') || ' ' || COALESCE(NEW.last_name, ''))
);

-- Correct Attio structure
NEW.phone_numbers = jsonb_build_array(
    jsonb_build_object(
        'original_phone_number', NEW.mobile_number,
        'country_code', 'GB'
    )
);

-- Clean structure, validates email
IF NEW.email LIKE '%@%' THEN
    NEW.email_addresses = jsonb_build_array(
        jsonb_build_object(
            'email_address', NEW.email
        )
    );
END IF;
```

---

## Real Example

### Sample Customer Data

**Input (Legacy TEXT fields):**
```
first_name:    "Sarah"
last_name:     "Johnson"
email:         "sarah.johnson@example.com"
mobile_number: "+44 20 7946 0958"
company_name:  "Tech Solutions Ltd"
```

### Output (Attio-Compatible JSONB)

**Before (Causing Errors):**
```json
{
  "name": {
    "first_name": "Sarah",
    "last_name": "Johnson"
  },
  "email_addresses": [{"email_address": "sarah.johnson@example.com", "type": "work"}],
  "phone_numbers": [{"phone_number": "+44 20 7946 0958", "type": "mobile"}],
  "companies": ["Tech Solutions Ltd"]
}
```
❌ **Result**: Attio sync fails with multiple validation errors

**After (Correct):**
```json
{
  "personal_name": {
    "first_name": "Sarah",
    "last_name": "Johnson",
    "full_name": "Sarah Johnson"
  },
  "email_addresses": [{"email_address": "sarah.johnson@example.com"}],
  "phone_numbers": [{"original_phone_number": "+44 20 7946 0958", "country_code": "GB"}],
  "companies": ["Tech Solutions Ltd"]
}
```
✅ **Result**: Attio sync succeeds, customer appears in CRM

---

## Verification Query

To verify the fix in your database:

```sql
SELECT 
    first_name,
    last_name,
    email,
    mobile_number,
    personal_name,
    email_addresses,
    phone_numbers,
    companies
FROM customers
LIMIT 1;
```

**Expected Result:**
```
first_name  | last_name | email              | mobile_number    | personal_name                                           | email_addresses                        | phone_numbers                                            | companies
------------|-----------|--------------------|-----------------|---------------------------------------------------------|----------------------------------------|----------------------------------------------------------|------------------
Sarah       | Johnson   | sarah@example.com  | +44 20 7946... | {"first_name":"Sarah","last_name":"Johnson",...}        | [{"email_address":"sarah@example.com"}]| [{"original_phone_number":"+44...","country_code":"GB"}] | ["Tech Solutions Ltd"]
```

---

## What Happens on Deployment

1. **Automatic Migration**: Trigger function is replaced with correct version
2. **Backfill**: Existing customer records are updated to correct format
3. **New Records**: All new customers automatically get correct structure
4. **Attio Sync**: Should work without errors immediately

No manual intervention required! ✅
