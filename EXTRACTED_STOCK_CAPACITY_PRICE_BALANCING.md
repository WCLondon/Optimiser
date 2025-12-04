# Extracted Stock Capacity and Price Balancing Logic in Optimizer Core

This document explains how the optimizer core balances stock availability with price minimization. This is critical for debugging when "low stock management" logic appears to be missing.

---

## Overview: The Optimization Problem

The optimizer solves a **Linear Programming (LP)** problem that:
1. **Minimizes total cost** (primary objective)
2. **Respects stock capacity constraints** (hard constraints)
3. **Uses tie-breakers** for equal-cost options (proximity, then capacity)

**Key Insight:** Stock capacity is enforced as a **hard constraint**, not a soft preference. The optimizer cannot allocate more units from a stock item than `quantity_available`.

---

## 1. How Stock Capacity Data is Built

### 1.1 Stock Capacity Dictionary Creation (lines 2012-2016, 2611-2614)

```python
# In prepare_options() - Area ledger
stock_caps: Dict[str, float] = {}
stock_bankkey: Dict[str, str] = {}
for _, s in Stock.iterrows():
    stock_caps[sstr(s["stock_id"])] = float(s.get("quantity_available", 0) or 0.0)
    stock_bankkey[sstr(s["stock_id"])] = sstr(s.get("BANK_KEY") or s.get("bank_id"))
```

```python
# Combining all three ledgers (lines 2611-2614)
stock_caps: Dict[str, float] = {}
stock_caps.update(caps_area)      # From prepare_options()
stock_caps.update(caps_hedge)     # From prepare_hedgerow_options()
stock_caps.update(caps_water)     # From prepare_watercourse_options()
```

**Data Structure:**
```python
stock_caps = {
    "stock_001": 15.5,   # 15.5 units available
    "stock_002": 3.2,    # 3.2 units available
    "stock_003": 0.0,    # No units available (will be rejected)
    ...
}
```

---

## 2. How Options Track Stock Usage

### 2.1 Each Option Specifies Which Stock(s) It Uses (lines 911-916, 2166, 2306)

**Normal (non-paired) allocation:**
```python
{
    "demand_idx": 0,
    "demand_habitat": "Modified grassland",
    "supply_habitat": "Mixed scrub",
    "BANK_KEY": "Nunthorpe",
    "tier": "local",
    "unit_price": 28000,
    "stock_id": "stock_001",
    "stock_use": {"stock_001": 1.0},  # Uses 1.0 units of stock per demand unit
    ...
}
```

**Paired allocation (uses two stocks):**
```python
{
    "demand_idx": 0,
    "demand_habitat": "Modified grassland", 
    "supply_habitat": "Mixed scrub + Native grassland",
    "BANK_KEY": "Cobham",
    "tier": "far",
    "unit_price": 22000,  # Blended price
    "stock_use": {
        "stock_002": 0.5,  # 50% from stock_002 (demand habitat)
        "stock_003": 0.5   # 50% from stock_003 (companion habitat)
    },
    ...
}
```

**The `stock_use` dictionary maps `stock_id` → coefficient (multiplier per demand unit).**

---

## 3. LP Solver: Stock Capacity Constraints (lines 2807-2814)

This is the **critical constraint** that enforces stock limits:

```python
# Stock capacity constraints
use_map: Dict[str, List[Tuple[int, float]]] = {}
for i, opt in enumerate(options):
    for sid, coef in opt["stock_use"].items():
        use_map.setdefault(sid, []).append((i, float(coef)))

for sid, pairs in use_map.items():
    cap = float(stock_caps.get(sid, 0.0))
    # CONSTRAINT: Sum of (coefficient × allocation) for each stock ≤ capacity
    prob += pulp.lpSum([coef * x[i] for (i, coef) in pairs]) <= cap
```

### What This Does:
1. **Builds a map** of which options use each stock item
2. **For each stock item**, adds a constraint:
   - Sum of all allocations (weighted by `stock_use` coefficient) ≤ available capacity

### Example:
- Stock "stock_001" has `quantity_available = 10.0`
- Option 3 uses `{"stock_001": 1.0}` (full units)
- Option 7 uses `{"stock_001": 0.5}` (half units for paired allocation)
- Constraint: `1.0 * x[3] + 0.5 * x[7] <= 10.0`

---

## 4. Objective Function: Price + Tie-Breakers (lines 2780-2788)

```python
# Primary: minimize cost
obj = pulp.lpSum([options[i]["unit_price"] * x[i] for i in range(len(options))])

eps = 1e-9   # Proximity tie-break weight (very small)
eps2 = 1e-14 # Capacity tie-break weight (even smaller)

# Secondary tie-break: prefer closer banks (local > adjacent > far)
obj += eps * pulp.lpSum([TIER_PROXIMITY_RANK.get(options[i].get("tier", "far"), 2) * x[i] for i in range(len(options))])

# Tertiary tie-break: prefer higher-capacity banks
obj += -eps2 * pulp.lpSum([bank_capacity_total[b] * y[b] for b in bank_keys])
```

