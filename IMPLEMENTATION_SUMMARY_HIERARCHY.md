# Implementation Summary: Medium Distinctiveness Habitat Hierarchy

## Issue Addressed
When processing on-site offsets, Medium distinctiveness habitats now follow a priority hierarchy where certain broad groups are processed first, as they are more important to mitigate (higher cost or more difficult to replace).

## Changes Made

### 1. Core Implementation (`metric_reader.py`)

#### Added Module-Level Constant
```python
PRIORITY_MEDIUM_GROUPS = {
    "cropland",
    "lakes",
    "sparsely vegetated land",
    "urban",
    "individual trees",
    "woodland and forest",
    "intertidal sediment",
    "intertidal hard structures"
}
```

#### Modified `apply_area_offsets()` Function
- **Sorting Logic**: Deficits are now sorted with priority:
  1. Very High distinctiveness (unchanged)
  2. High distinctiveness (unchanged)
  3. **Medium distinctiveness - PRIORITY groups** (NEW)
  4. **Medium distinctiveness - SECONDARY groups** (Grassland, Heathland and shrub) (NEW)
  5. Low distinctiveness (unchanged)

- **Flow Log**: Added comprehensive tracking of all allocations with structure:
  ```python
  {
      "deficit_habitat": str,
      "deficit_broad_group": str,
      "deficit_distinctiveness": str,
      "surplus_habitat": str,
      "surplus_broad_group": str,
      "surplus_distinctiveness": str,
      "units_allocated": float,
      "priority_medium": bool  # True for priority groups
  }
  ```

#### Updated `parse_metric_requirements()` Function
- Returns `flow_log` in result dictionary
- Updated docstring to document flow log and hierarchy

### 2. Testing (`test_medium_hierarchy.py`)

Created comprehensive test suite with three test scenarios:
- **Priority ordering test**: Verifies priority groups processed before secondary
- **Full example test**: End-to-end parsing with realistic Excel file
- **Non-Medium unchanged test**: Confirms other distinctiveness levels unaffected

### 3. Documentation

#### `MEDIUM_HIERARCHY_IMPLEMENTATION.md`
- Detailed explanation of the hierarchy
- Processing order documentation
- Flow log structure reference
- Example scenarios

## Verification Results

### Manual Testing
✅ All priority groups processed before secondary groups  
✅ Priority flag correctly set in flow log  
✅ Broad group names used (not specific habitat names)  
✅ Original functionality preserved for Low/High/Very High  

### Automated Testing
✅ Original `test_metric_reader.py` passes  
✅ New `test_medium_hierarchy.py` passes (3/3 scenarios)  
✅ Verified with actual BNG habitat names  

### Code Quality
✅ Magic numbers extracted to named constants  
✅ Priority groups moved to module-level constant  
✅ Comprehensive docstrings  
✅ All code review feedback addressed  

## Key Implementation Details

1. **Uses Broad Groups**: Implementation correctly uses the "Broad habitat" column values, not specific habitat names
   - Example: "Cropland - Arable field margins" → "Cropland" group → Priority
   - Example: "Grassland - Other lowland" → "Grassland" group → Secondary

2. **No Changes to Eligibility Rules**: Only the processing order changed, not which surpluses can offset which deficits

3. **Backwards Compatible**: 
   - Returns flow_log as new optional field
   - Existing code that doesn't use flow_log continues to work
   - All existing test cases pass

## Example Output

Given deficits in both priority and secondary Medium groups:

```
Processing order (flow log):
1. ✓ PRIORITY | Cropland - Arable field margins
2. ✓ PRIORITY | Lakes - Ponds (non-priority)
3. ✓ PRIORITY | Urban - Cemeteries
4. ✓ PRIORITY | Woodland and forest - Other broadleaved
5. ✓ PRIORITY | Individual trees - Rural tree
6. ✓ PRIORITY | Sparsely vegetated land - Inland rock
7.   SECONDARY | Grassland - Other lowland
8.   SECONDARY | Heathland and shrub - Mixed scrub
```

All priority groups receive allocation before any secondary groups, ensuring important habitats are mitigated first.
