# Fix for Optimizer Tie-Breaking: Proximity Preference

## Issue Summary
The optimizer was not always selecting the cheapest eligible trade for Net Gain units. When multiple options had the same price, the optimizer would select based on bank capacity rather than proximity, sometimes choosing more expensive far bank allocations over cheaper local options.

## Root Cause
The original tie-breaking logic only considered bank capacity, not proximity to the target site. This meant that when two options had the same price, a far bank with higher capacity would be selected over a local bank with lower capacity.

## Solution
Added proximity-based tie-breaking to ensure that when options have the same price, the optimizer prefers:
1. **Local** banks (same LPA or NCA)
2. **Adjacent** banks (neighboring LPA or NCA)
3. **Far** banks (all other locations)
4. Higher-capacity banks (as a final tie-breaker)

## Changes Made

### 1. Added TIER_PROXIMITY_RANK constant (app.py, line 54)
```python
TIER_PROXIMITY_RANK = {"local": 0, "adjacent": 1, "far": 2}
```
Defines numerical ranking where lower is better (closer).

### 2. Updated PuLP solver objective function (app.py, lines 2298-2331)

**For Stage A & C (minimize cost):**
- Primary: minimize cost (coefficient = 1.0)
- Secondary: prefer closer banks (coefficient = 1e-9)
- Tertiary: prefer higher-capacity banks (coefficient = -1e-14)

**For Stage B (minimize banks):**
- Primary: minimize number of banks (coefficient = 1.0)
- Secondary: minimize cost (coefficient = 1e-9)
- Tertiary: prefer closer banks (coefficient = 1e-12)
- Final: prefer higher-capacity banks (coefficient = -1e-17)

The epsilon values are carefully chosen to ensure proper hierarchy:
- Each level dominates the next by at least 100x
- Proximity dominates capacity even with large capacity differences (100,000+ units)

### 3. Updated greedy fallback sorting (app.py, lines 2438-2447)
```python
cand_idx = sorted(
    [i for i in range(len(options)) if options[i]["demand_idx"] == di],
    key=lambda i: (
        options[i]["unit_price"],
        TIER_PROXIMITY_RANK.get(options[i].get("tier", "far"), 2),
        -sum(stock_caps.get(sid, 0.0) for sid in options[i]["stock_use"].keys())
    )
)
```
Multi-level sort key ensures the cheapest, closest, highest-capacity option is selected first.

## Testing
Created comprehensive tests to verify:
- ✓ TIER_PROXIMITY_RANK is correctly ordered
- ✓ Greedy sorting selects local option first when prices are equal
- ✓ Cheaper options are selected regardless of proximity
- ✓ PuLP epsilon coefficients maintain proper hierarchy
- ✓ Proximity dominates capacity in tie-breaking

All tests pass successfully.

## Expected Behavior
After this fix, the optimizer will:
1. Always select the cheapest legal option for each demand row
2. When prices are equal, prefer local banks over adjacent/far banks
3. When prices and proximity are equal, prefer banks with higher capacity
4. Respect the constraint of using at most two banks per quote

## Impact
- ✅ Optimizer now correctly prioritizes proximity when prices are equal
- ✅ Cheaper local options will be selected over more expensive far options
- ✅ Tie-breaking is deterministic and predictable
- ✅ No impact on non-tied scenarios (different prices)
- ✅ Maintains compatibility with existing allocation logic

## Files Modified
- `app.py` - Added proximity-based tie-breaking to PuLP solver and greedy fallback
