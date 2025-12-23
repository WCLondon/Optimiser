# Paired Allocation CSV Bundling Logic

## The Key Concept

**ONE ALLOCATION = ONE CSV ROW**

When an allocation is marked as `allocation_type == "paired"`, it means the optimizer is using a **blended pricing strategy** where multiple habitat types from a single bank are bundled together. In the CSV output:

- All habitats from the same `BANK_KEY` are grouped into **ONE row**
- Up to **8 habitats** can fit in each CSV row (columns AV-CY)
- The reference number gets **letter suffixes** (a, b, c) only if there are **multiple banks**

---

## How Grouping Works

### Code Location: `sales_quotes_csv.py` lines 503-588

```python
# Group by bank - each bank gets its own row
for bank_key, bank_group in alloc_df.groupby(bank_ref_col):
    
    # Determine if this bank group contains ANY paired allocation
    allocation_types = bank_group.get("allocation_type", ...)
    is_paired = any(str(t).lower() == "paired" for t in allocation_types)
    
    # Aggregate ALL habitats from this bank into one list
    habitats = []
    for _, row in bank_group.iterrows():
        habitats.append({
            "type": habitat_type,
            "units_supplied": units_supplied,
            "effective_units": effective_units,
            "avg_effective_unit_price": avg_effective_unit_price
        })
```

### The Logic:

1. **Group by `BANK_KEY`** - All allocations from the same bank go together
2. **Check `is_paired`** - If ANY allocation in the bank group has `allocation_type == "paired"`, the entire row is treated as paired
3. **Bundle habitats** - All habitats from that bank go into the same row's habitat columns

---

## Example: Two Paired Habitats from One Bank

**Input allocations:**
```python
[
    {"BANK_KEY": "Central Bedfordshire", "supply_habitat": "Grassland - Traditional orchards", 
     "allocation_type": "paired", "units_supplied": 0.75, "effective_units": 0.75, ...},
    {"BANK_KEY": "Central Bedfordshire", "supply_habitat": "Heathland and shrub - Mixed scrub", 
     "allocation_type": "paired", "units_supplied": 0.25, "effective_units": 0.25, ...}
]
```

**CSV Output: ONE ROW with two habitats filled:**

| Column AC | Column AD | ... | Column AV | Column AW | ... | Column BC | Column BD |
|-----------|-----------|-----|-----------|-----------|-----|-----------|-----------|
| WC1P6 - Central Bedfordshire | 1 | ... | Grassland - Traditional orchards | 0.7500 | ... | Heathland and shrub - Mixed scrub | 0.2500 |

---

## Column Mapping for Habitats

Each habitat occupies 7 columns. The first 8 habitat slots are:

| Habitat # | Start Index | Columns (Excel) | Contents |
|-----------|-------------|-----------------|----------|
| 1 | 47 | AV-BB | Type, # credits, ST, blank, Quoted Price, blank, Price inc SRM |
| 2 | 54 | BC-BI | Type, # credits, ST, blank, Quoted Price, blank, Price inc SRM |
| 3 | 61 | BJ-BP | Type, # credits, ST, blank, Quoted Price, blank, Price inc SRM |
| 4 | 68 | BQ-BW | Type, # credits, ST, blank, Quoted Price, blank, Price inc SRM |
| 5 | 75 | BX-CD | Type, # credits, ST, blank, Quoted Price, blank, Price inc SRM |
| 6 | 82 | CE-CK | Type, # credits, ST, blank, Quoted Price, blank, Price inc SRM |
| 7 | 89 | CL-CR | Type, # credits, ST, blank, Quoted Price, blank, Price inc SRM |
| 8 | 96 | CS-CY | Type, # credits, ST, blank, Quoted Price, blank, Price inc SRM |

---

## Spatial Multiplier Handling

### Code Location: `sales_quotes_csv.py` lines 324-337

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
        row[29] = "1"
```

### SRM Manual Note (Column T)

For paired allocations, the SRM is already baked into the blended price, so we add a note:

```python
# Code Location: lines 310-315
elif is_paired:
    if spatial_relation == "far":
        row[19] = "SRM manual (0.5)"
    elif spatial_relation == "adjacent":
        row[19] = "SRM manual (0.75)"