**Tier Proximity Ranking:**
```python
TIER_PROXIMITY_RANK = {
    "local": 0,     # Most preferred
    "adjacent": 1,  # Second choice
    "far": 2        # Least preferred
}
```

### Objective Function Breakdown:
1. **Primary:** Minimize `Σ(unit_price × units_allocated)`
2. **Secondary:** Among equal-cost options, prefer closer banks
3. **Tertiary:** Among equal-cost + equal-proximity, prefer banks with more total capacity

**Important:** The capacity tie-breaker is **negative** (`-eps2`), meaning it **subtracts** from the objective. This causes the solver to prefer higher-capacity banks when all else is equal.

---

## 5. Bank Capacity Total Calculation (lines 2762-2766)

```python
# Calculate tie-break metrics
bank_capacity_total: Dict[str, float] = {b: 0.0 for b in bank_keys}
for sid, cap in stock_caps.items():
    bkey = stock_bankkey.get(sid, "")
    if bkey in bank_capacity_total:
        bank_capacity_total[bkey] += float(cap or 0.0)
```

**What This Does:**
- Sums up all available stock for each bank
- Used as a tie-breaker in the objective function
- **Higher total capacity = preferred when cost and proximity are equal**

---

## 6. Greedy Fallback Solver: Explicit Stock Checking (lines 2920-2997)

When the LP solver fails, the greedy fallback explicitly checks and updates stock:

```python
# ---- Greedy fallback (unchanged) ----
caps = stock_caps.copy()  # Make a working copy of stock capacities
used_banks: List[str] = []

for di, drow in demand_df.iterrows():
    need = float(drow["units_required"])
    
    # Sort by price first, then by proximity, then by capacity (descending)
    cand_idx = sorted(
        [i for i in range(len(options)) if options[i]["demand_idx"] == di],
        key=lambda i: (
            options[i]["unit_price"],                                           # 1. Lowest price first
            TIER_PROXIMITY_RANK.get(options[i].get("tier", "far"), 2),         # 2. Closest tier first
            -sum(stock_caps.get(sid, 0.0) for sid in options[i]["stock_use"].keys())  # 3. Highest capacity first
        )
    )

    best_i = None
    for i in cand_idx:
        opt = options[i]
        bkey = opt["BANK_KEY"]
        
        # Check bank limit
        if not bank_ok(bkey):
            continue
        
        # Check if enough stock for this option
        ok = True
        for sid, coef in opt["stock_use"].items():
            req = coef * need  # Required stock = coefficient × demand units
            if caps.get(sid, 0.0) + 1e-9 < req:  # Not enough stock
                ok = False
                break
        
        if not ok:
            continue  # Skip this option, try next
        
        # Found a valid option
        this_cost = need * opt["unit_price"]
        if this_cost < best_cost - 1e-9:
            best_cost = this_cost
            best_i = i

    # Deduct stock after allocation
    opt = options[best_i]
    for sid, coef in opt["stock_use"].items():
        caps[sid] = caps.get(sid, 0.0) - coef * need  # Reduce remaining capacity
```

### Key Points:
1. **Copies stock capacities** at the start
2. **Checks each option** to see if enough stock exists
3. **Deducts used stock** after allocation
4. **Prefers higher-capacity options** via the sort key (negative capacity = higher ranked)

---

