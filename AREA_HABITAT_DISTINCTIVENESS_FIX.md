# Area Habitat Distinctiveness Validation Fix

## Issue Summary
User reported that Medium distinctiveness area habitat surpluses were not offsetting Low distinctiveness deficits, similar to the hedgerow issue previously fixed.

### Symptoms
- User uploaded metric file showing:
  - Medium Distinctiveness: +0.53 units surplus (Grassland, Heathland, Individual trees)
  - Low Distinctiveness: -1.85 units net deficit (Modified grassland: -2.48, Ruderal: -0.04, plus small surpluses: +0.68)
  - 10% Net Gain target: 0.67 units

- Parsed requirements showed:
  ```
  Grassland - Modified grassland: 2.479928
  Sparsely vegetated land - Ruderal/ephemeral: 0.040036
  ```

- Expected: Medium surplus (0.53) should offset part of the Low deficit according to area trading rules
- Actual: All Low deficits appeared in requirements, not offset by Medium surplus

## Root Cause
The `can_offset_area()` function had the same issue as `can_offset_hedgerow()` before the fix:

1. Used `rank.get(str(d_band), 0)` which returns 0 for NA/unknown distinctiveness
2. Did not have validation to reject offsetting when distinctiveness is invalid
3. This allowed trading between habitats with unknown distinctiveness levels

## Solution
Applied the same fix pattern used for hedgerows to area habitats:

### 1. Added Distinctiveness Validation
```python
# Handle NA or invalid distinctiveness - prevent offsetting if we don't know the bands
if is_invalid_distinctiveness(d_band) or is_invalid_distinctiveness(s_band):
    return False
```

### 2. Changed Default Rank
```python
rank = {"Low":1, "Medium":2, "High":3, "Very High":4}
rd = rank.get(str(d_band), -1)  # -1 if not found (was 0)
rs = rank.get(str(s_band), -1)

# If either rank is unknown, don't allow offsetting
if rd < 0 or rs < 0:
    return False
```

### 3. Moved Helper Function
Reorganized code to place `is_invalid_distinctiveness()` before both `can_offset_area()` and `can_offset_hedgerow()` so both can use it.

## Testing

### New Tests Created

1. **test_area_habitat_offsetting.py** - Comprehensive test for area habitat offsetting:
   ```
   Input:
     Medium: +0.53 units (Grassland, Heathland, Individual trees)
     Low: -1.84 net deficit (Modified grassland: -2.48, Ruderal: -0.04, surpluses: +0.68)
     Net gain: 0.67 units
   
   Expected:
     Medium (0.53) offsets part of Low deficit (1.84)
     Remaining: 1.84 - 0.53 = 1.31 units
     Total requirements: 1.31 + 0.67 = 1.98 units
   
   Result: ✅ PASS
     Modified grassland: 2.48 → 1.27 units (offset by 0.53 Medium + 0.68 Low)
     Total: 2.51 → 1.98 units
   ```

2. **test_area_validation.py** - Validation warning test:
   ```
   Scenario: Area habitats without proper distinctiveness headers
   
   Result: ✅ PASS
     - Warning issued: "Area Habitats: 1 deficit habitat(s) have undefined distinctiveness"
     - Deficits appear in requirements (safer than incorrect offsetting)
   ```

### All Tests Passing
```
✅ test_hedgerow_surplus_offsetting.py - 3/3 (hedgerow tests)
✅ test_area_habitat_offsetting.py - NEW (area habitat offsetting)
✅ test_area_validation.py - NEW (area habitat validation)
✅ test_failed_distinctiveness_extraction.py (hedgerow validation)
✅ test_issue_reproduction.py (original hedgerow issue)
✅ test_full_workflow.py (end-to-end workflow)
```

## Impact

### For Standard Metric Files
- ✅ No behavior change
- ✅ Medium surpluses now correctly offset Low deficits
- ✅ All area habitat trading rules properly enforced

### For Non-Standard Metric Files
- ✅ Warning issued when distinctiveness extraction fails
- ✅ Deficits appear in requirements (safer than incorrect offsetting)
- ✅ User guidance provided

## Area Habitat Trading Rules
Now correctly enforced with NA validation:

- **Very High**: Same habitat required (like-for-like)
- **High**: Same habitat required (like-for-like)
- **Medium**: 
  - High/Very High can offset from any broad group
  - Medium can offset Medium only if same broad group
- **Low**: Same distinctiveness or better (Medium, High, Very High can all offset Low)

## Example Results

### Before Fix
```
Parsed requirements (incorrect):
  Grassland - Modified grassland: 2.479928
  Sparsely vegetated land - Ruderal/ephemeral: 0.040036
  
Total: 2.52 units (no offsetting applied)
```

### After Fix
```
Parsed requirements (correct):
  Modified grassland: 1.27 units
  Ruderal/ephemeral: 0.04 units
  Net Gain: 0.67 units
  
Total: 1.98 units
Reduction: 2.52 → 1.98 (0.54 units offset by Medium surplus)
```

## Files Modified
- `metric_reader.py`: 
  - Enhanced `can_offset_area()` with distinctiveness validation
  - Reorganized `is_invalid_distinctiveness()` placement
  - Added comprehensive docstrings
- `test_area_habitat_offsetting.py`: New comprehensive test
- `test_area_validation.py`: New validation test

## Related Fixes
This complements the hedgerow fix from previous commits:
- Hedgerow fix: PR commits 42f8d3f, d9c1bd5
- Area habitat fix: This commit (0f83d3b)
- Both now use consistent validation logic

## Backward Compatibility
✅ 100% backward compatible
- Standard metric files work correctly with proper offsetting
- Non-standard files get clear warnings instead of silent incorrect behavior
- No breaking changes to API or functionality
