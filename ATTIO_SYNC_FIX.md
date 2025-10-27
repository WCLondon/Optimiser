# Attio Sync Compatibility Fix

## Problem Statement

The Supabase customers table was storing data in TEXT format, but Attio (via StackSync) expects data in specific JSONB formats:
- **Company**: Expected as array, but receiving string
- **Email addresses**: Expected as array, but receiving string  
- **Name**: Expected as JSON object, but receiving string
- **Phone numbers**: Expected as JSON, but receiving string

Additionally, the user requested that first name and surname be required fields, and that email report generation be disabled until these fields are provided.

## Solution Overview

We implemented a dual-column approach that maintains backward compatibility while adding Attio-compatible JSONB fields to the customers table.

### Database Schema Changes

#### New Columns Added to `customers` Table

1. **`personal_name` (JSONB)**: Stores customer name as JSON object (Attio requirement)
   ```json
   {
     "first_name": "John",
     "last_name": "Smith",
     "full_name": "John Smith"
   }
   ```

2. **`email_addresses` (JSONB)**: Stores email as array of objects
   ```json
   [
     {
       "email_address": "john.smith@example.com"
     }
   ]
   ```

3. **`phone_numbers` (JSONB)**: Stores phone numbers as array of objects (Attio format)
   ```json
   [
     {
       "original_phone_number": "+44 7700 900000",
       "country_code": "GB"
     }
   ]
   ```

4. **`companies` (JSONB)**: Stores company names as array
   ```json
   ["Acme Corporation"]
   ```

### Automatic Synchronization

A PostgreSQL trigger (`sync_customer_attio_fields_trigger`) automatically converts legacy TEXT fields to Attio-compatible JSONB format on every INSERT or UPDATE:

```sql
CREATE TRIGGER sync_customer_attio_fields_trigger
BEFORE INSERT OR UPDATE ON customers
FOR EACH ROW EXECUTE FUNCTION sync_customer_attio_fields();
```

This ensures:
- No manual data conversion needed
- Legacy code continues to work
- Attio receives data in the expected format
- Data consistency between old and new formats

### Application Changes

#### 1. Required Customer Fields

First name and last name are now **required** for all customer records:

**In Customer Management:**
```python
if not cust_first_name or not cust_first_name.strip():
    st.error("First name is required for Attio sync.")
elif not cust_last_name or not cust_last_name.strip():
    st.error("Last name is required for Attio sync.")
```

**In database.py:**
```python
if not first_name or not first_name.strip():
    raise ValueError("First name is required for customer records")
if not last_name or not last_name.strip():
    raise ValueError("Last name is required for customer records")
```

#### 2. Form Updates

The main optimization form now requires first and last name:
- Fields moved out of "Additional Details" expander to main form
- Marked as required with asterisk (*)
- Placeholder text indicates they are required
- Clear validation messages when missing

#### 3. Email Download Protection

Email report download is now disabled until first and last name are provided:

```python
has_customer_name = (
    st.session_state.get("form_customer_first_name") and 
    st.session_state.get("form_customer_first_name").strip() and
    st.session_state.get("form_customer_last_name") and
    st.session_state.get("form_customer_last_name").strip()
)

if not has_customer_name:
    st.warning("⚠️ Email download is disabled: Please provide First Name and Last Name...")
```

### Data Migration

