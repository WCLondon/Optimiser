# Paired Allocations in Client Report Table: Display Logic

This document explains how paired allocations should be displayed in the client report table (email) and why they may sometimes incorrectly show combined habitat names.

---

## The Problem

Paired allocations are showing combined habitat names in the "Habitats Supplied" column:

**Incorrect:**
```
Habitats Supplied: Grassland - Traditional orchards + Grassland - Other neutral grassland
```

**Correct:**
```
Habitats Supplied: Grassland - Traditional orchards
```

The "Habitats Supplied" column should show **only the main legal trade habitat** (the one with the highest distinctiveness), not the combined pair.

---

## How the Code SHOULD Handle This

### Location: `generate_client_report_table_fixed()` (lines 4774-4835)

```python
# For paired allocations, show only the highest distinctiveness habitat
allocation_type = sstr(alloc_row.get("allocation_type", "normal"))
if allocation_type == "paired" and "paired_parts" in alloc_row and alloc_row["paired_parts"]:
    try:
        paired_parts = json.loads(sstr(alloc_row["paired_parts"]))
        if paired_parts and len(paired_parts) >= 2:
            # Get distinctiveness for each habitat in the pair
            habitat_distinctiveness = []
            for idx, part in enumerate(paired_parts):
                habitat = sstr(part.get("habitat", ""))
                cat_match = backend["HabitatCatalog"][backend["HabitatCatalog"]["habitat_name"] == habitat]
                if not cat_match.empty:
                    dist_name = cat_match["distinctiveness_name"].iloc[0]
                    dist_value = dist_levels_map.get(dist_name, dist_levels_map.get(dist_name.lower(), 0))
                    habitat_distinctiveness.append({
                        "habitat": habitat,
                        "distinctiveness_name": dist_name,
                        "distinctiveness_value": dist_value,
                        "index": idx  # Track original index to prefer demand habitat in ties
                    })
            
            # Select the habitat with highest distinctiveness value
            # In case of tie, prefer the demand habitat (index 0)
            if habitat_distinctiveness:
                highest_dist = max(habitat_distinctiveness, key=lambda x: (x["distinctiveness_value"], -x["index"]))
                supply_habitat = highest_dist["habitat"]  # <-- THIS replaces the combined name
                supply_distinctiveness = highest_dist["distinctiveness_name"]
```

### The Logic:
1. Check if `allocation_type == "paired"`
2. Check if `paired_parts` exists and is not empty
3. Parse `paired_parts` JSON to get individual habitats
4. Look up distinctiveness for each habitat in the pair
5. Select the habitat with the **highest distinctiveness value**
6. In case of tie, prefer the **demand habitat (index 0)**
7. **Replace `supply_habitat`** with just that single habitat name

---

## Why This Logic Might Not Be Working

### Issue 1: `paired_parts` is Missing or Empty

If the allocation row doesn't have a `paired_parts` field, the code falls back to showing `supply_habitat` directly:

```python
# Line 4759 - supply_habitat is set to the combined name
supply_habitat = alloc_row["supply_habitat"]
# e.g., "Grassland - Traditional orchards + Grassland - Other neutral grassland"

# If paired_parts check fails, this combined name is displayed
```

**Check:** Ensure allocations have `paired_parts` populated:
```python
print(alloc_row.get("paired_parts"))
# Should be: '[{"habitat": "Grassland - Traditional orchards", ...}, {"habitat": "Grassland - Other neutral grassland", ...}]'
# NOT: None or ""
```

### Issue 2: `paired_parts` is Not Valid JSON

If `paired_parts` contains invalid JSON, the `try/except` block falls through:

```python
except Exception:
    # If paired_parts parsing fails, fallback to default lookup
    supply_cat_match = backend["HabitatCatalog"][backend["HabitatCatalog"]["habitat_name"] == supply_habitat]
```

**Check:** Validate the JSON format:
```python
import json
try:
    parts = json.loads(alloc_row["paired_parts"])
    print("Valid JSON:", parts)
except:
    print("INVALID JSON:", alloc_row["paired_parts"])
```

### Issue 3: Habitat Not Found in Catalog

If habitats in `paired_parts` don't match entries in `backend["HabitatCatalog"]`, the lookup fails:

```python
cat_match = backend["HabitatCatalog"][backend["HabitatCatalog"]["habitat_name"] == habitat]
if not cat_match.empty:  # This might be empty!
```

**Check:** Verify habitat names match exactly:
```python
parts = json.loads(alloc_row["paired_parts"])
for part in parts:
    hab = part.get("habitat")
    matches = backend["HabitatCatalog"][backend["HabitatCatalog"]["habitat_name"] == hab]
    if matches.empty:
        print(f"NOT FOUND IN CATALOG: '{hab}'")
    else:
        print(f"Found: '{hab}' -> {matches['distinctiveness_name'].iloc[0]}")
```

