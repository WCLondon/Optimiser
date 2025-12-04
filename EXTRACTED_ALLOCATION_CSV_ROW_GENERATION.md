# Allocation CSV Row Generation

**Purpose:** This document explains exactly how the optimizer generates CSV rows for the Sales & Quotes Excel workbook. VSCode Copilot should use this as the authoritative reference for CSV generation.

---

## Overview

The `sales_quotes_csv.py` module converts optimizer allocation results into CSV data rows aligned with the Sales & Quotes Excel workbook column structure (A-CY, 103 columns total).

**Key principle:** ONE allocation = ONE CSV row. For multi-bank allocations, each bank gets its own row with a letter suffix (a, b, c...).

---

## Critical CSV Column Mapping

```
Column A  (index 0):  blank
Column B  (index 1):  Client Name
Column C  (index 2):  Development Address (commas replaced with semicolons)
Column D  (index 3):  Reference Number (with letter suffix if multi-bank)
Columns E-S (4-18):   blank
Column T  (index 19): Notes / SRM manual
Columns U-AB (20-27): blank
Column AC (index 28): Habitat Bank / Source of Mitigation (format: "WC1P2 - Nunthorpe")
Column AD (index 29): Spatial Multiplier ("1" for paired, "=4/3" or "=2/1" for normal)
Column AE (index 30): Total Units (4 decimal places)
Column AF (index 31): Contract Value (first row includes admin fee)
Column AG (index 32): blank
Column AH (index 33): Local Planning Authority
Column AI (index 34): National Character Area
Column AJ (index 35): blank
Column AK (index 36): Introducer (or "Direct")
Column AL (index 37): Quote Date (DD/MM/YYYY)
Column AM (index 38): Quote Period ("30")
Column AN (index 39): Quote Expiry (formula: =AL{row}+AM{row})
Columns AO-AQ (40-42): blank
Column AR (index 43): Admin Fee (first row only, £500 or £300 for fractional)
Column AS (index 44): blank
Column AT (index 45): Total Credit Price
Column AU (index 46): Total Units (duplicate)
Column AV onwards:    Habitat data (8 habitats max, 7 columns each)
```

---

## Habitat Columns (8 habitats × 7 columns each)

Starting at Column AV (index 47), each habitat uses 7 columns:

```python
# For each habitat (hab_idx = 0 to 7):
base_idx = 47 + (hab_idx * 7)

row[base_idx + 0] = habitat["type"]              # Habitat type name
row[base_idx + 1] = units_value                   # # credits (4 decimal places)
row[base_idx + 2] = st                            # Stock Take = SM × credits (4 decimal places)
row[base_idx + 3] = ""                            # blank
row[base_idx + 4] = quoted_price                  # Quoted Price (2 decimal places)
row[base_idx + 5] = ""                            # blank
row[base_idx + 6] = habitat_total_cost            # Price inc SRM = ST × Quoted Price
```

**Habitat column ranges:**
- Habitat 1: AV-BB (indices 47-53)
- Habitat 2: BC-BI (indices 54-60)
- Habitat 3: BJ-BP (indices 61-67)
- Habitat 4: BQ-BW (indices 68-74)
- Habitat 5: BX-CD (indices 75-81)
- Habitat 6: CE-CK (indices 82-88)
- Habitat 7: CL-CR (indices 89-95)
- Habitat 8: CS-CY (indices 96-102)

---

## The Core CSV Generation Function

```python
def generate_sales_quotes_csv(
    quote_number: str,
    client_name: str,
    development_address: str,
    base_ref: str,
    introducer: Optional[str],
    today_date: datetime,
    local_planning_authority: str,
    national_character_area: str,
    allocations: List[Dict[str, Any]],
    contract_size: str = "small"
) -> str:
```

### Expected Allocation Structure

Each allocation dict must have:

```python
allocation = {
    "bank_ref": "WC1P2",              # Bank reference from BANK_KEY
    "bank_name": "Nunthorpe",          # Bank display name
    "is_paired": False,                # Boolean - true if paired allocation
    "spatial_relation": "adjacent",    # "local", "adjacent", or "far"
    "spatial_multiplier_numeric": 1.333, # Numeric: 1.0, 1.333, or 2.0
    "allocation_total_credits": 0.5,   # Total credits for this bank
    "contract_value_gbp": 12500.00,    # Contract value for this allocation
    "habitats": [                      # List (max 8) of habitat dicts
        {
            "type": "Grassland - Other neutral grassland",
            "units_supplied": 0.5,
            "effective_units": 0.5,
            "avg_effective_unit_price": 25000.00
        }
    ]
}
```

---

## Spatial Multiplier (SRM) Logic

### For Normal (Non-Paired) Allocations

