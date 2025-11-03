# Rounding and Minimum Unit Delivery Fix - Documentation

## Latest Update: 2 Decimal Places & Minimum 0.01 Units

### New Requirements Implemented

1. **Minimum Unit Delivery**: 0.01 units
   - Cannot deliver anything less than 0.01 units
   - Enforced as a constraint in the optimizer
   
2. **2 Decimal Places for All Calculations**
   - Changed from 3 decimal places to 2 decimal places
   - Consistent formatting throughout the application

---

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
# Units: 0.12          (2 decimals - standard format)
Price Per Unit: £22,000
Offset Cost: £2,725    (USES UPSTREAM: rounds £2,725.14 to £2,725 - CORRECT!)
```

**Solution:** The table uses the upstream cost value directly and displays all values at 2 decimal places.

---

## How the Formatting Works

The `format_units_dynamic()` and `format_units_total()` functions:
1. Format all values to exactly 2 decimal places
2. Maintain consistency across the application

### Examples:

| Original Value | Displayed As | Notes |
|----------------|--------------|-------|
| 0.12387        | 0.12         | Rounded to 2 decimals |
| 0.12           | 0.12         | Already 2 decimals |
| 1.5            | 1.50         | 2 decimals |
| 0.083          | 0.08         | Rounded to 2 decimals |
| 0.123456       | 0.12         | Rounded to 2 decimals |
| 2.345678       | 2.35         | Rounded to 2 decimals |

---

## Minimum Unit Delivery Constraint

### Implementation

The optimizer now enforces a minimum delivery of 0.01 units:

```python
MIN_UNIT_DELIVERY = 0.01

# In the optimization problem:
# If option i is selected (z[i] = 1), then x[i] must be at least 0.01
prob += x[i] >= MIN_UNIT_DELIVERY * z[i]
```

### Examples:

| Demand Units | Result | Notes |
|--------------|--------|-------|
| 0.01         | ✓ Valid | Exactly at minimum |
| 0.02         | ✓ Valid | Above minimum |
| 1.5          | ✓ Valid | Normal case |
| 0.005        | ✗ Invalid | Below minimum - cannot be delivered |

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

### 2. Fixed Unit Formatting (2 decimals)
**Before:**
```python
"# Units": format_units_dynamic(supply_units)  # Variable decimals (2-5)
```

**After:**
```python
"# Units": format_units_dynamic(supply_units)  # Fixed 2 decimals
```

### 3. Added Minimum Unit Constraint
**New:**
```python
MIN_UNIT_DELIVERY = 0.01
prob += x[i] >= MIN_UNIT_DELIVERY * z[i]
```

### 4. Applied Throughout
Updated in:
- Optimizer allocations
- Manual hedgerow entries
- Manual watercourse entries  
- Manual area habitat entries (paired and simple)
- Bundled Low + Net Gain rows
- Total rows in HTML table
- All formatting functions

---

## Key Principles

✅ **Keep all maths from the program exactly as-is**
- Use upstream `price_per_unit` directly
- Use upstream `cost` directly

✅ **Stop recomputing Price Per Unit**
- Don't divide total cost by units
- Use the value from pricing engine

✅ **Consistent 2 decimal formatting**
- All units displayed at 2 decimals
- All calculations at 2 decimals

✅ **Enforce minimum unit delivery**
- Cannot deliver less than 0.01 units
- Constraint enforced in optimizer

✅ **Round only at presentation layer**
- Price per unit: Round to nearest £50 for display
- Offset cost: Round to nearest £1 for display
- Units: Show exactly 2 decimals

---

## Test Results

All tests passing ✅

```
✓ format_units_dynamic(0.12387) = 0.12
✓ format_units_dynamic(0.083) = 0.08
✓ format_units_total(0.349) = 0.35
✓ Issue example test PASSED
✓ No recalculation test PASSED
✓ Minimum unit constraint test PASSED
```

The fix ensures that:
1. Unit quantities are displayed at exactly 2 decimal places
2. Price per unit comes from upstream calculations
3. Offset costs are never recalculated from rounded values
4. Only display formatting is rounded, not the underlying math
5. Minimum delivery of 0.01 units is enforced in the optimizer
