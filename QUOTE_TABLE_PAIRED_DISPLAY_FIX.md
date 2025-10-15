# Quote Table Paired Allocation Display Fix

## Issue Summary
When the optimiser produces a paired allocation (e.g., Traditional Orchard + Mixed Scrub), the quote table should display only the highest distinctiveness habitat and its corresponding level, rather than showing both habitats concatenated with a "+".

## Problem
Previously, paired allocations were displayed in the quote table as:
- **Habitats Supplied**: "Traditional Orchard + Mixed Scrub"
- **Distinctiveness**: Would show whichever habitat was looked up (often incorrect)

This made the quote table confusing and didn't properly represent which habitat was being used to meet the distinctiveness requirements.

## Solution
Modified the `generate_client_report_table_fixed` function in `app.py` (lines 2997-3049) to:
1. Detect paired allocations by checking the `allocation_type` column
2. Parse the `paired_parts` JSON data to extract both habitats
3. Look up the distinctiveness level for each habitat from the HabitatCatalog
4. Compare distinctiveness values using the global `dist_levels_map`
5. Select and display only the habitat with the highest distinctiveness value

## Implementation Details

### Code Location
`app.py`, lines 2997-3049 in the `generate_client_report_table_fixed` function

### Logic Flow
```python
# For paired allocations:
1. Check if allocation_type == "paired"
2. Parse paired_parts JSON array
3. For each habitat in the pair:
   - Look up habitat in HabitatCatalog
   - Get distinctiveness_name
   - Get distinctiveness numeric value from dist_levels_map
4. Select habitat with max(distinctiveness_value)
5. Display only that habitat and its distinctiveness
```

### Example Transformation

**Before:**
- Habitats Supplied: "Traditional Orchard + Mixed Scrub"
- Distinctiveness: "Medium" (incorrect)

**After:**
- Habitats Supplied: "Traditional Orchard"
- Distinctiveness: "High" (correct - Traditional Orchard has higher distinctiveness than Mixed Scrub)

## Impact

### What Changed
✅ Quote table now shows only the highest distinctiveness habitat for paired allocations
✅ Distinctiveness column displays the correct level for the shown habitat
✅ More accurate representation of mitigation being provided

### What Didn't Change
✅ Pricing logic remains completely unchanged
✅ Optimization logic remains completely unchanged
✅ Cost calculations remain completely unchanged
✅ Allocation logic remains completely unchanged
✅ Non-paired allocations display exactly as before

## Testing

### Test Scenarios
1. **Traditional Orchard (High) + Mixed Scrub (Medium)**
   - Display: Traditional Orchard (High)
   - Reason: High > Medium

2. **Woodland (Very High) + Grassland (Low)**
   - Display: Woodland (Very High)
   - Reason: Very High > Low

3. **Mixed Scrub (Medium) + Grassland (Low)**
   - Display: Mixed Scrub (Medium)
   - Reason: Medium > Low

### Fallback Behavior
If paired_parts data is missing or invalid, the function falls back to the original behavior to prevent errors.

## Files Modified
- `app.py` (lines 2997-3049) - Added paired allocation display logic in `generate_client_report_table_fixed`

## Verification
Run the following to verify syntax:
```bash
python -m py_compile app.py
```

All syntax checks pass successfully.
