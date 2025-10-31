# Rounding Fix - Visual Examples

## Issue Example: The Problem

### Before the Fix (WRONG ❌)
When the optimiser calculates: **0.12387 units @ £22,000 per unit = £2,725.14**

The table would display:
```
# Units: 0.12          (hardcoded to 2 decimals - loses precision!)
Price Per Unit: £22,000
Offset Cost: £2,640    (RECALCULATED: £22,000 × 0.12 = £2,640 - WRONG!)
```

**Problem:** The table recalculated the cost using rounded units, producing an incorrect value.

---

### After the Fix (CORRECT ✅)
When the optimiser calculates: **0.12387 units @ £22,000 per unit = £2,725.14**

The table now displays:
```
# Units: 0.124         (dynamic formatting - shows 3 sig figs to preserve accuracy)
Price Per Unit: £22,000
Offset Cost: £2,725    (USES UPSTREAM: rounds £2,725.14 to £2,725 - CORRECT!)
```

**Solution:** The table uses the upstream cost value directly and displays enough significant figures on units.

---

## How the Dynamic Formatting Works

The `format_units_dynamic()` function:
1. Tests increasing decimal precision (2, 3, 4, 5 decimals)
2. Stops when the formatted value is within 0.5% of the original
3. Removes trailing zeros (but keeps minimum 2 decimals)

### Examples:

| Original Value | Displayed As | Decimals Used | Notes |
|----------------|--------------|---------------|-------|
| 0.12387        | 0.124        | 3             | Issue example - needs precision |
| 0.12           | 0.12         | 2             | Already 2 decimals |
| 1.5            | 1.50         | 2             | Minimum 2 decimals |
| 0.080          | 0.08         | 2             | Trailing zero removed |
| 0.083          | 0.083        | 3             | Cannot round - needs 3 |
| 0.123456       | 0.123        | 3             | 0.5% accuracy sufficient |
| 2.345678       | 2.346        | 3             | 0.5% accuracy sufficient |

---

## What Changed

### 1. Stopped Recalculating Costs
**Before:**
```python
unit_price = round_to_50(unit_price)
offset_cost = unit_price * supply_units  # ❌ RECALCULATED
```

**After:**
```python
unit_price_display = round_to_50(unit_price)  # For display only
offset_cost_display = round(offset_cost)       # Use upstream, round for display
```

### 2. Dynamic Unit Formatting
**Before:**
```python
"# Units": f"{supply_units:.2f}"  # ❌ Hardcoded 2 decimals
```

**After:**
```python
"# Units": format_units_dynamic(supply_units)  # ✅ Dynamic precision
```

### 3. Applied Throughout
Updated in:
- Optimizer allocations
- Manual hedgerow entries
- Manual watercourse entries  
- Manual area habitat entries (paired and simple)
- Bundled Low + Net Gain rows
- Total rows in HTML table

---

## Key Principles

✅ **Keep all maths from the program exactly as-is**
- Use upstream `price_per_unit` directly
- Use upstream `cost` directly

✅ **Stop recomputing Price Per Unit**
- Don't divide total cost by units
- Use the value from pricing engine

✅ **Dynamically display enough significant figures**
- Show 2-5 decimals as needed
- Remove trailing zeros (but keep minimum 2)

✅ **Round only at presentation layer**
- Price per unit: Round to nearest £50 for display
- Offset cost: Round to nearest £1 for display
- Units: Show dynamic precision for accuracy

---

## Test Results

All tests passing ✅

```
✓ format_units_dynamic(0.12387) = 0.124
✓ format_units_dynamic(0.083) = 0.083
✓ Issue example test PASSED
✓ No recalculation test PASSED
```

The fix ensures that:
1. Unit quantities show enough precision to reconcile with totals
2. Price per unit comes from upstream calculations
3. Offset costs are never recalculated from rounded values
4. Only display formatting is rounded, not the underlying math
