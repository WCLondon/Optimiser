# Promoter Authentication System Migration

## Overview

The authentication system has been updated to use two new tables: `promoter_companies` and `promoter_individuals`, replacing the old `introducers` table. This change provides better separation between company-level settings and individual user accounts.

## New Table Structure

### promoter_companies
Stores company/organization-level information and discount settings.

**Columns:**
- `id` (TEXT, PRIMARY KEY): Unique identifier (UUID)
- `name` (TEXT, UNIQUE): Company name
- `email` (TEXT): Company contact email
- `phone` (TEXT): Company phone number
- `discount_type` (TEXT): Type of discount ('tier_up', 'percentage', 'no_discount')
- `discount_value` (FLOAT): Discount value
- `active` (BOOLEAN): Whether company is active
- `type` (TEXT): Fixed value 'Company'
- `requires_approval` (BOOLEAN): Whether quotes require approval
- `approval_threshold` (FLOAT): Dollar threshold for approval requirement
- `notes` (TEXT): Additional notes
- `created_by`, `updated_by` (TEXT): Audit fields
- `created_date`, `updated_date` (TIMESTAMP): Timestamps

### promoter_individuals
Stores individual user accounts, linked to companies.

**Columns:**
- `id` (TEXT, PRIMARY KEY): Unique identifier (UUID)
- `name` (TEXT): Individual's full name
- `username` (TEXT, UNIQUE): Login username (typically email)
- `password_hash` (TEXT): SHA256 password hash
- `email` (TEXT): Individual's email
- `phone` (TEXT): Individual's phone
- `company_id` (TEXT, FK): Reference to parent company
- `discount_type` (TEXT): Individual discount type (usually NULL, inherits from company)
- `discount_value` (FLOAT): Individual discount value
- `active` (BOOLEAN): Whether user is active
- `type` (TEXT): Fixed value 'User'
- `role` (TEXT): User role ('Team Leader', 'Standard User', 'Leadership')
- `team_leader_id` (TEXT, FK): Reference to team leader
- `job_title` (TEXT): Job title
- `notes` (TEXT): Additional notes
- `created_by`, `updated_by` (TEXT): Audit fields
- `created_date`, `updated_date` (TIMESTAMP): Timestamps

## Authentication Flow

### Login Process
1. User enters username (email) and password
2. System looks up user in `promoter_individuals` table
3. Password is hashed with SHA256 and compared to stored hash
4. If match, system fetches associated company from `promoter_companies`
5. Discount settings are inherited from company (override individual settings)
6. User session is established with combined company + individual data

### Password Hashing
**New System (promoter_individuals):**
- Uses SHA256 hashing directly (no salt)
- Example: `hashlib.sha256(password.encode('utf-8')).hexdigest()`

**Old System (introducers):**
- Uses SHA256 with a separate salt column
- Backward compatible but not recommended for new users

## Code Changes

### database.py
**New Methods:**
- `authenticate_promoter(username, password)` - Main authentication for new system
- `get_all_promoter_companies()` - List all companies
- `get_all_promoter_individuals()` - List all individuals
- `get_promoter_individual_by_id(id)` - Get specific individual
- `get_promoter_company_by_id(id)` - Get specific company
- `update_promoter_individual_password(id, password)` - Update password

**Modified Methods:**
- `authenticate_introducer(username, password)` - Now checks new tables first, then falls back to old `introducers` table

### promoter_app.py
**Updated Functions:**
- `authenticate_promoter()` - Handles both old and new authentication systems
- Password change form - Detects system type and uses appropriate update method

## Discount Inheritance

Individual users inherit discount settings from their parent company:

```python
# Company level (promoter_companies)
discount_type = 'tier_up'
discount_value = 0

# Individual level (promoter_individuals)
# Individual's discount_type and discount_value are typically NULL
# System uses company's settings instead

# In authentication response:
promoter_info = {
    'name': 'John Smith',
    'company_name': 'Arbtech',
    'effective_discount_type': 'tier_up',  # From company
    'effective_discount_value': 0,          # From company
    ...
}
```

## Backward Compatibility

The system maintains backward compatibility with the old `introducers` table:

1. `authenticate_introducer()` checks new tables first
2. If not found, falls back to old `introducers` table
3. Existing apps continue to work without modification
4. New features (approval thresholds, roles) only available in new system

## Migration Notes

### For New Deployments
- Use the SQL sample data provided in the issue
- Tables will be auto-created by `database.py` on first run
- No migration needed

### For Existing Deployments
- New tables created automatically on app startup
- Old `introducers` table remains functional
- Optional: Use `migrate_introducers_to_promoters.py` to migrate data
- **Important:** Migrated users must reset passwords (different hash format)

## Testing

Run the test script to verify authentication:

```bash
python test_promoter_auth.py
```

This will:
1. Verify tables exist
2. List promoter companies and individuals
3. Test authentication methods
4. Confirm discount inheritance works

## Security Considerations

1. **Password Hashing:** New system uses SHA256 without salt
   - Simple but adequate for this use case
   - All passwords transmitted over HTTPS
   - Consider adding salt in future for enhanced security

2. **Active Status:** Inactive users/companies cannot log in
   - Check `active = TRUE` in all queries

3. **Approval Thresholds:** Companies can require approval for large quotes
   - Stored in `requires_approval` and `approval_threshold` fields
   - Application logic must check these values

## Example Usage

### Authentication
```python
from database import SubmissionsDB

db = SubmissionsDB()
success, promoter_info = db.authenticate_introducer(
    username="user@example.com",
    password="user_password"
)

if success:
    company_name = promoter_info['company_name']
    discount_type = promoter_info['effective_discount_type']
    # ... use promoter_info
```

### Updating Password
```python
# Detect system type
if 'company_id' in promoter_info:
    # New system
    db.update_promoter_individual_password(
        promoter_info['id'], 
        new_password
    )
else:
    # Old system
    db.update_introducer_password(
        promoter_info['id'], 
        new_password
    )
```

## Support

For questions or issues:
1. Check the test script output
2. Review database logs for connection issues
3. Verify Supabase connection settings in secrets.toml
4. Contact the development team
