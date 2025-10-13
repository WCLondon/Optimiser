# Promoter/Introducer Discount Feature - Implementation Summary

## Overview
This implementation adds complete promoter/introducer discount functionality to the BNG Optimiser application, including database storage, UI controls, pricing logic, and reporting.

## Changes Made

### 1. Database Changes (database.py)

#### New Tables
- **introducers table**: Stores approved introducers/promoters
  - `id`: Primary key
  - `name`: Unique introducer name
  - `discount_type`: Either 'tier_up' or 'percentage'
  - `discount_value`: Decimal value (percentage for percentage type, ignored for tier_up)
  - `created_date`: Timestamp when created
  - `updated_date`: Timestamp when last updated

#### Updated Tables
- **submissions table**: Extended with promoter tracking fields
  - `promoter_name`: Name of the introducer (if used)
  - `promoter_discount_type`: Type of discount applied
  - `promoter_discount_value`: Discount value applied

#### New CRUD Operations
- `add_introducer()`: Create a new introducer
- `get_all_introducers()`: Retrieve all introducers
- `get_introducer_by_name()`: Find introducer by name
- `update_introducer()`: Modify introducer details
- `delete_introducer()`: Remove an introducer
- `store_submission()`: Updated to accept promoter parameters

### 2. Main Application Changes (app.py)

#### Session State Initialization
Added promoter-related session state variables:
- `use_promoter`: Boolean flag for promoter checkbox
- `selected_promoter`: Name of selected promoter
- `promoter_discount_type`: Type of discount ('tier_up' or 'percentage')
- `promoter_discount_value`: Discount value

#### Admin Dashboard Enhancements
Added introducer management section with:
- Form to add new introducers
- List view of all introducers
- Edit functionality (inline forms)
- Delete functionality
- Display of discount type and value

#### Main Workflow UI
Added promoter selection section after "Locate target site":
- Checkbox to enable promoter discount
- Dropdown populated from database
- Info display showing discount type and value
- Automatic loading of introducer list from database

#### Discount Helper Functions
Three new helper functions:
1. `apply_tier_up_discount(tier)`: Moves tier up one level (local→adjacent→far)
2. `apply_percentage_discount(price, percentage)`: Applies percentage discount
3. `get_active_promoter_discount()`: Retrieves active discount from session state

#### Pricing Logic Integration
Modified pricing in all three option builders:
- `prepare_options()`: Area habitat pricing
- `prepare_hedgerow_options()`: Hedgerow pricing
- `prepare_watercourse_options()`: Watercourse pricing

For each option builder:
- Retrieves active promoter discount settings
- For tier_up: Calculates pricing using higher tier
- For percentage: Applies discount to unit_price
- Keeps original tier for reporting purposes

#### Report Generation
Updated `generate_client_report_table_fixed()`:
- Added promoter parameters to function signature
- Displays promoter name in email body
- Shows discount type and explanation in quote section

Updated `store_submission()` call:
- Passes promoter_name, promoter_discount_type, promoter_discount_value

#### Admin Dashboard Display
- Shows promoter name in submission list view
- Displays promoter details in submission detail view

## Discount Types Explained

### Tier Up Discount
- Pricing is calculated as if the bank is one tier closer
- local → pricing uses adjacent tier
- adjacent → pricing uses far tier
- far → stays at far tier (no change)
- The actual tier remains unchanged for reporting
- This effectively reduces the cost by using a lower price point

### Percentage Discount
- A percentage discount is applied to all line items
- The £500 admin fee is NOT discounted (as specified in requirements)
- Supports decimal percentages (e.g., 10.5%)
- Formula: discounted_price = original_price × (1 - percentage/100)

## Testing Performed

### 1. Database Operations Test
- ✅ Add introducer
- ✅ Get all introducers
- ✅ Get introducer by name
- ✅ Update introducer
- ✅ Delete introducer
- ✅ Final state verification

### 2. Discount Functions Test
- ✅ Tier up logic (local→adjacent→far)
- ✅ Percentage discount (various percentages)
- ✅ Edge cases (0%, decimal percentages)

### 3. Code Validation
- ✅ Python syntax check (py_compile)
- ✅ Module import test
- ✅ No syntax errors in app.py or database.py

## Data Flow

1. **Admin adds introducer**:
   Admin Dashboard → Add Introducer Form → Database (introducers table)

2. **User selects promoter**:
   Main UI → Promoter Checkbox → Dropdown → Session State

3. **Discount applied during optimization**:
   Session State → prepare_options() → Discount Functions → Modified Pricing

4. **Discount saved with quote**:
   Session State → store_submission() → Database (submissions table)

5. **Discount shown in reports**:
   Session State → generate_client_report_table_fixed() → Email/Report Display

## Key Design Decisions

1. **Discount Applied Before Optimization**: Ensures the optimizer sees the discounted prices and makes optimal decisions based on them.

2. **Original Tier Preserved**: While pricing uses a modified tier for tier_up discounts, the original tier is stored for reporting accuracy.

3. **Admin Fee Exclusion**: The £500 admin fee is never discounted, regardless of discount type.

4. **Database Normalization**: Introducers are stored separately with CRUD operations, not hardcoded.

5. **Session State Management**: Promoter selection is stored in session state for persistence during the workflow.

6. **Discount Visibility**: All reports and database records include full disclosure of promoter and discount applied.

## Usage Instructions

### For Administrators
1. Go to Admin Dashboard (sidebar selector)
2. Enter admin password
3. Navigate to "Introducer/Promoter Management" section
4. Add new introducers with name, type, and value
5. Edit or delete introducers as needed

### For Users
1. Complete site location as normal
2. Check "Use Promoter/Introducer" checkbox
3. Select introducer from dropdown
4. View discount info displayed below
5. Proceed with optimization as normal
6. Discount is automatically applied to pricing
7. Reports show promoter details

## Files Modified

- `database.py`: +92 lines (new table, CRUD operations)
- `app.py`: +188 lines (UI, discount logic, reporting)

## Backward Compatibility

- Existing quotes without promoters remain unaffected
- Database migration is automatic (new columns/tables created on first run)
- All promoter fields are optional in submissions table
- No breaking changes to existing functionality

## Future Enhancements (Not Implemented)

The following were explicitly excluded per requirements:
- Additional metadata for introducers
- Maximum/minimum discount validation
- Time-limited discounts
- Usage tracking/reporting
- Discount approval workflows