```python
# Column AD: Spatial Multiplier formula
if spatial_relation == "adjacent":
    row[29] = "=4/3"
elif spatial_relation == "far":
    row[29] = "=2/1"
else:  # local
    row[29] = "1"

# Calculate Stock Take (ST)
sm_numeric = spatial_multiplier_numeric  # 1.0, 1.333, or 2.0
st = sm_numeric * units_supplied

# Calculate Price inc SRM
habitat_total_cost = st * quoted_price
```

### For Paired Allocations

```python
# Column AD: Always 1 (SRM is baked into blended price)
row[29] = "1"

# Column T: SRM manual note
if spatial_relation == "far":
    row[19] = "SRM manual (0.5)"
elif spatial_relation == "adjacent":
    row[19] = "SRM manual (0.75)"

# For paired, use effective_units instead of units_supplied
units_value = habitat.get("effective_units", 0.0)
st = 1.0 * units_value  # SM is 1 for paired
habitat_total_cost = st * quoted_price
```

---

## Bank Name Standardization (Column AC)

```python
def get_standardized_bank_name(bank_key: str, bank_name: str) -> Tuple[str, str, str]:
    """
    Get standardized bank name format from Banks table in database.
    Format: first 5 chars of bank_id + " - " + BANK_KEY
    
    Returns:
        Tuple of (standardized_bank_name, notes_for_column_S, source_display)
    """
    # Look up bank_id from database using BANK_KEY
    bank_id = get_bank_id_from_database(bank_key)
    
    if bank_id:
        bank_id_short = bank_id[:5]  # e.g., "WC1P2"
        return bank_key, "", f"{bank_id_short} - {bank_key}"
    else:
        # Not found - use 'Other'
        return "Other", bank_key, f"{bank_key[:5]} - Other"
```

**Example outputs:**
- `"WC1P2 - Nunthorpe"`
- `"WC1P6 - Central Bedfordshire"`
- `"WC1P5 - Bedford"`

---

## Reference Number Suffixes (Column D)

```python
# If multiple allocations (multi-bank), suffix with letters
if num_allocations > 1:
    suffix = chr(ord('a') + alloc_idx)  # a, b, c, ...
    row[3] = f"{base_ref}{suffix}"     # e.g., "BNG01640a"
else:
    row[3] = base_ref                   # e.g., "BNG01640"
```

---

## Admin Fee Handling (Column AR, Column AF)

```python
def get_admin_fee_for_contract_size(contract_size: str) -> float:
    if str(contract_size).lower().strip() == "fractional":
        return 300.0   # ADMIN_FEE_FRACTIONAL_GBP
    return 500.0       # ADMIN_FEE_GBP

# Admin fee only on first row
if alloc_idx == 0:
    row[43] = f"{admin_fee:.2f}"         # Column AR
    contract_value = total_credit_price + admin_fee  # Column AF includes fee
else:
    row[43] = ""                          # No admin fee
    contract_value = total_credit_price   # Column AF without fee
```

---

## Complete Row Generation Example

```python
# Example: Single allocation, local tier, one habitat
allocation = {
    "bank_ref": "WC1P2",
    "bank_name": "Nunthorpe",
    "is_paired": False,
    "spatial_relation": "local",
    "spatial_multiplier_numeric": 1.0,
    "allocation_total_credits": 0.5,
    "contract_value_gbp": 12500.00,
    "habitats": [{
        "type": "Grassland - Other neutral grassland",
        "units_supplied": 0.5,
        "effective_units": 0.5,
        "avg_effective_unit_price": 25000.00
    }]
}

# Generated CSV row (key columns):
row[1] = "David Evans"                      # Client
row[2] = "123 High Street; London"          # Address (semicolons)
row[3] = "BNG01640"                          # Ref
row[19] = ""                                 # Notes (blank for non-paired local)
row[28] = "WC1P2 - Nunthorpe"               # Habitat Bank
row[29] = "1"                                # Spatial Multiplier (local = 1)
row[30] = "0.5000"                           # Total Units
row[31] = "13000.00"                         # Contract Value (12500 + 500 admin)
row[33] = "Redcar and Cleveland"             # LPA
row[34] = "Tees Lowlands"                    # NCA
row[36] = "Direct"                           # Introducer
row[37] = "04/12/2025"                       # Quote Date
row[38] = "30"                               # Quote Period
row[43] = "500.00"                           # Admin Fee
row[45] = "12500.00"                         # Total Credit Price
row[46] = "0.5000"                           # Total Units

# Habitat 1 columns (AV-BB, indices 47-53):
row[47] = "Grassland - Other neutral grassland"  # Type
row[48] = "0.5000"                               # # credits
row[49] = "0.5000"                               # ST (1.0 × 0.5)
row[50] = ""                                     # blank
row[51] = "25000.00"                             # Quoted Price
row[52] = ""                                     # blank
row[53] = "12500.00"                             # Price inc SRM (0.5 × 25000)
```

