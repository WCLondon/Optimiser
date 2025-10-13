# Fix for Paired Allocation Accounting

## Issue Summary
When paired habitat allocations (e.g., Traditional orchards + Mixed scrub) were used with Spatial Risk Multipliers (SRM), the system incorrectly split the requirement using stock_use ratios before applying the SRM multiplier. This resulted in under-allocation where each component only delivered half the required effective units.

## Root Cause
The bug was in the `split_paired_rows` function which:
1. Took the effective requirement (e.g., 0.14 units)
2. Split it by stock_use ratio (e.g., 0.5 each for far tier)  
3. Divided by SRM (e.g., ÷2 for far tier)
4. Result: each component got 0.14 × 0.5 ÷ 2 = 0.035 raw → 0.07 effective (WRONG)

The expected behavior is:
1. Each component independently satisfies the full effective requirement
2. Result: each component gets 0.14 ÷ 2 = 0.07 raw → 0.14 effective (CORRECT)

## Changes Made

### 1. Fixed `split_paired_rows` function (app.py, lines 2351-2365)
**Old logic:**
```python
rr["units_supplied"] = units_total * stock_use_ratio / srm
```

**New logic:**
```python
raw_units_per_component = units_total / srm
rr["units_supplied"] = raw_units_per_component
```

Each component now receives the full raw requirement (effective / SRM), ignoring stock_use split.

### 2. Updated blended price calculation (app.py, lines 1432-1448)
**Old logic:**
- Far: `blended_price = 0.5 * price_o + 0.5 * price_other`
- Adjacent: `blended_price = (1.0 * price_o + 1/3 * price_other) / (4/3)`

**New logic:**
```python
blended_price = (price_o + price_other) / srm
```

This reflects the new semantics where each component delivers the full requirement.

### 3. Updated stock_use coefficients (app.py, lines 1440-1448)
**Old logic:**
- Far: orchard=0.5, scrub=0.5
- Adjacent: orchard=1.0, scrub=1/3

**New logic:**
```python
stock_use_per_component = 1.0 / srm
```

- Far (SRM=2): each component uses 0.5 per effective unit
- Adjacent (SRM=4/3): each component uses 0.75 per effective unit

## Verification

### Test Case from Issue (Far Tier)
**Input:** R = 0.14, SRM = far (×2), Traditional orchards + Mixed scrub

**Output (OLD - WRONG):**
- Orchards: raw 0.035 → effective 0.07, cost = £1,428
- Mixed scrub: raw 0.065 → effective 0.13, cost = £1,872

**Output (NEW - CORRECT):**
- Orchards: raw 0.07 → effective 0.14, cost = £2,856
- Mixed scrub: raw 0.07 → effective 0.14, cost = £2,016
- Total: £4,872 (matches optimizer cost)

### Test Case: Adjacent Tier
**Input:** R = 0.14, SRM = adjacent (×4/3)

**Output:**
- Orchards: raw 0.105 → effective 0.14, cost = £4,284
- Mixed scrub: raw 0.105 → effective 0.14, cost = £3,024
- Total: £7,308 (matches optimizer cost)

### Non-Paired Behavior
Non-paired (normal) allocations remain unchanged and work as before.

## Impact

### Positive Changes
✅ Each paired component now correctly delivers the full effective requirement
✅ Cost calculations remain consistent between optimizer and display
✅ Stock consumption accurately reflects actual raw units used
✅ Non-paired allocations unaffected

### Breaking Changes
⚠️ Paired allocation costs will INCREASE compared to the old (buggy) behavior
- This is correct because we're now properly accounting for full delivery per component
- The old behavior was under-costing the paired allocations

## Files Modified
- `app.py` - Fixed `split_paired_rows` and updated paired option creation
- `.gitignore` - Added to exclude Python cache files
