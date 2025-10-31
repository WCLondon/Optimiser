# Medium Distinctiveness Habitat Hierarchy

## Overview

The metric reader now implements a priority hierarchy for Medium distinctiveness habitats when processing on-site offsets. This ensures that certain Medium broad groups, which are more important to mitigate first (due to higher cost or difficulty to replace), are processed before others.

## Implementation Details

### Priority Groups (Processed First)

The following Medium distinctiveness broad groups are given priority during on-site offset allocation:

1. **Cropland**
2. **Lakes**
3. **Sparsely vegetated land**
4. **Urban**
5. **Individual trees**
6. **Woodland and forest**
7. **Intertidal sediment**
8. **Intertidal hard structures**

### Secondary Groups (Processed After Priority)

After priority groups are fully processed, remaining Medium surpluses are used to mitigate for:

1. **Grassland**
2. **Heathland and shrub**

### Unchanged Behavior

- **Low distinctiveness**: Processing order unchanged
- **High distinctiveness**: Processing order unchanged
- **Very High distinctiveness**: Processing order unchanged
- **Offset eligibility rules**: Not changed - only the order of processing Medium deficits has been modified

### Processing Order

The complete processing order for deficits is now:

1. Very High distinctiveness (all broad groups)
2. High distinctiveness (all broad groups)
3. Medium distinctiveness - **Priority groups** (Cropland, Lakes, etc.)
4. Medium distinctiveness - **Secondary groups** (Grassland, Heathland)
5. Low distinctiveness (all broad groups)

Within each distinctiveness level, deficits maintain their original order from the input data.

## Flow Log

Each allocation in the on-site offset process is now tracked in a flow log with the following structure:

```python
{
    "deficit_habitat": str,              # Name of habitat with deficit
    "deficit_broad_group": str,          # Broad group of deficit habitat
    "deficit_distinctiveness": str,      # Distinctiveness band of deficit
    "surplus_habitat": str,              # Name of habitat providing surplus
    "surplus_broad_group": str,          # Broad group of surplus habitat
    "surplus_distinctiveness": str,      # Distinctiveness band of surplus
    "units_allocated": float,            # Number of units allocated
    "priority_medium": bool              # True if deficit is in priority Medium group
}
```

The `priority_medium` flag indicates whether the allocation was for a priority Medium group, making it easy to track and verify the hierarchy implementation.

## Example

Given the following Medium distinctiveness deficits and surpluses:

**Deficits:**
- Grassland (secondary group): -5.0 units
- Cropland (priority group): -4.0 units
- Heathland (secondary group): -3.0 units
- Woodland (priority group): -6.0 units

**Surpluses:**
- High distinctiveness: 20.0 units

**Processing Order:**
1. Cropland deficit (-4.0) ← allocated 4.0 units (priority_medium=True)
2. Woodland deficit (-6.0) ← allocated 6.0 units (priority_medium=True)
3. Grassland deficit (-5.0) ← allocated 5.0 units (priority_medium=False)
4. Heathland deficit (-3.0) ← allocated 3.0 units (priority_medium=False)

If surplus runs out before all deficits are covered, priority groups will have received allocation first.

## Testing

Run the comprehensive test suite:

```bash
python test_medium_hierarchy.py
```

This tests:
- Priority Medium groups are processed before secondary Medium groups
- `priority_medium` flag is correctly set in flow log
- Other distinctiveness levels (Low, High, Very High) are unaffected
- Full end-to-end parsing with realistic Excel file
