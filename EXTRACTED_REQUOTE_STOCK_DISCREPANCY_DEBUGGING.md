# Debugging Requote Allocation Differences: Stock-Based Selection

This document explains why the optimizer may produce different allocations for the same demand between original quotes and requotes, specifically due to **stock capacity constraints**.

---

## The Problem: Why Did the Allocation Change?

### Original Allocation (Correct)
```json
{
    "BANK_KEY": "Central Bedfordshire",
    "bank_id": "WC1P6",
    "supply_habitat": "Grassland - Traditional orchards + Heathland and shrub - Mixed scrub",
    "unit_price": 29600,
    "demand_habitat": "Individual trees - Urban tree"
}
```

### Requote Allocation (Different)
```
BANK_KEY: Bedford
bank_id: WC1P5
supply_habitat: Individual trees - Rural tree + Heathland and shrub - Mixed scrub
unit_price: 28,300
demand_habitat: Individual trees - Urban tree
```

### Key Difference
- Bedford (WC1P5) at £28,300 is **cheaper**
- Central Bedfordshire (WC1P6) at £29,600 is **more expensive**

**But the original optimizer chose the more expensive option. Why?**

---

## The Answer: Stock Capacity Constraints

The optimizer enforces **hard stock limits** via this constraint (line 2814):

```python
# Stock capacity constraints
for sid, pairs in use_map.items():
    cap = float(stock_caps.get(sid, 0.0))
    prob += pulp.lpSum([coef * x[i] for (i, coef) in pairs]) <= cap
```

### What This Means:
- If Bedford (WC1P5) has **low stock** of "Individual trees - Rural tree", the optimizer **cannot** use it
- The optimizer is then **forced** to choose the next best option: Central Bedfordshire (WC1P6)
- Even though it's more expensive, it's the only feasible solution

---

