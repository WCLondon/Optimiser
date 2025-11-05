# Hedgerow Parsing Fix Summary

## Issue
Trading Summary Hedgerows tab was not correctly offsetting deficits with surpluses, causing habitats like "Native hedgerow" to appear in requirements even when they should have been mitigated by higher distinctiveness surpluses like "Species-rich native hedgerow".

### Example from Issue
- **Input:**
  - Medium: Species-rich native hedgerow: +1.47 units (surplus)
  - Low: Native hedgerow: -0.70 units (deficit)
- **Expected:** Native hedgerow deficit offset by Medium surplus (trading rules allow Medium to offset Low)
- **Actual (before fix):** Native hedgerow showing 0.6996 units in requirements

## Root Cause
The `col_like()` function uses **substring matching** to find columns. When searching for a "Distinctiveness" column, it would match ANY column containing the word "Distinct", including summary columns like:
- "Medium Distinctiveness net change in units"
- "High Distinctiveness Summary"  
- "Cumulative availability of units"

This caused distinctiveness values to be populated with summary text instead of actual distinctiveness bands (Very High, High, Medium, Low, Very Low).

When distinctiveness is invalid/NA, the `can_offset_hedgerow()` function correctly returns `False` to prevent incorrect offsetting, which meant:
- Surpluses couldn't offset deficits even when trading rules allowed it
- Deficits that should have been mitigated appeared in final requirements

## Solution

### 1. Created `col_exact()` Helper Function
```python
def col_exact(df: pd.DataFrame, *cands: str) -> Optional[str]:
    """Find a column that exactly matches any of the candidate names (after canonicalization)"""
    cols = {canon(c): c for c in df.columns}
    for c in cands:
        if canon(c) in cols: 
            return cols[canon(c)]
    return None
```

### 2. Updated Distinctiveness Column Detection
```python
# OLD - substring matching (would match "Medium Distinctiveness net change in units")
distinctiveness_col = col_like(df, "Distinctiveness", "Distinct")

# NEW - exact matching (only matches "Distinctiveness" or "Distinct")
distinctiveness_col = col_exact(df, "Distinctiveness", "Distinct")
```

## Changes Made

### metric_reader.py
- **Lines 114-121:** Added `col_exact()` helper function
- **Line 267:** Changed distinctiveness detection to use `col_exact()` instead of `col_like()`

### Tests Added
- **test_with_summary_columns.py:** Reproduces the issue with summary columns and validates the fix
- **test_distinctiveness_column.py:** Ensures explicit Distinctiveness columns still work (regression test)

## Testing Results

All tests passing ✅

1. **test_with_summary_columns.py**
   - Reproduces issue with Trading Summary containing summary columns
   - Validates fix works correctly

2. **test_distinctiveness_column.py**  
   - Tests explicit "Distinctiveness" column format
   - Ensures no regression

3. **test_hedgerow_surplus_offsetting.py**
   - All 3 test scenarios pass
   - Tests various hedgerow trading rules

4. **test_hedgerow_watercourse_netgain.py**
   - All hedgerow and watercourse tests pass

5. **test_metric_reader.py**
   - All unit tests pass

6. **CodeQL Security Scan**
   - 0 alerts found ✅

## Impact

Hedgerow trading rules now work correctly even when Trading Summary sheets contain summary columns. Surpluses properly offset deficits according to the hedgerow trading rules:
- **Very High & High:** Same habitat required (like-for-like)
- **Medium, Low, Very Low:** Same distinctiveness or better can offset

This prevents unnecessary off-site hedgerow requirements when on-site surpluses can mitigate deficits.

## Note for Other Categories

This same issue may affect **Area Habitats** if they also use `col_like()` for distinctiveness detection with Trading Summary sheets that have summary columns. The fix would be identical - use `col_exact()` instead of `col_like()` for distinctiveness column detection.
