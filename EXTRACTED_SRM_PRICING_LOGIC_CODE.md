# Extracted SRM (Spatial Risk Multiplier) / Pricing Logic for CSV Generation

This document explains the SRM (Spatial Risk Multiplier) and Pricing logic used in the CSV generation for the Sales & Quotes Excel workbook. This is critical to understand to avoid incorrect pricing in the database.

---

## Overview: What is SRM?

**SRM (Spatial Risk Multiplier)** determines how many credits a buyer needs based on the geographic relationship between their development site and the habitat bank.

| Tier | SRM | Formula | Meaning |
|------|-----|---------|---------|
| **Local** | 1.0 | `=1/1` | Same LPA or NCA - buyer needs exact credits |
| **Adjacent** | 4/3 ≈ 1.333 | `=4/3` | Neighboring LPA/NCA - buyer needs 33% more credits |
| **Far** | 2.0 | `=2/1` | Not local or adjacent - buyer needs 2× credits |

**Key Formula:**
```
Stock Take (ST) = Spatial Multiplier × # Credits
Price inc SRM = ST × Quoted Price per Unit
```

---

## CRITICAL: Paired vs Non-Paired Allocations

### Non-Paired Allocations
Standard single-bank allocations where SRM is applied directly:
- SRM = 1.0 for local
- SRM = 4/3 for adjacent  
- SRM = 2.0 for far

### Paired Allocations (SRM Manual)
When habitat is allocated across two banks/habitats to reduce cost, the **SRM is handled manually**:
- CSV column AD shows `1` (not the SRM formula)
- CSV column T shows `"SRM manual (0.5)"` or `"SRM manual (0.75)"`
- The SRM is already **baked into the blended price**

**This is important**: For paired allocations, the stock_use ratios determine the split:
- Adjacent tier: 3/4 demand + 1/4 companion = blended price with SRM 4/3 effect
- Far tier: 1/2 demand + 1/2 companion = blended price with SRM 2.0 effect

---

## 1. Spatial Multiplier Calculation (sales_quotes_csv.py, lines 534-540)

```python
# Calculate spatial multiplier
if tier == "local":
    spatial_multiplier_numeric = 1.0
elif tier == "adjacent":
    spatial_multiplier_numeric = 4.0 / 3.0  # ≈ 1.333
else:  # far
    spatial_multiplier_numeric = 2.0
```

---

## 2. Stock Take (ST) Calculation (sales_quotes_csv.py, lines 245-274)

```python
# Calculate totals for this row
# Note: We now use ST (Stock Take) = spatial_multiplier × # credits
# For paired allocations, spatial_multiplier = 1
# For non-paired allocations, spatial_multiplier varies based on tier

# Get the numeric spatial multiplier for calculations
if is_paired:
    sm_numeric = 1.0  # <<< Paired allocations use 1.0 because SRM is in the blended price
else:
    sm_numeric = spatial_multiplier_numeric

total_st = 0.0  # Total Stock Take (sum of ST values)
total_credit_price = 0.0  # Total price including SRM

for h in habitats:
    # Get # credits (units_supplied for non-paired, effective_units for paired)
    if is_paired:
        credits = h.get("effective_units", 0.0)
    else:
        credits = h.get("units_supplied", 0.0)
    
    # Calculate ST = spatial_multiplier × # credits
    st = sm_numeric * credits
    total_st += st
    
    # Calculate price = ST × Quoted Price
    quoted_price = h.get("avg_effective_unit_price", 0.0)
    total_credit_price += st * quoted_price
```

**Key Points:**
- For **non-paired**: `ST = SRM × units_supplied`
- For **paired**: `ST = 1.0 × effective_units` (SRM already in `avg_effective_unit_price`)

---

## 3. CSV Column AD: Spatial Multiplier Formula (sales_quotes_csv.py, lines 324-340)

```python
# Column AD (index 29): Spatial Multiplier
if is_paired:
    # For paired allocations, use numeric 1
    row[29] = "1"
else:
    # For non-paired, use formula
    if spatial_relation == "adjacent":
        row[29] = "=4/3"
    elif spatial_relation == "far":
        row[29] = "=2/1"
    else:
        # Default to 1 if relation not specified
        row[29] = "1"
```

**Output in Excel:**
| Allocation Type | Tier | Column AD Value |
|-----------------|------|-----------------|
| Non-paired | Local | `1` |
| Non-paired | Adjacent | `=4/3` |
| Non-paired | Far | `=2/1` |
| Paired | Any | `1` |

---