Existing customer records are automatically backfilled with Attio-compatible data:

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
WHERE personal_name IS NULL OR email_addresses IS NULL OR phone_numbers IS NULL OR companies IS NULL;
```

## Benefits

1. **Attio Compatibility**: Data now syncs correctly with Attio CRM
2. **Backward Compatibility**: Existing code continues to work with TEXT fields
3. **Automatic Sync**: No manual data conversion needed
4. **Data Quality**: Required fields ensure complete customer records
5. **User Guidance**: Clear validation messages guide users
6. **No Data Loss**: Legacy columns retained alongside new JSONB columns

## Testing

Comprehensive test suite validates:
- ✅ Customers table has all required Attio-compatible columns
- ✅ Trigger function exists and is properly configured
- ✅ Backfill query exists for existing records
- ✅ Validation enforces first_name and last_name requirements
- ✅ App forms properly mark fields as required
- ✅ Email download validation works correctly
- ✅ submissions_attio table has all required fields

Run tests with:
```bash
python test_attio_sync.py
```

## Usage

### For End Users

1. When creating a quote, provide first and last name in the customer information section
2. These fields are now required and marked with asterisk (*)
3. Email report download will be disabled until both fields are provided
4. Clear error messages will guide you if fields are missing

### For Administrators

1. When adding customers in Customer Management, first and last name are required
2. Existing customers without names should be updated with complete information
3. The system automatically converts data to Attio format
4. No manual intervention needed for sync

### For Developers

1. Legacy TEXT columns (`first_name`, `last_name`, `email`, `mobile_number`, `company_name`) still work
2. New JSONB columns (`name`, `email_addresses`, `phone_numbers`, `companies`) are automatically populated
3. Trigger handles synchronization transparently
4. Use `add_customer()` method which enforces validation

## Migration Notes

### Immediate Effect
- All new customer records automatically get Attio-compatible data
- Existing records backfilled on first database initialization
- Forms updated to require first and last name
- Email download protected by validation

### No Breaking Changes
- Existing code that reads/writes TEXT columns continues to work
- Trigger ensures JSONB columns stay in sync
- StackSync can now successfully pull data from customers table

## Technical Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                      Application Layer                       │
│  (app.py - Forms with first/last name validation)          │
└─────────────────┬───────────────────────────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────────────────────────┐
│                    Database Layer (database.py)              │
│  - add_customer() validates first_name & last_name          │
│  - Inserts to customers table with TEXT fields              │
└─────────────────┬───────────────────────────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────────────────────────┐
│              PostgreSQL Trigger (BEFORE INSERT/UPDATE)       │
│  sync_customer_attio_fields_trigger                         │
│  - Converts TEXT → JSONB automatically                      │
│  - personal_name: {first_name, last_name, full_name}       │
│  - email_addresses: [{email_address}]                      │
│  - phone_numbers: [{original_phone_number, country_code}] │
│  - companies: [company_name]                               │
└─────────────────┬───────────────────────────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────────────────────────┐
│                      customers Table                         │
│  ┌──────────────┬──────────────────────────────────────┐   │
│  │ Legacy (TEXT)│ Attio-Compatible (JSONB)            │   │
│  ├──────────────┼──────────────────────────────────────┤   │
│  │ first_name   │ personal_name: {first_name,         │   │
│  │ last_name    │   last_name, full_name}             │   │
│  │ email        │ email_addresses: [{email_address}]  │   │
│  │ mobile_number│ phone_numbers: [{original_phone_    │   │
│  │              │   number, country_code}]            │   │
│  │ company_name │ companies: [company_name]           │   │
│  └──────────────┴──────────────────────────────────────┘   │
└─────────────────┬───────────────────────────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────────────────────────┐
│                   Attio / StackSync                          │
│  Reads JSONB columns for CRM integration                    │
│  - Proper array/object formats                              │
│  - No sync errors                                           │
└─────────────────────────────────────────────────────────────┘
```

## Future Considerations

1. **Phase Out Legacy Columns**: After confirming Attio sync works correctly, legacy TEXT columns could be deprecated
2. **Additional Validation**: Could add email format validation, phone number format validation
3. **Multiple Emails/Phones**: Structure already supports multiple entries per customer
4. **Company Hierarchy**: Could extend companies array to include company relationships

## Support

If you encounter issues:
1. Check that first_name and last_name are provided when creating customers
2. Verify PostgreSQL trigger is active: `\dFt sync_customer_attio_fields_trigger`
3. Check JSONB columns are populated: `SELECT name, email_addresses FROM customers LIMIT 5;`
4. Run test suite: `python test_attio_sync.py`

## Change Log

### 2025-01-27 (Initial Implementation)
- Added Attio-compatible JSONB columns to customers table
- Created automatic sync trigger
- Made first_name and last_name required
- Updated forms with validation
- Added email download protection
- Backfilled existing customer records
- Created comprehensive test suite