## 7. Complete Stock Balancing Flow Diagram

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         STOCK TABLE (from Supabase)                      │
│  stock_id | habitat_name | bank_id | BANK_KEY | quantity_available       │
│  ---------|--------------|---------|----------|------------------------  │
│  stk_001  | Mixed scrub  | BK001   | Nunthorpe| 15.50                   │
│  stk_002  | Grassland    | BK002   | Cobham   | 3.20                    │
│  stk_003  | Woodland     | BK002   | Cobham   | 8.00                    │
└───────────────────────────────────┬─────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                    BUILD stock_caps DICTIONARY                           │
│                                                                          │
│  for _, s in Stock.iterrows():                                          │
│      stock_caps[s["stock_id"]] = float(s["quantity_available"])         │
│                                                                          │
│  Result: stock_caps = {"stk_001": 15.5, "stk_002": 3.2, "stk_003": 8.0} │
└───────────────────────────────────┬─────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                    BUILD OPTIONS WITH stock_use                          │
│                                                                          │
│  Option 1: {"stock_use": {"stk_001": 1.0}, "unit_price": 28000, ...}    │
│  Option 2: {"stock_use": {"stk_002": 1.0}, "unit_price": 30000, ...}    │
│  Option 3: {"stock_use": {"stk_002": 0.5, "stk_003": 0.5}, ...}         │
└───────────────────────────────────┬─────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                         LP SOLVER (PuLP)                                 │
│                                                                          │
│  Objective: Minimize Σ(unit_price × x[i])                               │
│             + ε × Σ(proximity_rank × x[i])        # tie-breaker         │
│             - ε² × Σ(bank_capacity × y[bank])    # capacity preference  │
│                                                                          │
│  Subject to:                                                             │
│  1. Σ(x[options for demand]) = demand_units    (fulfill demand)         │
│  2. Σ(coef × x[i]) ≤ stock_cap                 (stock limits)           │
│  3. Σ(y[banks]) ≤ max_banks                    (bank count limit)       │
└───────────────────────────────────┬─────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                         ALLOCATION RESULT                                │
│                                                                          │
│  Demand 1: 5 units from Nunthorpe (stk_001)  →  5.0 units deducted      │
│  Demand 2: 3 units from Cobham (stk_002+stk_003 paired) → 1.5 + 1.5    │
│                                                                          │
│  Stock remaining:                                                        │
│    stk_001: 15.5 - 5.0 = 10.5 units                                     │
│    stk_002: 3.2 - 1.5 = 1.7 units                                       │
│    stk_003: 8.0 - 1.5 = 6.5 units                                       │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## 8. Debugging: What Can Go Wrong

### 8.1 Stock Ignored or Not Respecting Capacity

**Check Point 1:** Is `quantity_available` being read correctly?
```python
# In prepare_options(), line 2015:
stock_caps[sstr(s["stock_id"])] = float(s.get("quantity_available", 0) or 0.0)
```
- Ensure the column name is exactly `quantity_available`
- Ensure values are numeric (not strings like "10.5")

**Check Point 2:** Is `stock_use` being set on options?
```python
# In prepare_options(), lines 2166:
"stock_use": {sstr(srow["stock_id"]): 1.0},
```
- Each option must have a `stock_use` dictionary
- Missing this = no constraint on that option

**Check Point 3:** Is the constraint being added?
```python
# Line 2814:
prob += pulp.lpSum([coef * x[i] for (i, coef) in pairs]) <= cap
```
- If `stock_caps.get(sid, 0.0)` returns 0 for all stocks, constraints may be ineffective

### 8.2 Allocating More Than Available

**Root Cause:** `stock_caps` dictionary not being populated correctly.

**Debug:**
```python
print("Stock caps:", stock_caps)
print("Option stock_use:", options[0]["stock_use"])
```

### 8.3 Low Stock Not Being Preferred

The optimizer prefers **higher capacity** banks as a tie-breaker, not lower. This is intentional:
- Higher capacity = more flexibility = less risk of stock-out
- Low stock is respected via **hard constraints**, not preferences

**To change behavior:** Modify the capacity tie-breaker coefficient from negative to positive:
```python
# Currently (prefers higher capacity):
obj += -eps2 * pulp.lpSum([bank_capacity_total[b] * y[b] for b in bank_keys])

# To prefer lower capacity instead (NOT RECOMMENDED):
obj += +eps2 * pulp.lpSum([bank_capacity_total[b] * y[b] for b in bank_keys])
```

---

## 9. Key Variables Summary

| Variable | Type | Purpose | Location |
|----------|------|---------|----------|
| `stock_caps` | `Dict[str, float]` | Maps stock_id → available units | Lines 783, 2012, 2400 |
| `stock_bankkey` | `Dict[str, str]` | Maps stock_id → BANK_KEY | Lines 784, 2013, 2401 |
| `opt["stock_use"]` | `Dict[str, float]` | Maps stock_id → usage coefficient | Lines 916, 2166, 2306 |
| `bank_capacity_total` | `Dict[str, float]` | Total capacity per bank (for tie-breaking) | Line 2762 |
| `use_map` | `Dict[str, List[Tuple]]` | Maps stock_id → list of (option_idx, coefficient) | Line 2808 |

---

## 10. Summary: How Stock Balancing Works

1. **Stock capacity is read** from `quantity_available` column in Stock table
2. **Each option specifies** which stock(s) it uses via `stock_use` dictionary
3. **LP solver enforces** capacity constraints: `Σ(coef × allocation) ≤ capacity`
4. **Tie-breaker prefers** banks with higher total capacity (more flexibility)
5. **Greedy fallback** explicitly checks and deducts stock after each allocation

**The key piece for "low stock management" is the stock capacity constraint (line 2814).** If this constraint is missing or `stock_caps` is empty, the optimizer will ignore stock limits.
