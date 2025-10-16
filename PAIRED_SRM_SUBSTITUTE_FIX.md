# Paired SRM Offset Fix - Bug Resolution (CORRECTED)

## Issue Summary
When allocating demand for 'Individual trees - Urban Tree' to an adjacent bank, the optimiser correctly identified a cheaper substitute trade for 'Traditional orchard' in the adjacent bank. However, although a legal pairing with 'Mixed Scrub' (also in stock and cheaper) was possible, this pairing was not selected. The pairing would have reduced the overall SRM-adjusted price for that line item.

## Important Note
This document was updated to correct a fundamental misunderstanding about how paired allocations should work. The original PAIRED_ALLOCATION_FIX.md had the wrong formula. The correct logic uses weighted averages, not equal contributions from both components.

## Root Cause
The bug had three components:

1. **Incorrect price lookup**: At line 2175 (now 2178), the code was looking up the price for the **demand habitat** (`dem_hab`, e.g., "Individual trees - Urban Tree") instead of the **supply habitat** (`d_stock["habitat_name"]`, e.g., "Traditional orchard"). When a substitute trade was used, the demand habitat may not have a price at that bank/tier, causing the lookup to fail (`pi_demand = None`) and paired options to not be created.

2. **Incorrect companion filtering**: At line 2147 (now 2156), companion candidates were filtered to exclude the demand habitat (`!= dem_hab`) instead of the supply habitat. This meant that when a substitute was used, the supply habitat itself could be selected as its own companion, which doesn't make sense.

3. **Incorrect price filtering**: At line 2236, paired options were only created if `blended_price < price_demand`. This comparison was flawed and prevented valid paired options from being created, even when they would be cheaper than single allocations once the SRM penalty was properly accounted for.

## The Fix

### Change 1: Move companion filtering inside the loop
**Before** (line 2147):
```python
companion_candidates = stock_full[
    (stock_full["BANK_KEY"] == bk) &
    (stock_full["habitat_name"] != dem_hab) &  # Wrong: excludes demand, not supply
    ...
]
```

**After** (line 2156):
```python
# Get supply habitat name (may be different from demand if it's a substitute)
supply_hab = sstr(d_stock["habitat_name"])

# Get "companion" candidates: any area habitat with positive stock
# excluding the supply habitat itself to avoid self-pairing
companion_candidates = stock_full[
    (stock_full["BANK_KEY"] == bk) &
    (stock_full["habitat_name"] != supply_hab) &  # Correct: excludes supply habitat
    ...
]
```

### Change 2: Use supply habitat for price lookup
**Before** (line 2175):
```python
# Get demand habitat price at this tier
pi_demand = find_price_for_supply(bk, dem_hab, target_tier, d_broader, d_dist)
```

**After** (line 2178):
```python
# Get supply habitat price at this tier (not demand habitat - use actual supply)
pi_demand = find_price_for_supply(bk, supply_hab, target_tier, d_broader, d_dist)
```

### Change 3: Remove incorrect price filtering
**Before** (line 2236):
```python
# Only add paired option if it's cheaper than normal allocation
# (to avoid creating unnecessary options)
if blended_price < price_demand:
    options.append({
        "type": "paired",
        ...
    })
```

**After** (line 2233):
```python
# Always add paired option and let optimizer choose the best allocation
options.append({
    "type": "paired",
    ...
})
```

This change ensures paired options are always created when a valid companion exists, allowing the optimizer's linear programming solver to evaluate all options and select the truly cheapest allocation.

### Change 4: Fix blended price calculation (CRITICAL CORRECTION)
**Incorrect formula** (from PAIRED_ALLOCATION_FIX.md):
```python
# Adjacent
blended_price = (price_demand + price_companion) / srm  # WRONG!
stock_use_demand = 1.0 / srm  # = 0.75
stock_use_companion = 1.0 / srm  # = 0.75
```

**Correct formula** (weighted average as originally intended):
```python
# Adjacent: 3/4 main + 1/4 companion
stock_use_demand = 3/4
stock_use_companion = 1/4
blended_price = 0.75 * price_demand + 0.25 * price_companion

# Far: 1/2 main + 1/2 companion
stock_use_demand = 1/2
stock_use_companion = 1/2
blended_price = 0.5 * price_demand + 0.5 * price_companion
```

**Explanation**: SRM is already baked into the pricing matrix. For adjacent tier (SRM 4/3), we use 3/4 of the main component and 1/4 of the cheapest companion to create a weighted average price. This is NOT equal contributions from both components.

### Change 5: Fix split_paired_rows to use stock_use ratios
**Incorrect logic** (from PAIRED_ALLOCATION_FIX.md):
```python
# Each component gets the full raw requirement
raw_units_per_component = units_total / srm
rr["units_supplied"] = raw_units_per_component
```

**Correct logic**:
```python
# Use stock_use ratio to determine units for this component
stock_use = float(part.get("stock_use", 0.5))
rr["units_supplied"] = units_total * stock_use
```

This ensures the split reflects the weighted contribution of each component (3/4 and 1/4 for adjacent, 1/2 and 1/2 for far).

## Impact

### What's Fixed
✅ Paired options are now correctly created when substitute trades are used at adjacent/far tiers
✅ Companion habitats are properly excluded from being paired with themselves
✅ Price lookups use the actual supply habitat, ensuring valid prices are found
✅ The optimiser can now select cheaper paired allocations that were previously missed
✅ **CRITICAL**: Blended price now uses correct weighted average formula
✅ **CRITICAL**: Units are split according to actual contribution ratios (3/4 and 1/4, not equal)

### Example Scenario
- **Demand**: 'Individual trees - Urban Tree' (0.07 units at adjacent tier)
- **Bank A** has:
  - 'Traditional orchard' (substitute, £32,800/unit)
  - 'Mixed Scrub' (companion, £20,000/unit estimated)
  
**Before fix**:
- Only 'Traditional orchard' option created (no paired option)
- Cost: £32,800 × 0.07 = £2,296

**After fix (CORRECTED)**:
- Both single and paired options created:
  1. Single: 'Traditional orchard' at £32,800/unit → £2,296
  2. Paired: 'Traditional orchard' (0.0525 units) + 'Mixed Scrub' (0.0175 units)
- Blended price = 0.75 × £32,800 + 0.25 × £20,000 = £29,600 per effective unit
- Total paired cost: 0.0525 × £32,800 + 0.0175 × £20,000 = £2,072
- Optimizer selects the cheaper paired option, saving £224

### What's Unchanged
✅ Non-substitute trades continue to work as before
✅ Local tier allocations are unaffected
✅ Single-habitat options are still created
✅ Existing test suite passes

## Testing
- ✅ All existing tests pass (test_repo_validation.py)
- ✅ New test validates the fix (test_paired_allocation_fix.py)
- ✅ Python syntax verified with py_compile
- ⏳ Manual testing with real database and data (requires setup)

## Files Modified
- `app.py`: Lines 2145-2178 (paired allocation logic in `prepare_options` function)
- `test_paired_allocation_fix.py`: New comprehensive test file

## References
- Original issue: "Bug: Paired SRM offset not selected despite available, cheaper companion habitat in adjacent bank"
- PAIRED_ALLOCATION_FIX.md: Documentation of intended pairing behavior
- GitHub PR: copilot/fix-paired-srm-selection-bug
