# Watercourse Trading Rules and SRM Implementation

## Overview

This document describes the implementation of watercourse trading rules and Spatial Risk Multiplier (SRM) requirements for the BNG Optimiser.

## Trading Rules for Watercourses

Watercourse habitats follow strict trading rules based on distinctiveness:

### Very High Distinctiveness
- **Rule**: Not eligible for normal trading
- **Action**: Bespoke compensation required
- **Implementation**: `can_offset_watercourse()` returns `False` for any Very High deficit
- **Example**: Priority habitat watercourses cannot be offset by any surplus

### High Distinctiveness
- **Rule**: Same habitat required (like-for-like)
- **Action**: Only same watercourse habitat type with same or higher distinctiveness
- **Implementation**: Checks habitat normalization and requires `surplus_distinctiveness >= deficit_distinctiveness`
- **Example**: "Other rivers and streams" (High) can be offset by "Other rivers and streams" (High or Very High), but not by "Canals" or lower distinctiveness

### Medium Distinctiveness
- **Rule**: Same habitat required (like-for-like)
- **Action**: Only same watercourse habitat type with same or higher distinctiveness
- **Implementation**: Same as High - checks habitat normalization and distinctiveness level
- **Example**: "Ditches" (Medium) can be offset by "Ditches" (Medium, High, or Very High), but not by "Canals" or "Culvert"

### Low Distinctiveness
- **Rule**: Must trade to better distinctiveness habitat
- **Action**: Can only be offset by higher distinctiveness of the same habitat type
- **Implementation**: Requires `surplus_distinctiveness > deficit_distinctiveness` (strictly greater) and same habitat
- **Example**: "Culvert" (Low) can be offset by "Culvert" (Medium, High, Very High), but NOT by "Culvert" (Low)

## Habitat Normalization

Watercourse habitat names are normalized to handle variations:

```python
"Other rivers and streams" → "rivers_streams"
"rivers and streams" → "rivers_streams"
"Canals" → "canals"
"Ditches" → "ditches"
"Culvert" → "culvert"
"Priority habitat" → "priority_habitat"
```

This ensures consistent matching across different metric formats.

## Spatial Risk Multiplier (SRM)

### SRM Rules for Watercourses

Unlike area habitats and hedgerows which use LPA/NCA based tiering, watercourses use catchment-based SRM:

1. **Same Waterbody Catchment**
   - SRM = 1.0 (no uplift)
   - No additional units required
   - Ideal scenario for offsetting

2. **Same Operational Catchment (Different Waterbody)**
   - SRM = 0.75
   - Effective uplift = 4/3 (buyer needs 1.33× units)
   - Acceptable but requires more units

3. **Outside Operational Catchment**
   - SRM = 0.5
   - Effective uplift = 2× (buyer needs 2× units)
   - Last resort option

### Data Sources

Waterbody and operational catchment boundaries are obtained from:

**Environment Agency Water Framework Directive (WFD) Datasets:**
- WFD River Waterbody Catchments: Individual waterbody boundaries
  - URL: `https://environment.data.gov.uk/spatialdata/water-framework-directive-river-waterbody-catchments-cycle-2/wfs`
  
- WFD River Operational Catchments: Larger operational catchment boundaries
  - URL: `https://environment.data.gov.uk/spatialdata/water-framework-directive-river-operational-catchments-cycle-2/wfs`

### Combined Rule Application

**IMPORTANT**: SRM and trading rules work TOGETHER:

```
Valid Offset = Trading Rules Satisfied AND SRM Requirements Met
```

Examples:

1. ✅ **Valid**: High "Rivers and streams" deficit offset by High "Rivers and streams" surplus in same waterbody
   - Trading rule: ✓ (same habitat, same distinctiveness)
   - SRM: ✓ (1.0 - same waterbody)

2. ✅ **Valid**: Medium "Ditches" deficit offset by High "Ditches" surplus in same operational catchment
   - Trading rule: ✓ (same habitat, higher distinctiveness allowed for Medium)
   - SRM: ⚠️ (0.75 - different waterbody but same op catchment, needs 4/3× units)

3. ❌ **Invalid**: High "Rivers and streams" deficit offset by High "Canals" surplus in same waterbody
   - Trading rule: ✗ (different habitat - not allowed for High)
   - SRM: ✓ (1.0 - same waterbody)
   - Result: **Not allowed** (trading rule fails)

4. ❌ **Invalid**: Low "Culvert" deficit offset by Low "Culvert" surplus in same waterbody
   - Trading rule: ✗ (Low cannot offset Low)
   - SRM: ✓ (1.0 - same waterbody)
   - Result: **Not allowed** (trading rule fails)

## Implementation Details

### Files Modified

1. **metric_reader.py**
   - Added `can_offset_watercourse()` function for trading rule validation
   - Added `apply_watercourse_offsets()` function to apply trading rules
   - Updated `parse_metric_requirements()` to use full watercourse trading logic
   - Added habitat normalization for watercourse types

2. **app.py**
   - Added waterbody and operational catchment URL constants
   - Documentation for watercourse SRM requirements
   - (Future: Integration of catchment queries for SRM calculation)

### Testing

Comprehensive test coverage in `test_watercourse_trading_rules.py`:

- ✅ Very High distinctiveness cannot be offset (bespoke compensation)
- ✅ High distinctiveness requires like-for-like same habitat
- ✅ Medium distinctiveness requires like-for-like same habitat
- ✅ Low distinctiveness must trade up (cannot offset Low with Low)
- ✅ Habitat normalization handles name variations
- ✅ Integration tests with full metric parsing

## Usage Example

```python
from metric_reader import parse_metric_requirements

# Parse metric file with watercourse trading summary
requirements = parse_metric_requirements(uploaded_file)

# Access watercourse requirements (after trading rules applied)
watercourse_req = requirements['watercourses']

# Requirements dataframe contains:
# - habitat: Watercourse habitat name
# - units: Units needed (after on-site offsets with trading rules)
```

## Future Enhancements

1. **Catchment Query Integration**
   - Implement WFS queries to Environment Agency datasets
   - Cache catchment boundaries for performance
   - Add catchment name extraction and comparison

2. **SRM Application in Optimizer**
   - Extend optimizer to consider catchment proximity for watercourses
   - Apply appropriate SRM multipliers during allocation
   - Display catchment information in quote results

3. **Bank Catchment Data**
   - Store waterbody/operational catchment for each bank
   - Enable automatic SRM calculation during optimization
   - Add catchment visualization to maps

## References

- DEFRA Biodiversity Metric 4.0 User Guide
- Environment Agency Water Framework Directive Datasets
- Trading Rules Summary from BNG Metric "Trading Summary WaterCs" tab