## 4. CSV Column T: SRM Manual Notes (sales_quotes_csv.py, lines 304-316)

```python
# Column T (index 19): Notes / SRM manual
# Priority 1: Bank fallback note (if using 'Other')
# Priority 2: SRM logic based on pairing and spatial_relation
if bank_fallback_note:
    # If bank is not in valid combinations, put the actual bank name here
    row[19] = bank_fallback_note
elif is_paired:
    if spatial_relation == "far":
        row[19] = "SRM manual (0.5)"
    elif spatial_relation == "adjacent":
        row[19] = "SRM manual (0.75)"
    # else: blank
# else: blank for non-paired
```

**Why paired uses "SRM manual":**
- The blended price already accounts for the SRM
- The 0.5 or 0.75 indicates the *effective SRM* built into the price
- This tells the user that SRM adjustment was done upstream, not in Excel

---

## 5. Per-Habitat ST Calculation (sales_quotes_csv.py, lines 407-440)

```python
# Process all habitats (up to 8)
for hab_idx in range(min(len(habitats), 8)):
    habitat = habitats[hab_idx]
    base_idx = 47 + (hab_idx * 7)  # Starting column for this habitat
    
    # Column 0: Type
    row[base_idx] = str(habitat.get("type", "")).strip()
    
    # Column 1: # credits
    # Use effective_units if paired, otherwise units_supplied
    if is_paired:
        units_value = habitat.get("effective_units", 0.0)
    else:
        units_value = habitat.get("units_supplied", 0.0)
    row[base_idx + 1] = f"{units_value:.4f}"
    
    # Column 2: ST (Stock Take) = spatial_multiplier × # credits
    st = sm_numeric * units_value
    row[base_idx + 2] = f"{st:.4f}"
    
    # Column 4: Quoted Price (avg_effective_unit_price)
    quoted_price = habitat.get("avg_effective_unit_price", 0.0)
    row[base_idx + 4] = f"{quoted_price:.2f}"
    
    # Column 6: Price inc SRM (Total Cost) = ST × Quoted Price
    habitat_total_cost = st * quoted_price
    row[base_idx + 6] = f"{habitat_total_cost:.2f}"
```

---

## 6. How Paired Allocations Get Their Blended Price (app.py, lines 3351-3365)

The blended price for paired allocations is calculated in the optimizer:

```python
# Calculate blended price and stock_use based on tier
# SRM is already baked into pricing, so we use weighted average

if target_tier == "adjacent":
    srm = 4/3
    stock_use_demand = 3/4  # Main component contributes 3/4
    stock_use_companion = 1/4  # Companion contributes 1/4
    blended_price = stock_use_demand * price_demand + stock_use_companion * price_companion
    
else:  # far
    srm = 2.0
    stock_use_demand = 1/2  # Main component contributes 1/2
    stock_use_companion = 1/2  # Companion contributes 1/2
    blended_price = stock_use_demand * price_demand + stock_use_companion * price_companion
```

**Why this works:**
- For **adjacent (SRM 4/3)**: To get 1.0 effective unit, buyer needs 4/3 raw units
  - 3/4 from main habitat + 1/4 from companion = 1.0 effective
  - The blended price reflects this weighted cost

- For **far (SRM 2.0)**: To get 1.0 effective unit, buyer needs 2× raw units
  - 1/2 from main habitat + 1/2 from companion = 1.0 effective
  - The blended price reflects this 50/50 cost

---

## 7. How `effective_units` and `avg_effective_unit_price` are Calculated (app.py, lines 4580-4595)

```python
# Calculate effective units based on tier
expanded_alloc["effective_units"] = expanded_alloc.apply(
    lambda r: r["units_supplied"] * (4/3 if r.get("tier") == "adjacent" else 
                                      2.0 if r.get("tier") == "far" else 1.0),
    axis=1
)

# Aggregate to site_hab_totals
site_hab_totals = expanded_alloc.groupby(
    ["BANK_KEY", "bank_name", "supply_habitat", "tier", "allocation_type"],
    as_index=False
).agg(
    units_supplied=("units_supplied", "sum"),
    effective_units=("effective_units", "sum"),
    cost=("cost", "sum")
)

# Calculate average effective unit price
site_hab_totals["avg_effective_unit_price"] = (
    site_hab_totals["cost"] / site_hab_totals["effective_units"].replace(0, np.nan)
)
```

---

