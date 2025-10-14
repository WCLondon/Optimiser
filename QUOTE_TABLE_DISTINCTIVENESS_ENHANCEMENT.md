# Quote Table Enhancement: Show Only Highest Distinctiveness in Paired Allocations

## Summary

When the optimiser produces a paired allocation (e.g., "Traditional Orchard + Mixed Scrub"), the quote table now displays only the habitat with the highest distinctiveness from the pair, along with its corresponding distinctiveness level.

## Changes Made

### Modified Function: `generate_client_report_table_fixed()` (app.py, lines ~2943-3050)

#### 1. Added Helper Function: `get_highest_distinctiveness_habitat()`

This new helper function handles the logic for processing paired allocations:

**Functionality:**
- Detects paired allocations by checking for " + " separator in the supply_habitat string
- For paired allocations:
  - Parses both habitat names
  - Looks up each habitat's distinctiveness from the catalog
  - Selects the habitat with the highest distinctiveness (lowest order value)
  - Returns: `(habitat_name, distinctiveness_level)`
- For non-paired allocations:
  - Returns the habitat as-is with its distinctiveness level

**Distinctiveness Priority (from highest to lowest):**
1. Very High / V.High
2. High
3. Medium
4. Low + 10% Net Gain
5. Low
6. 10% Net Gain
7. Very Low / V.Low

#### 2. Modified Supply Habitat Processing

**Before:**
```python
supply_habitat = alloc_row["supply_habitat"]
supply_cat_match = backend["HabitatCatalog"][backend["HabitatCatalog"]["habitat_name"] == supply_habitat]
if not supply_cat_match.empty:
    supply_distinctiveness = supply_cat_match["distinctiveness_name"].iloc[0]
else:
    supply_distinctiveness = "Medium"
```

**After:**
```python
supply_habitat_raw = alloc_row["supply_habitat"]
# For paired allocations, get only the highest distinctiveness habitat
supply_habitat, supply_distinctiveness = get_highest_distinctiveness_habitat(supply_habitat_raw)
```

## Behavior Examples

### Example 1: Traditional Orchard + Mixed Scrub (Medium + Low)
**Input:** Paired allocation with "Traditional Orchard + Mixed Scrub"
- Traditional Orchard: Medium distinctiveness
- Mixed Scrub: Low distinctiveness

**Quote Table Display:**
- **Habitats Supplied:** Traditional Orchard
- **Distinctiveness:** Medium

### Example 2: Woodland + Grassland (High + Medium)
**Input:** Paired allocation with "Woodland + Grassland"
- Woodland: High distinctiveness
- Grassland: Medium distinctiveness

**Quote Table Display:**
- **Habitats Supplied:** Woodland
- **Distinctiveness:** High

### Example 3: Single Habitat (Non-Paired)
**Input:** Regular allocation with "Mixed Scrub"

**Quote Table Display:**
- **Habitats Supplied:** Mixed Scrub
- **Distinctiveness:** Low
- *(No change in behavior)*

## What Remains Unchanged

✅ **Pricing Logic:** All unit prices, blended prices, and cost calculations remain exactly as before

✅ **Optimization Logic:** The optimizer still creates paired allocations with the same criteria

✅ **Unit Allocation:** Units supplied and effective units remain unchanged

✅ **Cost Calculations:** Total costs and offset costs remain unchanged

✅ **Manual Entries:** Manual hedgerow and watercourse entries are unaffected

✅ **Non-Paired Allocations:** Single habitat allocations work exactly as before

## Impact

### Positive Changes
✅ **Clearer Reports:** Quote tables show only the most relevant habitat information

✅ **Accurate Distinctiveness Display:** Clients see the highest distinctiveness level from paired allocations

✅ **Consistent Pricing:** All pricing remains correct and unchanged

✅ **Backward Compatible:** Non-paired allocations continue to work identically

### No Breaking Changes
⚠️ **Display Only:** This change only affects what is displayed in the quote table

⚠️ **No Financial Impact:** All costs, prices, and calculations remain the same

## Testing

A comprehensive test suite was created to verify the logic:

```bash
python /tmp/test_paired_allocation.py
```

**Test Results:**
- ✓ Medium distinctiveness beats Low distinctiveness
- ✓ Order of habitats in pair doesn't matter
- ✓ High distinctiveness beats Medium distinctiveness
- ✓ Very High distinctiveness beats High distinctiveness
- ✓ Single (non-paired) habitats work correctly
- ✓ All tests passed!

## Files Modified

- `app.py` - Added helper function and modified supply habitat processing in `generate_client_report_table_fixed()`

## Acceptance Criteria Met

✅ For any paired allocation in the quote table, display only the habitat with the higher distinctiveness

✅ Display the correct distinctiveness level (the highest of the pair)

✅ Underlying pricing logic is unchanged

✅ Quote table generation logic updated accordingly

## Technical Notes

- The helper function is defined within `generate_client_report_table_fixed()` to keep the change localized
- Uses the same distinctiveness order mapping that exists elsewhere in the codebase
- Minimal changes: ~60 lines added, 7 lines modified
- No new dependencies required
- No changes to function signatures or public APIs
