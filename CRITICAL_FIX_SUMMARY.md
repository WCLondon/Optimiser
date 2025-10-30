# Critical Fix: Metric Reader Logic Implementation

## Issue
The initial implementation extracted raw deficits from BNG metric files, but this was incorrect. Per user feedback:

> "Ok so we only need to provide off-site mitigation for the '🧮 Still needs mitigation OFF-SITE (after offsets + surplus→headline)' readout in the metric reader. Which should match the 'total units to mitigate'."

## Root Cause
The metric reader app applies complex trading logic to calculate what needs off-site mitigation:
1. On-site offsets reduce deficits using surpluses
2. Headline Net Gain is calculated from target % × baseline
3. Remaining surpluses are allocated to headline
4. Only the residual needs off-site sourcing

Simply extracting raw deficits ignores this entire calculation flow.

## Fix Applied (Commit fc62557)

Completely rewrote `metric_reader.py` to follow metric reader logic exactly:

### New Functions Added
```python
can_offset_area()              # Implements DEFRA trading rules
apply_area_offsets()           # Calculates on-site offsets and residuals  
parse_headline_target_row()    # Extracts Net Gain target from Headline Results
allocate_to_headline()         # Allocates surpluses to headline requirement
```

### Updated parse_metric_requirements()
**Before**: Simple deficit extraction
```python
def extract_deficits(df):
    deficits = df[df["project_wide_change"] < 0]
    return deficits.abs()
```

**After**: Full metric reader flow
```python
# 1. Apply on-site offsets
alloc = apply_area_offsets(area_norm)
residual_table = alloc["residual_off_site"]

# 2. Parse headline target
headline_info = parse_headline_target_row(xls)
headline_requirement = baseline * target_pct

# 3. Allocate surpluses to headline
applied = allocate_to_headline(headline_requirement, surplus_detail)

# 4. Calculate headline remainder
residual_headline = headline_requirement - applied

# 5. Return combined off-site needs
return habitat_residuals + headline_remainder
```

## Trading Rules Implemented

Per DEFRA guidance:
- **Very High distinctiveness**: Only like-for-like habitat
- **High distinctiveness**: Only like-for-like habitat
- **Medium distinctiveness**: 
  - Can be offset by High or Very High (any broad group)
  - Can be offset by Medium (same broad group only)
- **Low distinctiveness**: Can be offset by any distinctiveness ≥ Low

## Impact

### Before Fix
User uploads metric → Gets raw deficits → Numbers don't match metric reader

Example:
- Metric shows: "Total units to mitigate: 12.5" (after offsets + headline)
- Import gave: 20.3 units (raw deficits, no offsets applied)
- **Mismatch!** ❌

### After Fix
User uploads metric → Gets exact off-site mitigation → Matches metric reader

Example:
- Metric shows: "Total units to mitigate: 12.5"
- Import gives: 12.5 units (habitat residuals 2.5 + headline remainder 10.0)
- **Perfect match!** ✅

## Validation

✅ Unit tests pass
✅ Trading rules validated
✅ CodeQL security scan: 0 alerts
✅ Documentation updated
✅ User comment addressed

## Files Modified
- `metric_reader.py`: +230 lines (trading logic)
- `BNG_METRIC_IMPORT_GUIDE.md`: Updated to clarify off-site mitigation
- `IMPLEMENTATION_METRIC_IMPORT.md`: Updated technical details

## Conclusion
The metric reader now correctly calculates OFF-SITE mitigation requirements following the exact logic of the DEFRA BNG Metric Reader app. Users get the right numbers to quote for.