## Complete Pricing Flow Diagram

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         OPTIMIZER OUTPUT                                 │
│  alloc_df contains: units_supplied, cost, tier, allocation_type         │
└───────────────────────────────────┬─────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                    CALCULATE EFFECTIVE UNITS                             │
│  effective_units = units_supplied × SRM                                  │
│    • Local:    × 1.0                                                     │
│    • Adjacent: × 4/3                                                     │
│    • Far:      × 2.0                                                     │
└───────────────────────────────────┬─────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│               CALCULATE AVG EFFECTIVE UNIT PRICE                         │
│  avg_effective_unit_price = total_cost / effective_units                 │
│                                                                          │
│  This gives the "per effective unit" price that accounts for SRM         │
└───────────────────────────────────┬─────────────────────────────────────┘
                                    │
                    ┌───────────────┴───────────────┐
                    ▼                               ▼
┌───────────────────────────────┐   ┌───────────────────────────────────┐
│      NON-PAIRED ALLOCATION    │   │        PAIRED ALLOCATION          │
│                               │   │                                   │
│  • Use units_supplied         │   │  • Use effective_units            │
│  • SM = SRM (1, 4/3, or 2)    │   │  • SM = 1 (SRM in price)          │
│  • Column AD: "=4/3" etc      │   │  • Column AD: "1"                 │
│  • Column T: blank            │   │  • Column T: "SRM manual (0.5)"   │
│                               │   │                                   │
│  ST = SM × units_supplied     │   │  ST = 1 × effective_units         │
│  Price = ST × quoted_price    │   │  Price = ST × blended_price       │
└───────────────────────────────┘   └───────────────────────────────────┘
                    │                               │
                    └───────────────┬───────────────┘
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                           CSV OUTPUT                                     │
│  Column AD: Spatial Multiplier (formula or "1")                          │
│  Column T:  Notes/SRM manual                                             │
│  Habitat columns: # credits, ST, Quoted Price, Price inc SRM             │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## Example Calculations

### Example 1: Non-Paired, Adjacent Tier
- **Input:** 1.0 units_supplied, £30,000 quoted price, adjacent tier
- **SRM:** 4/3 = 1.333...
- **ST:** 1.0 × (4/3) = 1.333 units
- **Price inc SRM:** 1.333 × £30,000 = £40,000
- **Column AD:** `=4/3`
- **Column T:** (blank)

### Example 2: Paired, Far Tier
- **Input:** 2.0 effective_units, £25,000 blended price, far tier, paired
- **SRM:** Already in blended price (manual)
- **SM for CSV:** 1.0 (because SRM is baked in)
- **ST:** 2.0 × 1.0 = 2.0 units
- **Price inc SRM:** 2.0 × £25,000 = £50,000
- **Column AD:** `1`
- **Column T:** `SRM manual (0.5)`

### Example 3: Non-Paired, Local Tier
- **Input:** 0.5 units_supplied, £28,000 quoted price, local tier
- **SRM:** 1.0
- **ST:** 0.5 × 1.0 = 0.5 units
- **Price inc SRM:** 0.5 × £28,000 = £14,000
- **Column AD:** `1`
- **Column T:** (blank)

---

## Common Pricing Mistakes to Avoid

### ❌ Mistake 1: Double-Applying SRM to Paired Allocations
**Wrong:** Using `effective_units × (4/3)` for paired adjacent allocations
**Right:** Using `effective_units × 1.0` because SRM is already in the blended price

### ❌ Mistake 2: Using `units_supplied` for Paired Allocations
**Wrong:** Using raw `units_supplied` from paired allocations
**Right:** Using `effective_units` which already has the SRM factored in

### ❌ Mistake 3: Showing SRM Formula for Paired Allocations
**Wrong:** Column AD = `=4/3` for paired allocations
**Right:** Column AD = `1` with Column T = `SRM manual (0.5)` or `SRM manual (0.75)`

---

## Summary

| Allocation Type | Column AD | ST Calculation | Price Unit | SRM Location |
|-----------------|-----------|----------------|------------|--------------|
| Non-paired, Local | `1` | SM=1.0 × units_supplied | quoted_price | Direct in formula |
| Non-paired, Adjacent | `=4/3` | SM=1.33 × units_supplied | quoted_price | Direct in formula |
| Non-paired, Far | `=2/1` | SM=2.0 × units_supplied | quoted_price | Direct in formula |
| Paired, Adjacent | `1` | SM=1.0 × effective_units | blended_price | In blended price |
| Paired, Far | `1` | SM=1.0 × effective_units | blended_price | In blended price |

**The key insight:** For paired allocations, the SRM is **pre-calculated** into the blended price by the optimizer, so the CSV just uses a multiplier of 1.0 and notes "SRM manual" to indicate manual handling.