---

## Converting from Optimizer DataFrame

```python
def generate_sales_quotes_csv_from_optimizer_output(
    quote_number: str,
    client_name: str,
    development_address: str,
    base_ref: str,
    introducer: Optional[str],
    today_date: datetime,
    local_planning_authority: str,
    national_character_area: str,
    alloc_df: pd.DataFrame,        # site_hab_totals DataFrame
    contract_size: str = "small"
) -> str:
```

### Expected DataFrame Columns

```python
alloc_df.columns = [
    "BANK_KEY",                 # Bank reference (e.g., "Nunthorpe")
    "bank_name",                # Bank name
    "supply_habitat",           # Habitat type (already split for paired)
    "tier",                     # "local", "adjacent", or "far"
    "allocation_type",          # "paired" or "normal"
    "units_supplied",           # Units for this specific habitat
    "effective_units",          # Effective units (with SRM)
    "avg_effective_unit_price", # Average effective unit price
    "cost"                      # Total cost for this habitat
]
```

### Conversion Logic

```python
# Group by bank
for bank_key, bank_group in alloc_df.groupby("BANK_KEY"):
    bank_name = bank_group["bank_name"].iloc[0]
    
    # Determine if paired
    is_paired = any(str(t).lower() == "paired" for t in bank_group["allocation_type"])
    
    # Get tier and calculate spatial multiplier
    tier = str(bank_group["tier"].iloc[0]).lower()
    if tier == "local":
        spatial_multiplier_numeric = 1.0
    elif tier == "adjacent":
        spatial_multiplier_numeric = 4.0 / 3.0
    else:  # far
        spatial_multiplier_numeric = 2.0
    
    # Aggregate habitats for this bank
    habitats = []
    for _, row in bank_group.iterrows():
        habitats.append({
            "type": row["supply_habitat"],
            "units_supplied": float(row["units_supplied"]),
            "effective_units": float(row.get("effective_units", row["units_supplied"])),
            "avg_effective_unit_price": float(row["avg_effective_unit_price"])
        })
    
    allocations.append({
        "bank_ref": str(bank_key),
        "bank_name": bank_name,
        "is_paired": is_paired,
        "spatial_relation": tier,
        "spatial_multiplier_numeric": spatial_multiplier_numeric,
        "allocation_total_credits": sum(h["effective_units"] for h in habitats),
        "contract_value_gbp": bank_group["cost"].sum(),
        "habitats": habitats[:8]  # Max 8 habitats
    })
```

---

## Common Mistakes to Avoid

### ❌ WRONG: Double-applying SRM for paired allocations
```python
# Don't do this for paired:
st = spatial_multiplier_numeric * units_supplied  # WRONG!
```

### ✅ CORRECT: Use 1.0 for paired allocations
```python
if is_paired:
    sm_numeric = 1.0  # SRM already in blended price
    units_value = habitat.get("effective_units", 0.0)
else:
    sm_numeric = spatial_multiplier_numeric
    units_value = habitat.get("units_supplied", 0.0)

st = sm_numeric * units_value
```

### ❌ WRONG: Using Excel formula for paired allocations
```python
# Don't do this for paired:
row[29] = "=4/3"  # WRONG!
```

### ✅ CORRECT: Use "1" for paired allocations
```python
if is_paired:
    row[29] = "1"
```

### ❌ WRONG: Missing SRM manual note for paired allocations
```python
# Paired allocations MUST have SRM manual note in Column T
```

### ✅ CORRECT: Add SRM manual note
```python
if is_paired:
    if spatial_relation == "far":
        row[19] = "SRM manual (0.5)"
    elif spatial_relation == "adjacent":
        row[19] = "SRM manual (0.75)"
```

---

## Debugging Checklist

1. **Check column indices** - Remember row is 0-indexed, CSV columns A=0, B=1, etc.
2. **Check decimal places** - Units: 4 places, Prices: 2 places
3. **Check bank name format** - Must be "WC1P2 - Nunthorpe" format
4. **Check paired logic** - `is_paired` must trigger correct SM and notes
5. **Check admin fee** - Only on first row (`alloc_idx == 0`)
6. **Check reference suffix** - Letters only if `num_allocations > 1`
7. **Check CSV escaping** - Fields with commas must be quoted

---

## Full Code Reference

See: `/home/runner/work/Optimiser/Optimiser/sales_quotes_csv.py`

- Lines 168-455: `generate_sales_quotes_csv()` - Main CSV generation function
- Lines 458-601: `generate_sales_quotes_csv_from_optimizer_output()` - DataFrame converter
- Lines 74-103: `get_standardized_bank_name()` - Bank name formatting
- Lines 23-55: `get_bank_id_from_database()` - Database lookup for bank_id
