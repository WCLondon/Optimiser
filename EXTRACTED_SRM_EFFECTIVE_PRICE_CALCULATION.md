# SRM (Spatial Risk Multiplier) - Effective Price Calculation

## Overview

**CRITICAL: VSCode Copilot's understanding is INCORRECT.**

The example given is wrong. Here's the correct logic:

## The CORRECT SRM Pricing Logic

### Key Principle
**SRM does NOT change the unit price charged to the client.** Instead, SRM affects how many **stock units** are consumed from the bank per unit of client demand.

### SRM Multipliers (Spatial Tiers)
| Tier | SRM Value | Stock Consumption |
|------|-----------|-------------------|
| Local | 1.0 | 1 demand unit = 1 stock unit |
| Adjacent | 4/3 (≈1.33) | 1 demand unit = 1.33 stock units |
| Far | 2.0 | 1 demand unit = 2 stock units |

---

## CORRECT Calculation Example

### Scenario
- Client needs: **0.3 effective units** of habitat
- Bank tier: **"far"** (SRM = 2.0)
- Bank's unit price: **£100,000** per unit

### Step-by-Step Calculation

```
1. Demand (what client needs):     0.3 units
2. SRM for "far" tier:             2.0
3. Stock Take (bank consumption):  0.3 × 2.0 = 0.6 units from bank
4. Unit price (from pricing table): £100,000
5. Total cost to client:           0.3 × £100,000 = £30,000
```

### What the Client Report Should Show
| # Units | Price Per Unit | Offset Cost |
|---------|----------------|-------------|
| 0.3     | £100,000       | £30,000     |

### What the CSV Should Show (Sales & Quotes)
| Column | Value | Explanation |
|--------|-------|-------------|
| Q (# credits) | 0.3 | Demand units |
| T (SRM) | 2 or `=2/1` | The SRM multiplier |
| U (ST) | 0.6 | Stock Take = demand × SRM |
| V (Quoted Price) | £100,000 | From pricing table |
| W (Price inc SRM) | £30,000 | demand × quoted price |

---

## The VSCode Copilot Error

VSCode copilot incorrectly stated:
> "Cost charged: 0.6 × £100k = £60k"

This is **WRONG**. The correct calculation is:
```
Cost = demand_units × unit_price
Cost = 0.3 × £100,000 = £30,000
```

NOT:
```
Cost ≠ stock_take × unit_price  ← WRONG!
Cost ≠ 0.6 × £100,000 = £60,000  ← WRONG!
```

---

## Code Implementation (from app.py)

### For Non-Paired Allocations (lines ~5890-5920)

```python
# 1. Get demand units (what client needs)
units_supplied = allocation["units_supplied"]  # e.g., 0.3

# 2. Get SRM based on tier
tier = allocation["tier"]
if tier == "local":
    spatial_multiplier = 1.0
elif tier == "adjacent":
    spatial_multiplier = Decimal("4") / Decimal("3")  # 1.333...
else:  # "far"
    spatial_multiplier = 2.0

# 3. Calculate Stock Take (what bank loses)
stock_take = units_supplied * spatial_multiplier  # 0.3 × 2.0 = 0.6

# 4. Get unit price from allocation
unit_price = allocation["unit_price"]  # e.g., 100000

# 5. Calculate cost (DEMAND × PRICE, not STOCK_TAKE × PRICE)
cost = units_supplied * unit_price  # 0.3 × 100000 = 30000
```

### For Client Report Table (lines ~4750-4850)

```python
# Client sees:
# - Units: demand_units (0.3)
# - Price per unit: unit_price (£100,000)
# - Offset cost: demand_units × unit_price (£30,000)

display_units = allocation["units_supplied"]
display_price = allocation["unit_price"]
display_cost = display_units * display_price
```

### For CSV Generation (sales_quotes_csv.py)

```python
# Column Q: # credits = demand units
row["# credits"] = allocation["units_supplied"]  # 0.3

# Column T: SRM formula or value
if tier == "local":
    row["SRM"] = 1
elif tier == "adjacent":
    row["SRM"] = "=4/3"
else:
    row["SRM"] = "=2/1"

# Column U: Stock Take = demand × SRM
row["ST"] = units_supplied * spatial_multiplier  # 0.6

# Column V: Quoted price from pricing table
row["Quoted Price"] = unit_price  # 100000

# Column W: Price inc SRM = demand × quoted price
row["Price inc SRM"] = units_supplied * unit_price  # 30000
```

---

## Summary: The Golden Rule

```
┌─────────────────────────────────────────────────────────────┐
│                    THE GOLDEN RULE                          │
│                                                             │
│   Client Cost = Demand Units × Unit Price                   │
│                                                             │
│   NOT: Client Cost ≠ Stock Take × Unit Price                │
│                                                             │
│   SRM only affects how much stock the bank loses,           │
│   NOT what the client pays per unit of demand.              │
└─────────────────────────────────────────────────────────────┘
```

### Visual Flow

```
Client needs 0.3 units (demand)
          │
          ▼
┌─────────────────────┐
│ Tier Lookup         │
│ → "far" → SRM = 2.0 │
└─────────────────────┘
          │
          ▼
┌─────────────────────────────────────────────┐
│ Stock Take = 0.3 × 2.0 = 0.6 units          │
│ (This is what the bank loses from inventory)│
└─────────────────────────────────────────────┘
          │
          ▼
┌─────────────────────────────────────────────┐
│ Price Lookup: £100,000/unit                 │
│ (From Pricing table for this habitat)       │
└─────────────────────────────────────────────┘
          │
          ▼
┌─────────────────────────────────────────────┐
│ Client Cost = 0.3 × £100,000 = £30,000      │
│ (Demand × Unit Price, NOT Stock Take × Price)│
└─────────────────────────────────────────────┘
```

---

## Special Case: Paired Allocations

For paired allocations, the SRM is **already baked into the blended price**. Do NOT apply SRM again.

```python
if allocation["allocation_type"] == "paired":
    # SRM already included in unit_price
    # Column T shows: "SRM manual (0.5)" or "SRM manual (0.75)"
    # Stock Take = effective_units (NOT demand × SRM)
    stock_take = allocation.get("effective_units", units_supplied)
    
    # Cost is still: demand × blended_price
    cost = units_supplied * unit_price
```

---

## Debugging Checklist

If costs are coming out wrong, check:

1. **Are you multiplying by SRM for cost?** ← WRONG
   - Cost = demand × price (NO SRM in cost calculation)
   
2. **Is Stock Take calculated correctly?**
   - Stock Take = demand × SRM (for non-paired)
   - Stock Take = effective_units (for paired)

3. **Is the tier correct?**
   - Check `tier_for_bank()` is using correct neighbors

4. **For paired allocations:**
   - SRM is already in the blended price
   - Don't double-apply SRM

---

## Key Line References in app.py

| Purpose | Lines | Description |
|---------|-------|-------------|
| Tier lookup | 1717-1745 | `tier_for_bank()` |
| SRM assignment | 5890-5905 | Based on tier |
| Stock Take calc | 5907-5910 | demand × SRM |
| Cost calc | 5915-5920 | demand × unit_price |
| CSV output | sales_quotes_csv.py:180-220 | All columns |
