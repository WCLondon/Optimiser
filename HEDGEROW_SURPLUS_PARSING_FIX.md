# Hedgerow Surplus Parsing Fix

## Issue Summary
Hedgerow surpluses were not being read correctly by the metric reader when parsing BNG metric files, which prevented them from mitigating downstream deficits. This resulted in the optimiser incorrectly including hedgerow deficits (like "Non-native and ornamental hedgerow") in the off-site requirements even when sufficient surplus existed to offset them.

### Example from Issue
**Input data:**
- High: Species-rich native hedgerow with trees: **+0.37 units** (surplus) ✓
- Medium: Species-rich native hedgerow: **+0.13 units** (surplus) ✓
- Very Low: Non-native and ornamental hedgerow: **-0.03 units** (deficit) ⚠

**Expected behavior:**
The -0.03 deficit should be offset by the 0.50 total surplus (0.37 + 0.13)

**Actual behavior (before fix):**
The deficit appeared in the final requirements despite available surplus

## Root Cause
The `normalise_requirements` function in `metric_reader.py` was not checking for a "Distinctiveness" column in the Trading Summary dataframe. When hedgerow sheets had distinctiveness values in a column (a common format in BNG metric files), those values were not being extracted, leaving all distinctiveness as `<NA>`.

Without distinctiveness information:
- The `apply_hedgerow_offsets` function could not apply trading rules
- Surpluses could not be matched with deficits
- All deficits remained unmet regardless of available surplus

## Solution
Enhanced the `normalise_requirements` function to:
1. Check for a "Distinctiveness" column in the dataframe first
2. Use that column directly if present
3. Fall back to extracting from section headers if not present

Additionally fixed several related issues:
- Updated `find_header_row` to detect hedgerow/watercourse headers (which don't have "group" column)
- Added filter to remove section header rows (rows with NaN in project_wide_change)
- Added "Very Low" pattern (VL_PAT) to correctly identify "Very Low Distinctiveness"
- Updated `resolve_broad_group_col` to exclude distinctiveness columns from being treated as broad groups

## Changes Made

### 1. Enhanced Distinctiveness Parsing (metric_reader.py, lines 244-256)
```python
# Check if there's a Distinctiveness column in the dataframe
distinctiveness_col = col_like(df, "Distinctiveness", "Distinct")

if distinctiveness_col and distinctiveness_col in df.columns:
    # Use the Distinctiveness column directly
    df["__distinctiveness__"] = df[distinctiveness_col].astype(str).map(clean_text)
else:
    # Fall back to extracting from section headers
    habitat_list = df[habitat_col].astype(str).map(clean_text).tolist()
    band_map = build_band_map_from_raw(raw, habitat_list)
    df["__distinctiveness__"] = df[habitat_col].astype(str).map(lambda x: band_map.get(clean_text(x), pd.NA))
```

### 2. Fixed Header Row Detection (metric_reader.py, lines 86-98)
```python
def find_header_row(df: pd.DataFrame, within_rows: int = 80) -> Optional[int]:
    """Find the header row in a trading summary sheet"""
    for i in range(min(within_rows, len(df))):
        row = " ".join([clean_text(x) for x in df.iloc[i].tolist()]).lower()
        # Check for area habitat headers (with group column)
        if ("group" in row) and (("on-site" in row and "off-site" in row and "project" in row)
                                 or "project wide" in row or "project-wide" in row):
            return i
        # Check for hedgerow/watercourse headers (without group column)
        if (("habitat" in row or "feature" in row) and 
            ("project" in row and ("unit" in row or "change" in row))):
            return i
    return None
```

### 3. Added Very Low Pattern (metric_reader.py, lines 167-171)
```python
VH_PAT = re.compile(r"\bvery\s*high\b.*distinct", re.I)
H_PAT  = re.compile(r"\bhigh\b.*distinct", re.I)
M_PAT  = re.compile(r"\bmedium\b.*distinct", re.I)
VL_PAT = re.compile(r"\bvery\s*low\b.*distinct", re.I)  # NEW
L_PAT  = re.compile(r"\blow\b.*distinct", re.I)
```

### 4. Filter Section Header Rows (metric_reader.py, line 243)
```python
# Filter out rows where project_wide_change is NaN (section headers, repeated headers)
df = df[~df[proj_col].isna()].copy()
```

### 5. Exclude Distinctiveness from Broad Group (metric_reader.py, lines 142-144)
```python
# Exclude distinctiveness columns
if any(k in name for k in ["distinct"]):
    return False
```

## Testing

### New Tests Created
1. **test_hedgerow_surplus_offsetting.py** - Comprehensive test suite with 3 scenarios:
   - Surplus offsetting with Distinctiveness column format
   - Surplus offsetting with section header format (backward compatibility)
   - Hedgerow trading rules verification

2. **test_issue_verification.py** - Verifies the exact scenario from the GitHub issue

### Test Results
All tests pass:
```
✅ test_hedgerow_surplus_offsetting.py - 3/3 tests passed
✅ test_issue_verification.py - Issue resolved
✅ test_hedgerow_watercourse_netgain.py - 3/3 tests passed
✅ test_baseline_reading.py - All tests passed
✅ test_metric_reader.py - All tests passed
✅ test_rounding_fix.py - All tests passed
```

### Security Check
```
✅ CodeQL: No security issues found
```

## Impact
Hedgerow surpluses now correctly offset deficits according to hedgerow trading rules:
- **Very High & High**: Like-for-like only (same habitat required)
- **Medium, Low, Very Low**: Same distinctiveness or better

This significantly reduces unnecessary off-site hedgerow requirements when on-site surplus is available to mitigate deficits.

## Example Verification
Using the exact data from the issue:
```
Input:
  High: Species-rich native hedgerow with trees: +0.37 units
  Medium: Species-rich native hedgerow: +0.13 units
  Very Low: Non-native and ornamental hedgerow: -0.03 units
  Total surplus: 0.50 units
  Total deficit: 0.03 units
  Net gain requirement: 0.094 units

Output (after fix):
  (empty - all requirements covered by on-site surplus)

✅ Non-native hedgerow deficit correctly offset by surplus
✅ Net gain also covered by remaining surplus (0.47 units)
✅ No off-site requirements needed!
```

## Files Modified
- `metric_reader.py`: Core parsing logic fixes
- `test_hedgerow_surplus_offsetting.py`: New comprehensive test suite
- `test_issue_verification.py`: Issue verification test

## Backward Compatibility
The fix maintains full backward compatibility:
- Works with both "Distinctiveness" column format (new)
- Works with section header format (existing)
- All existing tests pass without modification
