# Hedgerow and Watercourse Net Gain Parsing Fix

## Issue
The optimiser was not calculating and inserting the hedgerow net gain (and watercourse net gain) requirement from the "Headline Results" tab in the BNG metric file.

### Example from Issue
```
Unit Type         Target   Baseline Units  Units Required  Unit Deficit  
Habitat units     10.00%   1.81            2.00            1.44
Hedgerow units    10.00%   0.94            1.04            1.04
Watercourse units 10.00%   0.00            0.00            0.00
```

**Before Fix:**
- Only hedgerow deficits from the Trading Summary sheet were parsed (1.04 units)
- The net gain requirement (0.94 × 10% = 0.094 units) was missing

**After Fix:**
- Hedgerow deficits from Trading Summary: 1.04 units
- Hedgerow net gain from Headline Results: 0.094 units
- Total hedgerow requirement: 1.134 units ✓

## Solution
Updated `metric_reader.py` to calculate net gain requirements for hedgerows and watercourses from the Headline Results tab, matching the existing behavior for habitat units.

### Changes Made

1. **Updated hedgerow parsing** (lines 785-807 in metric_reader.py):
   - Added calculation of hedgerow net gain: `baseline_units × target_percent`
   - Added "Net Gain (Hedgerows)" entry to requirements when baseline > 0
   
2. **Updated watercourse parsing** (lines 809-831 in metric_reader.py):
   - Added calculation of watercourse net gain: `baseline_units × target_percent`
   - Added "Net Gain (Watercourses)" entry to requirements when baseline > 0

3. **Updated documentation**:
   - Updated function docstring to reflect new behavior
   - Added clarification that hedgerows/watercourses don't support on-site offsetting

### Implementation Details

The net gain calculation follows this logic:
```python
# For hedgerows
hedgerow_info = headline_all["hedgerow"]
hedge_target_pct = hedgerow_info["target_percent"]
hedge_baseline_units = hedgerow_info["baseline_units"]
hedge_net_gain_requirement = hedge_baseline_units * hedge_target_pct

if hedge_net_gain_requirement > 1e-9:
    hedge_requirements.append({
        "habitat": "Net Gain (Hedgerows)",
        "units": round(hedge_net_gain_requirement, 4)
    })
```

The same logic applies to watercourses.

## Testing

Created comprehensive test suite in `test_hedgerow_watercourse_netgain.py`:

1. **test_hedgerow_netgain_with_deficits**: Verifies hedgerow net gain is calculated correctly when there are trading summary deficits
2. **test_watercourse_netgain**: Verifies watercourse net gain is calculated correctly
3. **test_netgain_only_when_baseline_positive**: Verifies net gain is not added when baseline units are zero

All existing tests continue to pass, including:
- `test_baseline_reading.py`: Verifies baseline info parsing for all unit types

## Example Output

Using the metric data from the issue:

```
Hedgerow Requirements:
             habitat  units
     Native hedgerow  1.040
Net Gain (Hedgerows)  0.094

Total hedgerow units required: 1.134
```

This matches the expected behavior where:
- Specific habitat deficits (Native hedgerow) are listed separately
- Net gain requirement is added as a separate line item
- The optimiser can fulfill "Net Gain (Hedgerows)" with any hedgerow habitat credit

## Consistency

This change brings hedgerow and watercourse parsing in line with the existing habitat unit parsing:

| Unit Type   | Trading Summary Deficits | Net Gain Calculation | Special Label |
|-------------|-------------------------|----------------------|---------------|
| Habitat     | ✓ Parsed                | ✓ Calculated         | "Net Gain (Low-equivalent)" |
| Hedgerow    | ✓ Parsed                | ✓ **NOW** Calculated | "Net Gain (Hedgerows)" |
| Watercourse | ✓ Parsed                | ✓ **NOW** Calculated | "Net Gain (Watercourses)" |

## Files Changed

1. `metric_reader.py`: Added net gain calculations for hedgerows and watercourses
2. `test_hedgerow_watercourse_netgain.py`: New comprehensive test suite

## Verification

Run tests to verify the fix:
```bash
python test_baseline_reading.py
python test_hedgerow_watercourse_netgain.py
```

All tests should pass with ✅ indicators.
