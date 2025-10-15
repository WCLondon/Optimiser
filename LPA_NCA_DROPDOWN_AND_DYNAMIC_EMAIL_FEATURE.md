# LPA/NCA Dropdown and Dynamic Promoter Email Implementation Summary

## Overview
This implementation adds two major features to the BNG Optimiser application:
1. **LPA/NCA Dropdown Selection** for promoters to select location without requiring postcode/address
2. **Dynamic Promoter Email Text** that changes based on whether a promoter is selected

## Feature 1: LPA/NCA Dropdown Selection for Promoters

### Problem Statement
Some promoters provide only the NCA and LPA for the target site to preserve site identity. They need a way to specify the location without entering a postcode or address.

### Solution
Added searchable dropdown menus at the top of the "Locate target site" section that allow users to directly select LPA (Local Planning Authority) and NCA (National Character Area) from lists populated from the backend Banks data.

### Implementation Details

#### Session State Changes (app.py)
Added three new session state variables:
- `use_lpa_nca_dropdown`: Boolean flag indicating dropdown selection is active
- `selected_lpa_dropdown`: Currently selected LPA from dropdown
- `selected_nca_dropdown`: Currently selected NCA from dropdown

#### UI Changes (app.py, lines ~966-1050)
Added new UI section before the postcode/address inputs:

**Option A: Select LPA/NCA directly (for promoters)**
- Two searchable selectboxes side-by-side for LPA and NCA
- Populated from unique values in `backend["Banks"]["lpa_name"]` and `backend["Banks"]["nca_name"]`
- "Apply LPA/NCA Selection" button to confirm selection
- Updates session state with selected LPA/NCA names
- Clears location-based data (lat/lon, geometries, neighbors) since no coordinates are available

**Option B: Enter postcode or address (standard method)**
- Existing postcode/address inputs remain unchanged
- When used, clears the `use_lpa_nca_dropdown` flag

#### Location Banner Update
Updated the persistent location banner to show source of location data:
- "(via dropdown)" - when LPA/NCA selected from dropdowns
- "(via postcode/address)" - when location found via postcode or address

### Usage
1. Upload backend workbook to populate LPA/NCA lists
2. Select desired LPA and/or NCA from dropdowns
3. Click "Apply LPA/NCA Selection"
4. Location banner shows selected LPA/NCA with "(via dropdown)" indicator
5. Proceed with demand entry and optimization as normal

### Limitations
- No map display when using dropdown (no coordinates available)
- No neighbor calculations (requires geometry)
- User must still select appropriate habitat demands and contract sizes

## Feature 2: Dynamic Promoter Email Text

### Problem Statement
The client email should have different introductory text based on whether a promoter is involved. Some promoters also don't provide discounts but need to be in the system for email customization.

### Solution
1. Added 'no_discount' option to introducer/promoter types
2. Modified email generation to conditionally render intro text based on promoter selection
3. Hide discount information for no_discount promoters

### Implementation Details

#### Database Schema Update (database.py, lines ~186-220)
Updated the `introducers` table CHECK constraint to include 'no_discount':
```sql
CHECK(discount_type IN ('tier_up', 'percentage', 'no_discount'))
```

Added migration logic to update existing databases:
- Drops old constraint if it exists
- Adds new constraint with 'no_discount' option
- Handles errors gracefully for fresh installations

#### Admin Dashboard Updates (app.py, lines ~377-460)

**Add New Introducer Form:**
- Added 'no_discount' to discount type selectbox
- Updated help text to mention no_discount
- Disabled discount value input when no_discount is selected
- Sets discount_value to 0.0 for no_discount type

**Introducer List Display:**
- Added handling for no_discount type: displays "No Discount"
- Shows discount value only for percentage type
- Shows "Tier Up" for tier_up type

**Edit Introducer Form:**
- Added 'no_discount' to discount type selectbox
- Disabled discount value input when no_discount is selected
- Sets discount_value to 0.0 when saving no_discount type

#### Main UI Updates (app.py, lines ~1163-1169)
Updated promoter selection info display:
- Shows "No Discount Applied: Promoter registered for dynamic email text only" for no_discount type
- Maintains existing messages for tier_up and percentage types

#### Email Generation Updates (app.py, lines ~3522-3560)

**Dynamic Intro Text:**
- **With Promoter:** "{Promoter Name} has advised us that you need Biodiversity Net Gain units for your development in {location}, and we're here to help you discharge your BNG condition."
- **Without Promoter:** "Thank you for enquiring about BNG Units for your development in {location}"

**Discount Information:**
- Only displayed when promoter has actual discount (not no_discount)
- Hidden completely for no_discount promoters

### Email Text Examples

#### No Promoter Selected
```
Dear {client_name}

Our Ref: {ref_number}

Thank you for enquiring about BNG Units for your development in {location}

About Us
...
```

#### Promoter with Discount
```
Dear {client_name}

Our Ref: {ref_number}

Arbtech has advised us that you need Biodiversity Net Gain units for your development in {location}, and we're here to help you discharge your BNG condition.

About Us
...

Your Quote - £{total} + VAT

Discount Applied: Introducer/Promoter: Arbtech
Discount Type: 10% percentage discount on all items (excluding £500 admin fee)
...
```

