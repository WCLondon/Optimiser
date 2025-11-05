# Watercourse Net Gain SRM Implementation Summary

## Issue Resolution

Fixed the error: `"These demand habitats aren't in the catalog: ['Net Gain (Watercourses)']"`

## Root Cause

The validation check in `app.py` (line 4080) only allowed `NET_GAIN_LABEL` and `NET_GAIN_HEDGEROW_LABEL` in the exception list, but not `NET_GAIN_WATERCOURSE_LABEL`.

## Changes Made

### 1. Validation Fix
**File:** `app.py` line 4080

**Before:**
```python
unknown = [h for h in demand_df["habitat_name"] if h not in cat_names_run and h not in [NET_GAIN_LABEL, NET_GAIN_HEDGEROW_LABEL]]
```

**After:**
```python
unknown = [h for h in demand_df["habitat_name"] if h not in cat_names_run and h not in [NET_GAIN_LABEL, NET_GAIN_HEDGEROW_LABEL, NET_GAIN_WATERCOURSE_LABEL]]
```

### 2. Watercourse SRM Implementation

Implemented the Spatial Risk Multiplier (SRM) system for watercourse habitats, which uses watercourse catchments instead of LPA/NCA boundaries for tiering.

#### New Functions

**`wfs_point_query(wfs_url, lat, lon)`**
- Queries WFS services to find features containing a point
- Returns first matching feature or empty dict

**`get_watercourse_catchments_for_point(lat, lon)`**
- Fetches waterbody and operational catchment names for a location
- Returns `(waterbody_name, operational_catchment_name)`
- Handles missing data gracefully

**`calculate_watercourse_srm(site_waterbody, site_operational, bank_waterbody, bank_operational)`**
- Calculates SRM based on catchment proximity
- Rules:
  - Same waterbody catchment → SRM = 1.0 (no uplift)
  - Same operational catchment (different waterbody) → SRM = 0.75 (4/3 uplift)
  - Outside operational catchment → SRM = 0.5 (2× uplift)
- Returns SRM multiplier

#### Modified Functions

**`init_session_state()`**
- Added `target_waterbody`: stores site waterbody catchment name
- Added `target_operational_catchment`: stores site operational catchment name
- Added `bank_watercourse_catchments`: dict storing watercourse catchments for banks

**`find_site(postcode, address)`**
- Now also fetches watercourse catchments for the site
- Stores in session state for use during optimization

**Bank catchment loading (around line 4242)**
- Updated to also fetch watercourse catchments for each bank
- Stores in `st.session_state["bank_watercourse_catchments"]`

**`prepare_watercourse_options(...)`**
- Replaced LPA/NCA-based `tier_for_bank()` call with SRM calculation
- Fetches catchment data from session state
- Calculates SRM using `calculate_watercourse_srm()`
- Maps SRM to tier for pricing:
  - SRM >= 0.95 → "local"
  - SRM >= 0.70 → "adjacent"
  - SRM < 0.70 → "far"
- Stores SRM value in option dict for reference

### 3. Testing

**New Test Files:**

1. **`test_watercourse_netgain_validation.py`**
   - Verifies all three Net Gain labels are defined
   - Confirms validation check includes all three labels
   - Checks NET_GAIN_WATERCOURSE_LABEL is in HAB_CHOICES
   - Validates get_umbrella_for() handles watercourse label

2. **`test_watercourse_srm.py`**
   - Tests SRM calculation for same waterbody (SRM = 1.0)
   - Tests SRM calculation for same operational catchment (SRM = 0.75)
   - Tests SRM calculation for different operational catchment (SRM = 0.5)
   - Tests handling of missing catchment data
   - Tests case-insensitive catchment matching
   - Tests SRM to tier mapping

**Existing Tests:** All pass
- `test_hedgerow_watercourse_netgain.py` ✅
- `test_watercourse_trading_rules.py` ✅

## How It Works

### For Watercourse Habitats:

1. **Site Location:**
   - User enters postcode/address
   - System fetches:
     - LPA/NCA boundaries (for area and hedgerow habitats)
     - Waterbody and operational catchment names (for watercourse habitats)

2. **Bank Selection:**
   - When banks are selected for optimization
   - System fetches for each bank:
     - LPA/NCA boundaries (for area and hedgerow habitats)
     - Waterbody and operational catchment names (for watercourse habitats)

3. **Optimization:**
   - **Area habitats:** Use LPA/NCA-based tiering (local/adjacent/far)
   - **Hedgerow habitats:** Use LPA/NCA-based tiering (local/adjacent/far)
   - **Watercourse habitats:** Use SRM-based tiering
     - Calculate SRM based on catchment proximity
     - Map SRM to tier (1.0→local, 0.75→adjacent, 0.5→far)
     - Look up pricing for that tier

4. **Net Gain (Watercourses):**
   - Treated like "Low" distinctiveness within watercourse ledger
   - Can be satisfied by any watercourse habitat
   - Subject to SRM-based tiering (not LPA/NCA)
   - Respects watercourse-specific trading rules

## Data Sources

Watercourse catchments are queried from Environment Agency WFS services:

- **Waterbody Catchments:** 
  - `https://environment.data.gov.uk/spatialdata/water-framework-directive-river-waterbody-catchments-cycle-2/wfs`
  
- **Operational Catchments:**
  - `https://environment.data.gov.uk/spatialdata/water-framework-directive-river-operational-catchments-cycle-2/wfs`

## Benefits

1. **Accurate Watercourse Tiering:** Watercourse habitats now use scientifically appropriate catchment-based proximity instead of administrative boundaries

2. **Proper Net Gain Handling:** "Net Gain (Watercourses)" is now recognized and handled correctly

3. **Maintains Existing Behavior:** Area and hedgerow habitats continue to use LPA/NCA-based tiering

4. **Graceful Degradation:** If catchment data is unavailable, defaults to "far" tier (SRM = 0.5)

## Security

- CodeQL analysis: 0 alerts found ✅
- All tests passing ✅
- No new dependencies added ✅
