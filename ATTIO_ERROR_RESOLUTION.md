# Attio Sync Error Resolution

## Original Errors Reported

The following Attio sync errors were occurring:

1. **personal_name must be a dict with at least one of the following keys: first_name (str), last_name (str), full_name (str)**
2. **phone_numbers must be an array of dicts with the following keys: original_phone_number (str), country_code (str)**
3. **Attio error: An invalid value was passed to attribute with slug "email_addresses". Validation Errors: - Field 'email_address': Invalid email address**

## Root Cause Analysis

The initial implementation used incorrect field names and structures:

### Issue 1: Wrong Field Name
- **Used**: `name` 
- **Attio Expects**: `personal_name`
- **Impact**: Attio couldn't recognize the name field

### Issue 2: Missing full_name
- **Used**: `{first_name, last_name}`
- **Attio Expects**: At least one of `{first_name, last_name, full_name}`
- **Impact**: Although we had first and last names, Attio also expects full_name

### Issue 3: Wrong Phone Structure
- **Used**: `{phone_number, type}`
- **Attio Expects**: `{original_phone_number, country_code}`
- **Impact**: Attio couldn't parse phone numbers due to wrong field names

### Issue 4: Wrong Email Structure  
- **Used**: `{email_address, type}` with potential invalid emails
- **Attio Expects**: `{email_address}` with valid email format (containing @)
- **Impact**: Extra 'type' field and invalid emails caused validation errors

## Resolution

### 1. Changed Column Name
```sql
-- OLD:
ALTER TABLE customers ADD COLUMN name JSONB;

-- NEW:
ALTER TABLE customers ADD COLUMN personal_name JSONB;
```

### 2. Updated Trigger for personal_name
```sql
-- OLD:
NEW.name = jsonb_build_object(
    'first_name', COALESCE(NEW.first_name, ''),
    'last_name', COALESCE(NEW.last_name, '')
);

-- NEW:
NEW.personal_name = jsonb_build_object(
    'first_name', COALESCE(NEW.first_name, ''),
    'last_name', COALESCE(NEW.last_name, ''),
    'full_name', TRIM(COALESCE(NEW.first_name, '') || ' ' || COALESCE(NEW.last_name, ''))
);
```

**Result**: Now includes all three name fields that Attio expects.

### 3. Fixed Phone Numbers Structure
```sql
-- OLD:
NEW.phone_numbers = jsonb_build_array(
    jsonb_build_object(
        'phone_number', NEW.mobile_number,
        'type', 'mobile'
    )
);

-- NEW:
NEW.phone_numbers = jsonb_build_array(
    jsonb_build_object(
        'original_phone_number', NEW.mobile_number,
        'country_code', 'GB'
    )
);
```

**Changes**:
- Renamed `phone_number` → `original_phone_number` (Attio requirement)
- Removed `type` field
- Changed to `country_code` with default 'GB' (UK)

### 4. Fixed Email Addresses Structure and Validation
```sql
-- OLD:
IF NEW.email IS NOT NULL AND NEW.email != '' THEN
    NEW.email_addresses = jsonb_build_array(
        jsonb_build_object(
            'email_address', NEW.email,
            'type', 'work'
        )
    );

-- NEW:
IF NEW.email IS NOT NULL AND NEW.email != '' AND NEW.email LIKE '%@%' THEN
    NEW.email_addresses = jsonb_build_array(
        jsonb_build_object(
            'email_address', NEW.email
        )
    );
```

**Changes**:
- Removed `type` field (not needed)
- Added email validation: `email LIKE '%@%'` to ensure valid format
- Only creates email_addresses array if email contains @

## Updated Data Structures

### Personal Name (Correct Format)
```json
{
  "first_name": "John",
  "last_name": "Smith",
  "full_name": "John Smith"
}
```

### Email Addresses (Correct Format)
```json
[
  {
    "email_address": "john.smith@example.com"
  }
]
```

### Phone Numbers (Correct Format)
```json
[
  {
    "original_phone_number": "+44 7700 900000",
    "country_code": "GB"
  }
]
```

### Companies (Already Correct)
```json
["Acme Corporation"]
```

## Backfill Query Updated

The backfill query for existing customer records was also updated:

```sql
UPDATE customers SET
    personal_name = jsonb_build_object(
        'first_name', COALESCE(first_name, ''),
        'last_name', COALESCE(last_name, ''),
        'full_name', TRIM(COALESCE(first_name, '') || ' ' || COALESCE(last_name, ''))
    ),
    email_addresses = CASE 
        WHEN email IS NOT NULL AND email != '' AND email LIKE '%@%' THEN
            jsonb_build_array(
                jsonb_build_object('email_address', email)
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
WHERE personal_name IS NULL OR email_addresses IS NULL 
   OR phone_numbers IS NULL OR companies IS NULL;
```

## Expected Outcome

After these changes:

1. ✅ **personal_name** field will be recognized by Attio with all required keys
2. ✅ **phone_numbers** will have the correct structure with `original_phone_number` and `country_code`
3. ✅ **email_addresses** will only contain valid emails (with @) and proper structure
4. ✅ **companies** already working correctly
5. ✅ No more "The following fields contain errors: Name" messages
6. ✅ No more phone_numbers validation errors
7. ✅ No more email_addresses validation errors

## Testing

All tests pass with the updated structure:

```bash
$ python test_attio_sync.py

✓ PASS: Customers Table Schema
✓ PASS: Validation Requirements
✓ PASS: App Form Validation
✓ PASS: Submissions Attio Compatibility

The customers table is now compatible with Attio/StackSync:
- personal_name stored as JSONB object: {first_name, last_name, full_name}
- email_addresses stored as JSONB array: [{email_address}]
- phone_numbers stored as JSONB array: [{original_phone_number, country_code}]
- companies stored as JSONB array: [company_name]
```

## Deployment

These changes will take effect on the next application restart:

1. Database trigger will be updated automatically
2. New customer records will use correct structure
3. Existing records will be backfilled with correct format
4. Attio sync should work without errors

## Verification Steps

After deployment, verify:

1. Create a new customer with first name, last name, email, and phone
2. Check the customers table: `SELECT personal_name, email_addresses, phone_numbers FROM customers LIMIT 1;`
3. Verify Attio sync logs show no errors
4. Confirm customer records appear correctly in Attio CRM

## Notes

- **Country Code**: Defaulted to 'GB' (United Kingdom). If customers are from other countries, this may need to be made dynamic.
- **Email Validation**: Simple check for '@' character. More sophisticated validation could be added if needed.
- **Full Name**: Automatically constructed from first_name + last_name. If explicit full name is provided in future, trigger can be updated.