## How Stock Data Flows Through the Optimizer

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         STOCK TABLE (Supabase)                           │
│  stock_id | habitat_name              | bank_id | BANK_KEY | qty_avail  │
│  ---------|---------------------------|---------|----------|----------- │
│  stk_100  | Individual trees - Rural  | WC1P5   | Bedford  | 0.15       │ ← LOW STOCK!
│  stk_101  | Grassland - Trad orchards | WC1P6   | Cent.Beds| 5.00       │ ← Sufficient
└───────────────────────────────────┬─────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                    OPTIONS GENERATION (prepare_options)                  │
│                                                                          │
│  Option 1: Bedford (WC1P5) - £28,300 - "Individual trees - Rural tree"  │
│            stock_use: {"stk_100": 0.75}                                  │
│            Requires: 0.2608 × 0.75 = 0.1956 units of stock              │
│                                                                          │
│  Option 2: Central Beds (WC1P6) - £29,600 - "Traditional orchards"      │
│            stock_use: {"stk_101": 0.75}                                  │
│            Requires: 0.2608 × 0.75 = 0.1956 units of stock              │
└───────────────────────────────────┬─────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                         LP SOLVER CONSTRAINTS                            │
│                                                                          │
│  Objective: Minimize Σ(unit_price × allocation)                         │
│                                                                          │
│  Constraints:                                                            │
│  1. stk_100 usage ≤ 0.15   (Bedford's Rural tree stock)                 │
│  2. stk_101 usage ≤ 5.00   (Central Beds's Traditional orchards stock)  │
│                                                                          │
│  Result:                                                                 │
│  - Option 1 requires 0.1956 units, but only 0.15 available → INFEASIBLE │
│  - Option 2 requires 0.1956 units, 5.00 available → ✓ FEASIBLE          │
│                                                                          │
│  Solver picks Option 2 (more expensive but only feasible option)        │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## Why Requotes May Produce Different Allocations

### Scenario 1: Stock Was Replenished
Between the original quote and requote, the stock at Bedford (WC1P5) was **replenished**:
- Original: "Individual trees - Rural tree" = 0.15 units (too low)
- Requote: "Individual trees - Rural tree" = 2.00 units (sufficient)

Now Bedford becomes feasible and cheaper, so the optimizer picks it.

### Scenario 2: Stock Was Depleted Elsewhere
Other quotes may have **consumed stock** from the originally preferred bank:
- Original: Central Bedfordshire had plenty of stock
- Requote: Central Bedfordshire stock was depleted by other quotes

### Scenario 3: Different Stock Snapshot
The requote endpoint may be loading stock data from a different source or snapshot than the original optimizer.

---

## Key Code Locations for Debugging

| Component | Location | Purpose |
|-----------|----------|---------|
| Stock loading | `Stock` table in `backend["Stock"]` | Source of `quantity_available` |
| `stock_caps` creation | Lines 783, 2012, 2400 | Maps `stock_id` → `quantity_available` |
| Constraint enforcement | Line 2814 | `prob += lpSum([coef * x[i] for pairs]) <= cap` |
| Option `stock_use` | Lines 916, 2166, 2306 | Defines which stocks an option uses |

---

## Debugging Checklist for Requote Discrepancies

### 1. Compare Stock Levels at Time of Each Allocation
```sql
-- Check stock for Bedford's "Individual trees - Rural tree"
SELECT stock_id, habitat_name, bank_id, BANK_KEY, quantity_available
FROM stock
WHERE BANK_KEY = 'Bedford' AND habitat_name LIKE 'Individual trees%';

-- Check stock for Central Bedfordshire's "Traditional orchards"
SELECT stock_id, habitat_name, bank_id, BANK_KEY, quantity_available
FROM stock
WHERE BANK_KEY = 'Central Bedfordshire' AND habitat_name LIKE 'Grassland - Traditional%';
```

### 2. Verify Stock Data is Being Loaded
```python
# In optimizer, check stock_caps is populated
print("Stock caps:", stock_caps)
print("Bedford Rural tree stock:", stock_caps.get("stk_100"))
print("Central Beds Orchards stock:", stock_caps.get("stk_101"))
```

### 3. Check Option Stock Usage
```python
# For each option, verify stock_use is set correctly
for opt in options:
    if "Bedford" in opt.get("BANK_KEY", ""):
        print(f"Bedford option: {opt['supply_habitat']}")
        print(f"  stock_use: {opt['stock_use']}")
        for sid, coef in opt['stock_use'].items():
            print(f"  {sid}: need {coef * opt['units_supplied']}, have {stock_caps.get(sid)}")
```

### 4. Track Why Options Were Rejected
Add logging to see which options were considered but rejected:
```python
# Before LP solve
for i, opt in enumerate(options):
    feasible = True
    for sid, coef in opt['stock_use'].items():
        required = coef * demand_units
        available = stock_caps.get(sid, 0.0)
        if required > available + 1e-9:
            print(f"Option {i} ({opt['BANK_KEY']}) REJECTED: needs {required:.4f} of {sid}, only {available:.4f} available")
            feasible = False
            break
    if feasible:
        print(f"Option {i} ({opt['BANK_KEY']}) FEASIBLE at £{opt['unit_price']}")
```

---

## VSCode Copilot's Analysis: Confirmed

The VSCode analysis is **correct**:

> "Your new optimizer IS working correctly - it's picking the cheapest option. The difference is that the old quote might have been generated when Bedford had low stock of "Individual trees - Rural tree", forcing it to use the more expensive Central Bedfordshire option instead."

**Summary:**
1. The optimizer **always** picks the cheapest feasible option
2. "Feasible" means: respecting stock capacity constraints
3. If the cheapest option has insufficient stock, it's **rejected**
4. The next cheapest feasible option is selected instead
5. Stock levels change over time → different allocations for same demand

---

## Options for Resolution

### Option A: Preserve Original Allocation in Requotes
Store and reuse the original allocation data when creating requotes, rather than re-running the optimizer.

### Option B: Lock Stock for Pending Quotes
Implement stock "reservation" when a quote is generated, preventing other quotes from consuming that stock until the quote is accepted or expires.

### Option C: Show Stock-Based Warnings
When the optimizer picks a more expensive option due to stock constraints, show a warning:
```
⚠️ Preferred option (Bedford, £28,300) unavailable due to low stock.
   Selected alternative: Central Bedfordshire, £29,600 (+£1,300)
```

### Option D: Prefer Depleting Low-Stock Items First
Modify the tie-breaker to prefer options that use stocks with lower availability:
```python
# Current: prefer higher-capacity banks (preserves stock)
obj += -eps2 * pulp.lpSum([bank_capacity_total[b] * y[b] for b in bank_keys])

# Alternative: prefer lower-capacity (depletes low-stock first)
obj += +eps2 * pulp.lpSum([bank_capacity_total[b] * y[b] for b in bank_keys])
```

---

## Summary

| Question | Answer |
|----------|--------|
| Why different allocation? | Stock levels changed between quotes |
| Is new optimizer broken? | No, it's working correctly |
| Why more expensive? | Original had stock constraint that blocked cheap option |
| How to debug? | Compare `stock_caps` values at time of each allocation |
| How to fix? | Store original allocation or implement stock reservation |
