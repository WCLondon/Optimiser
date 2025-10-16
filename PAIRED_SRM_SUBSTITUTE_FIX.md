# Paired SRM Offset Fix - Bug Resolution

## Issue Summary
When allocating demand for 'Individual trees - Urban Tree' to an adjacent bank, the optimiser correctly identified a cheaper substitute trade for 'Traditional orchard' in the adjacent bank. However, although a legal pairing with 'Mixed Scrub' (also in stock and cheaper) was possible, this pairing was not selected. The pairing would have reduced the overall SRM-adjusted price for that line item.

## Root Cause
The bug had two components:

1. **Incorrect price lookup**: At line 2175 (now 2178), the code was looking up the price for the **demand habitat** (`dem_hab`, e.g., "Individual trees - Urban Tree") instead of the **supply habitat** (`d_stock["habitat_name"]`, e.g., "Traditional orchard"). When a substitute trade was used, the demand habitat may not have a price at that bank/tier, causing the price lookup to fail (`pi_demand = None`) and paired options to not be created.

2. **Incorrect companion filtering**: At line 2147 (now 2156), companion candidates were filtered to exclude the demand habitat (`!= dem_hab`) instead of the supply habitat. This meant that when a substitute was used, the supply habitat itself could be selected as its own companion, which doesn't make sense.

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

## Impact

### What's Fixed
✅ Paired options are now correctly created when substitute trades are used at adjacent/far tiers
✅ Companion habitats are properly excluded from being paired with themselves
✅ Price lookups use the actual supply habitat, ensuring valid prices are found
✅ The optimiser can now select cheaper paired allocations that were previously missed

### Example Scenario
- **Demand**: 'Individual trees - Urban Tree' (0.14 units)
- **Bank A** has:
  - 'Traditional orchard' (substitute, £40.80/unit at adjacent tier)
  - 'Mixed Scrub' (companion, £28.80/unit at adjacent tier)
  
**Before fix**:
- Only 'Traditional orchard' option created (no paired option)
- Cost: £40.80 × 0.14 = £5.71

**After fix**:
- Both single and paired options created:
  1. Single: 'Traditional orchard' at £40.80/unit
  2. Paired: 'Traditional orchard' + 'Mixed Scrub' at blended price
- Blended price = (£40.80 + £28.80) / (4/3) = £52.20 per effective unit
- Optimizer can choose the cheaper option

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