### Issue 4: `allocation_type` is Not "paired"

If the allocation type is something else (e.g., "normal", missing, or has different capitalization):

```python
allocation_type = sstr(alloc_row.get("allocation_type", "normal"))
if allocation_type == "paired":  # This comparison might fail
```

**Check:** Verify the allocation type:
```python
print(f"allocation_type: '{alloc_row.get('allocation_type')}'")
# Should be exactly "paired", not "Paired" or "PAIRED"
```

---

## The Correct `paired_parts` JSON Structure

For the display logic to work, `paired_parts` must be a valid JSON array with this structure:

```json
[
    {
        "habitat": "Grassland - Traditional orchards",
        "unit_price": 31200.0,
        "stock_use": 0.75
    },
    {
        "habitat": "Grassland - Other neutral grassland",
        "unit_price": 24800.0,
        "stock_use": 0.25
    }
]
```

**Key fields used by display logic:**
- `habitat` (required) - The individual habitat name
- `unit_price` (used elsewhere for pricing)
- `stock_use` (used elsewhere for stock allocation)

---

## Complete Flow Diagram

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    ALLOCATION FROM OPTIMIZER                             │
│                                                                          │
│  {                                                                       │
│    "allocation_type": "paired",                                         │
│    "supply_habitat": "Trad orchards + Other neutral grassland",         │
│    "paired_parts": '[{"habitat": "Trad orchards", ...}, ...]'           │
│  }                                                                       │
└───────────────────────────────────┬─────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│            GENERATE_CLIENT_REPORT_TABLE_FIXED() (line 4774)             │
│                                                                          │
│  1. Check: allocation_type == "paired"? → YES                           │
│  2. Check: paired_parts exists? → YES                                    │
│  3. Parse: json.loads(paired_parts) → 2 habitats                        │
│  4. Lookup distinctiveness for each:                                     │
│     - "Trad orchards": High (3)                                         │
│     - "Other neutral grassland": Medium (2)                             │
│  5. Pick highest: "Trad orchards" (High = 3)                            │
│  6. REPLACE supply_habitat → "Trad orchards"                            │
└───────────────────────────────────┬─────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                    CLIENT REPORT TABLE (HTML)                            │
│                                                                          │
│  Habitats Supplied: Grassland - Traditional orchards ✓                  │
│  (NOT: "Trad orchards + Other neutral grassland")                       │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## Debugging Checklist

### Step 1: Check Allocation Data
```python
for idx, row in alloc_df.iterrows():
    if row.get("allocation_type") == "paired":
        print(f"Row {idx}:")
        print(f"  supply_habitat: {row.get('supply_habitat')}")
        print(f"  allocation_type: {row.get('allocation_type')}")
        print(f"  paired_parts: {row.get('paired_parts')}")
        print()
```

### Step 2: Verify paired_parts Structure
```python
import json
for idx, row in alloc_df.iterrows():
    if row.get("allocation_type") == "paired":
        pp = row.get("paired_parts")
        try:
            parts = json.loads(pp)
            print(f"Row {idx} - Valid JSON with {len(parts)} parts:")
            for p in parts:
                print(f"  - {p.get('habitat')}")
        except Exception as e:
            print(f"Row {idx} - INVALID: {e}")
            print(f"  Raw value: {pp}")
```

### Step 3: Check Catalog Matching
```python
import json
Catalog = backend["HabitatCatalog"]
for idx, row in alloc_df.iterrows():
    if row.get("allocation_type") == "paired":
        pp = row.get("paired_parts")
        parts = json.loads(pp) if pp else []
        for p in parts:
            hab = p.get("habitat", "")
            match = Catalog[Catalog["habitat_name"] == hab]
            if match.empty:
                print(f"NOT FOUND: '{hab}'")
            else:
                print(f"FOUND: '{hab}' -> {match['distinctiveness_name'].iloc[0]}")
```

---

## If the Logic is Correct but Still Failing

If all the checks pass but the combined name still appears, the issue is likely:

1. **Code path not being hit** - The allocation might be processed through a different code path
2. **Data being overwritten** - Something downstream might be resetting `supply_habitat`
3. **Different function being used** - There might be multiple report generation functions

### Search for all usages:
```bash
grep -n "Habitats Supplied" app.py
```

This will show all places where the column is set, to ensure the paired allocation logic is applied everywhere.

---

## Summary

| Check | What to Look For | Fix If Needed |
|-------|------------------|---------------|
| `allocation_type` | Must be exactly `"paired"` | Ensure optimizer sets this |
| `paired_parts` | Must exist and be valid JSON | Ensure optimizer populates this |
| `paired_parts[].habitat` | Must match catalog entries exactly | Fix name mismatches |
| Catalog lookup | Must find distinctiveness | Add missing habitats to catalog |
| Code path | Must hit lines 4774-4799 | Add logging to verify |