```

---

## Multi-Bank Reference Suffixing

### Code Location: `sales_quotes_csv.py` lines 291-296

```python
# Column D (index 3): Ref
# If multiple allocations, suffix with letters (a, b, c, ...)
if num_allocations > 1:
    suffix = chr(ord('a') + alloc_idx)  # a, b, c, ...
    row[3] = f"{base_ref}{suffix}"
else:
    row[3] = base_ref
```

This means:
- **Single bank**: Reference = `BNG-A-02025`
- **Two banks**: Reference = `BNG-A-02025a`, `BNG-A-02025b`
- **Three banks**: Reference = `BNG-A-02025a`, `BNG-A-02025b`, `BNG-A-02025c`

---

## Units Calculation for Paired vs Non-Paired

### Code Location: `sales_quotes_csv.py` lines 419-424

```python
# Column 1: # credits
# Use effective_units if paired, otherwise units_supplied
if is_paired:
    units_value = habitat.get("effective_units", 0.0)
else:
    units_value = habitat.get("units_supplied", 0.0)
row[base_idx + 1] = f"{units_value:.4f}"
```

**Why the difference?**
- **Non-paired**: `units_supplied` is what the client needs
- **Paired**: `effective_units` already accounts for the blended allocation

---

## Admin Fee Handling

### Code Location: `sales_quotes_csv.py` lines 376-378

```python
# Column AR (index 43): Admin Fee (only on first row if multi-row)
if alloc_idx == 0:
    row[43] = f"{admin_fee:.2f}"
# else: blank for subsequent rows
```

The admin fee (£500 standard or £300 fractional) is added **only to the first row** to avoid double-counting when there are multiple banks.

---

## Complete Flow Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                    Optimizer Output                              │
│  List of allocations with:                                      │
│  - BANK_KEY, supply_habitat, allocation_type                    │
│  - units_supplied, effective_units, cost                        │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│  Group by BANK_KEY                                              │
│  (Each bank becomes ONE CSV row)                                │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│  For each bank group:                                           │
│  1. Check if ANY allocation is "paired"                        │
│  2. Determine tier (local/adjacent/far)                        │
│  3. Collect all habitats (up to 8)                             │
│  4. Calculate totals                                            │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│  Generate CSV Row:                                              │
│  - Column D: Ref (+ suffix if multiple banks)                  │
│  - Column T: SRM manual note (if paired)                       │
│  - Column AC: Bank name                                         │
│  - Column AD: Spatial Multiplier ("1" if paired, formula else) │
│  - Columns AV-CY: Up to 8 habitats                             │
└─────────────────────────────────────────────────────────────────┘
```

---

## Common Mistakes to Avoid

### ❌ WRONG: Creating separate CSV rows for each paired habitat
```python
# DON'T DO THIS
for allocation in allocations:
    create_csv_row(allocation)  # One row per habitat = WRONG
```

### ✅ CORRECT: Bundling habitats from same bank into one row
```python
# DO THIS
for bank_key, bank_group in alloc_df.groupby("BANK_KEY"):
    habitats = [h for h in bank_group.iterrows()]
    create_csv_row(bank_key, habitats)  # One row per bank = CORRECT
```

### ❌ WRONG: Using formula for paired spatial multiplier
```python
row[29] = "=4/3"  # WRONG for paired
```

### ✅ CORRECT: Using "1" for paired spatial multiplier
```python
if is_paired:
    row[29] = "1"  # CORRECT - SRM already in blended price
```

---

## Debugging Checklist

1. **Check grouping**: Print `alloc_df.groupby("BANK_KEY").groups` to verify bank grouping
2. **Check is_paired flag**: Verify `allocation_type` column has "paired" value (lowercase)
3. **Check habitat count**: Ensure each bank group has ≤8 habitats
4. **Check spatial multiplier**: Paired should show "1", non-paired should show formula
5. **Check Column T**: Paired with adjacent/far should show "SRM manual (0.x)" note