#### Promoter with No Discount
```
Dear {client_name}

Our Ref: {ref_number}

GreenPlanning Ltd has advised us that you need Biodiversity Net Gain units for your development in {location}, and we're here to help you discharge your BNG condition.

About Us
...

Your Quote - £{total} + VAT

See a detailed breakdown...
```

### Discount Application Logic
The existing discount application logic (`get_active_promoter_discount()` and pricing functions) already handles no_discount correctly:
- `promoter_discount_type == "tier_up"` checks will fail for no_discount
- `promoter_discount_type == "percentage"` checks will fail for no_discount
- No discount is applied to pricing when type is no_discount

## Files Modified

### app.py
1. **Session State Initialization** (lines ~76-115)
   - Added `use_lpa_nca_dropdown`, `selected_lpa_dropdown`, `selected_nca_dropdown`

2. **Locate Target Site UI** (lines ~966-1050)
   - Added LPA/NCA dropdown selection interface
   - Updated location banner to show source

3. **Admin Dashboard** (lines ~377-460)
   - Updated Add/Edit introducer forms to support no_discount
   - Updated display to handle no_discount type

4. **Main UI Promoter Section** (lines ~1163-1169)
   - Updated discount info display for no_discount

5. **Email Generation** (lines ~3522-3560)
   - Implemented dynamic intro text based on promoter
   - Conditional discount display

### database.py
1. **Introducers Table Schema** (lines ~186-220)
   - Updated CHECK constraint to include 'no_discount'
   - Added migration logic for existing databases

## Testing Performed

### Syntax Validation
- ✅ app.py syntax check passed
- ✅ database.py syntax check passed

### Manual Testing Required
1. **LPA/NCA Dropdown:**
   - Upload backend and verify LPA/NCA lists populate
   - Select LPA/NCA and verify location banner updates
   - Verify optimization works with dropdown-selected location
   - Verify switching between dropdown and postcode/address methods

2. **Dynamic Email:**
   - Add introducer with no_discount type
   - Generate email with no promoter selected
   - Generate email with promoter (with discount)
   - Generate email with promoter (no_discount)
   - Verify intro text changes correctly
   - Verify discount info shows/hides appropriately

## Backward Compatibility

### Database Migration
- Existing databases will be automatically migrated to support no_discount
- Migration is non-destructive and handles errors gracefully
- Existing introducers retain their current discount types

### Session State
- New session state variables have safe defaults
- Existing workflows unaffected by new variables

### UI Changes
- LPA/NCA dropdown is additive; existing postcode/address method still works
- Location banner enhanced but backward compatible
- Admin dashboard changes are additive

## Usage Instructions

### For Promoters Using LPA/NCA Dropdown
1. Open the Optimiser application
2. Upload backend workbook in sidebar
3. In "Locate target site" section, use **Option A**
4. Select LPA from first dropdown
5. Select NCA from second dropdown
6. Click "Apply LPA/NCA Selection"
7. Location banner shows selected LPA/NCA with "(via dropdown)"
8. Continue with demand entry and optimization

### For Admins Adding No-Discount Promoters
1. Switch to Admin Dashboard mode
2. Expand "➕ Add New Introducer"
3. Enter promoter name
4. Select "no_discount" from Discount Type dropdown
5. Note: Discount Value field is disabled
6. Click "Add Introducer"
7. Promoter now appears in list as "No Discount"

### For Users Generating Emails
- Email intro text automatically adjusts based on promoter selection
- No action required from user
- Discount information only shown for promoters with actual discounts

## Key Design Decisions

1. **Searchable Dropdowns**: Used standard Streamlit selectbox which provides type-ahead search capability out of the box

2. **No Coordinates for Dropdown**: When using LPA/NCA dropdown, no lat/lon or geometries are set. This is intentional as the exact site location is not known.

3. **No Discount as Separate Type**: Rather than adding a boolean flag, no_discount is a distinct discount_type. This maintains consistency with existing tier_up and percentage types.

4. **Email Text Priority**: Promoter name takes precedence in email intro. The generic "Thank you for enquiring" only appears when no promoter is selected.

5. **Discount Display Logic**: Discount information is shown based on both promoter existence AND discount type not being no_discount.

6. **Migration Strategy**: Database migration is handled inline during initialization, ensuring existing databases work without manual intervention.

## Future Enhancements (Not Implemented)

1. **LPA/NCA Geometry Lookup**: Could fetch geometries from ArcGIS services based on selected LPA/NCA names to enable map display

2. **Neighbor Calculation**: Could calculate neighbors for dropdown-selected locations by querying spatial services

3. **Promoter Templates**: Could support fully customizable email templates per promoter

4. **Batch LPA/NCA Operations**: Could support selecting multiple LPA/NCA combinations at once

5. **LPA/NCA Validation**: Could validate that selected LPA/NCA combination exists in actual stock

## Summary

Both features have been successfully implemented with:
- Minimal code changes (surgical modifications)
- Full backward compatibility
- Comprehensive error handling
- Clear user feedback
- Maintainable code structure

The implementation follows the existing patterns in the codebase and integrates seamlessly with the promoter discount system already in place.
