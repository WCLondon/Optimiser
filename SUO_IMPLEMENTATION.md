# Surplus Uplift Offset (SUO) - Implementation Summary

## Overview

The Surplus Uplift Offset (SUO) feature provides a **cost discount** to users who have created surplus habitat on their development site. This discount is applied **after optimization** based on:
- Eligible surplus from the BNG metric file (Medium+ distinctiveness only)
- The actual banks and SRMs selected by the optimizer
- A 50% "headroom" safety factor

## How It Works

### Step 1: Metric Upload & Import
```
User uploads BNG metric file
↓
Metric reader extracts:
- ALL deficits (imported to demand table as before)
- Surplus habitats after on-site trading
↓
Surplus stored in session state for SUO calculation
```

**Key Point**: Metric import is **unchanged** - all deficits are imported normally.

### Step 2: Optimization (Normal Flow)
```
User runs optimizer
↓
Optimizer allocates units from banks based on:
- Trading rules
- Prices
- Stock availability
- Bank limit (max 2 banks)
↓
Allocation complete with specific banks and tiers selected
```

**Key Point**: Optimization runs **normally** - SUO doesn't affect requirement allocation.

### Step 3: SUO Discount Calculation (After Optimization)
```
Check: Is there eligible surplus from metric?
↓
Filter surplus to Medium+ distinctiveness only
(Low distinctiveness excluded - same baseline as original land)
↓
Apply 50% headroom: usable = eligible × 0.5
↓
Get actual banks used and their SRMs:
- Extract bank IDs and tiers from allocation
- Map tiers to SRMs (local=1.0, adjacent=1.33, far=2.0)
- Calculate weighted average SRM
↓
Calculate effective offset: effective = usable / avg_SRM
↓
Calculate discount: discount% = effective / total_units_allocated
↓
Apply discount to allocation costs only
(Manual additions and admin fee NOT discounted)
```

### Step 4: Display & User Choice
```
Show SUO section with:
- Checkbox to enable/disable discount (default: enabled)
- Metrics: eligible surplus, usable surplus, effective offset, discount %
- Cost comparison: before vs after discount
- Total savings in £
```

## Example Calculation

### Scenario
- **Metric file shows**: 60 units of Medium distinctiveness surplus
- **Optimizer allocates**: 100 units total
  - Bank A (local tier): 70 units @ SRM 1.0
  - Bank B (adjacent tier): 30 units @ SRM 1.33

### Calculation Steps

1. **Eligible surplus**: 60 units (Medium, so eligible)

2. **Usable surplus** (50% headroom):
   ```
   60 × 0.5 = 30 units
   ```

3. **Weighted average SRM** from allocated banks:
   ```
   (70 units × 1.0 + 30 units × 1.33) / 100 units = 1.099
   ```

4. **Effective offset** (adjusted for SRM):
   ```
   30 units / 1.099 = 27.3 units
   ```

5. **Discount percentage**:
   ```
   27.3 / 100 = 27.3%
   ```

6. **Cost savings**:
   ```
   If allocation costs £10,000:
   Discount: £10,000 × 27.3% = £2,730 savings
   New cost: £7,270
   ```

## Why This Design?

### Problem with Previous Approach
❌ Tried to reduce requirements BEFORE optimization
❌ Didn't know which banks would be selected
❌ Assumed SRM=1.0 (incorrect for purchased credits)
❌ Complex allocation tracking

### Benefits of New Approach
✅ Correct SRM handling - uses actual banks from optimization
✅ Simple cost discount - easy to understand and verify
✅ Metric import unchanged - all deficits imported
✅ Clear savings displayed in £
✅ Optional feature - user can toggle on/off

## Distinctiveness Filtering

### Why Only Medium+ ?

**Low distinctiveness surplus is excluded** because:
- Low distinctiveness = same ecological value as baseline habitat
- Cannot provide genuine ecological uplift
- Would be "offsetting" with equivalent habitat (circular logic)

**Medium, High, Very High are included** because:
- Represent genuine ecological improvement over baseline
- Provide real additional biodiversity value
- Can legitimately offset mitigation requirements

### Example
```
Metric shows:
- 30 units Low distinctiveness grassland → EXCLUDED
- 40 units Medium distinctiveness heathland → INCLUDED (eligible)
- 20 units High distinctiveness woodland → INCLUDED (eligible)

Eligible surplus = 40 + 20 = 60 units
```

## UI Components

### Metrics Display
```
┌─────────────────────────────────────────────────────────┐
│ ✅ Apply Surplus Uplift Offset Discount [checked]      │
│                                                          │
│ ✅ SUO Discount Applied: 27.3% cost reduction          │
│                                                          │
│  Eligible    Usable      Effective     Discount        │
│  Surplus     (50%)       Offset        Applied         │
│  ─────────────────────────────────────────────────     │
│  60.0 units  30.0 units  27.3 units    27.3%          │
└─────────────────────────────────────────────────────────┘
```

### Cost Comparison Table
```
┌───────────────────────────────────────────────────────┐
│ Cost Item              Before SUO    After SUO  Savings│
├───────────────────────────────────────────────────────┤
│ Allocation Cost        £10,000.00   £7,270.00  £2,730 │
│ Manual Additions       £500.00      £500.00    £0     │
│ Admin Fee              £750.00      £750.00    £0     │
│ TOTAL                  £11,250.00   £8,520.00  £2,730 │
└───────────────────────────────────────────────────────┘

Total savings: £2,730 (27.3% discount on allocation costs)
```

## Configuration

All SUO parameters are in `compute_suo_discount()`:

```python
HEADROOM_FRACTION = 0.5              # Use 50% of eligible surplus
MIN_DISTINCTIVENESS = "Medium"        # Minimum level (excludes Low)
DISTINCTIVENESS_ORDER = {             # Hierarchy
    "Very Low": 0,
    "Low": 1,
    "Medium": 2,
    "High": 3,
    "Very High": 4
}
```

## Technical Notes

### SRM Handling
- SRM values come from the `SRM` reference table
- Maps tier → multiplier (local=1.0, adjacent=1.33, far=2.0)
- Weighted average calculated based on units allocated per bank/tier
- More units from lower-SRM banks = higher discount

### Discount Application
- Applied only to **allocation costs** from optimizer
- **NOT applied to**: manual additions, admin fee
- User can toggle on/off with checkbox
- Default: enabled (checkbox checked)

### Edge Cases Handled
- No surplus in metric → SUO not shown
- Only Low distinctiveness surplus → SUO not applicable
- Zero allocation → discount = 0%
- Missing SRM data → defaults to 1.0
- Removed allocation rows → excluded from calculation

## Testing

### Test Coverage
1. **`test_suo_discount.py`**: Verifies discount calculation with weighted SRMs
2. **`test_metric_reader.py`**: Confirms metric import unchanged
3. **Manual testing**: Required with actual metric files and UI

### Test Scenarios
- ✅ Multiple banks with different SRMs
- ✅ Mix of distinctiveness levels (filters correctly)
- ✅ 50% headroom applied
- ✅ Discount percentage calculation
- ✅ Cost savings computed correctly

## Future Enhancements

Potential improvements for v2:
- [ ] Per-line SRM if banks offer different tiers for different habitats
- [ ] Configurable headroom percentage (currently fixed at 50%)
- [ ] Group compatibility checking (currently allows cross-group)
- [ ] Save SUO details with quote in database
- [ ] Include SUO in email/PDF reports
