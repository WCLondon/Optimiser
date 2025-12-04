# Paired Allocation Habitat Splitting - CRITICAL DOCUMENTATION

## ⚠️ IMPORTANT: DO NOT DIVIDE EVENLY

**VSCode Copilot's suggestion to "divide evenly" is WRONG.**

When splitting paired allocation habitats for CSV columns, you **MUST** use the `stock_use` ratios from the `paired_parts` JSON field - NOT divide by 2 or any even split.

---

## The Problem

Paired allocations store habitat names as concatenated strings:
```
"Grassland - Traditional orchards + Grassland - Other neutral grassland"
```

**WRONG approach (what VSCode Copilot suggested):**
```python
# ❌ INCORRECT - Don't do this!
habitats = supply_habitat.split(" + ")
units_per_habitat = total_units / len(habitats)  # Divides evenly - WRONG!
```

**CORRECT approach:**
```python
# ✅ CORRECT - Use paired_parts for actual ratios
import json
paired_parts = json.loads(allocation["paired_parts"])
for part in paired_parts:
    habitat_name = part["habitat"]
    stock_use_ratio = part["stock_use"]  # e.g., 0.75 or 0.25
    habitat_units = total_units * stock_use_ratio
```

---

## The `paired_parts` JSON Structure

Each paired allocation has a `paired_parts` field containing the actual split ratios:

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

### Key Fields:
| Field | Description | Example |
|-------|-------------|---------|
| `habitat` | Habitat name for this part | `"Grassland - Traditional orchards"` |
| `unit_price` | Price per unit for this habitat | `31200.0` |
| `stock_use` | **THE SPLIT RATIO** - stock consumption coefficient | `0.75` |

---

## Correct Calculation Example

**Given:**
- Total units: 1.0
- `paired_parts`: `[{habitat: "A", stock_use: 0.75}, {habitat: "B", stock_use: 0.25}]`

**Correct Split:**
| Habitat | stock_use | Units | Cost |
|---------|-----------|-------|------|
| A | 0.75 | 1.0 × 0.75 = **0.75** | 0.75 × £31,200 = £23,400 |
| B | 0.25 | 1.0 × 0.25 = **0.25** | 0.25 × £24,800 = £6,200 |

**WRONG Split (dividing evenly):**
| Habitat | Units (WRONG) |
|---------|---------------|
| A | 1.0 / 2 = 0.5 ❌ |
| B | 1.0 / 2 = 0.5 ❌ |

---

## Complete Code Example

```python
import json

def split_paired_habitats_for_csv(allocation):
    """
    Split a paired allocation into individual habitat entries for CSV.
    
    IMPORTANT: Use stock_use ratios from paired_parts, NOT even division!
    """
    paired_parts = json.loads(allocation["paired_parts"])
    total_units = allocation.get("effective_units") or allocation.get("units_supplied", 0)
    total_cost = allocation.get("cost", 0)
    
    habitat_entries = []
    for part in paired_parts:
        ratio = part["stock_use"]  # e.g., 0.75 or 0.25
        
        entry = {
            "habitat_name": part["habitat"],
            "unit_price": part["unit_price"],
            "units": total_units * ratio,
            "cost": total_cost * ratio,
            "stock_use": ratio
        }
        habitat_entries.append(entry)
    
    return habitat_entries
```

---

## Where This Applies

### In `sales_quotes_csv.py`:

When populating habitat columns (AV-CY) for paired allocations:

```python
# Line ~233-260: Habitat column population
if is_paired and paired_parts:
    parts = json.loads(paired_parts)
    for i, part in enumerate(parts):
        col_start = 47 + (i * 7)  # 7 columns per habitat slot
        
        # Use stock_use for correct proportion
        ratio = part["stock_use"]
        
        row[col_start] = part["habitat"]              # Habitat name
        row[col_start + 1] = tier                     # Tier
        row[col_start + 2] = demand_habitat           # Demand
        row[col_start + 3] = units * ratio            # Units (proportional!)
        row[col_start + 4] = part["unit_price"]       # Unit price
        row[col_start + 5] = cost * ratio             # Cost (proportional!)
        row[col_start + 6] = stock_use_value * ratio  # Stock take
```

---

## Why This Matters

The `stock_use` ratio reflects:
1. **Legal trade relationship** - How much of each habitat satisfies the BNG requirement
2. **Actual stock consumption** - How much inventory the bank loses
3. **Cost allocation** - How the blended price breaks down

A 0.75/0.25 split means the first habitat (usually higher distinctiveness) contributes 75% of the trade value, not 50%.

---

## Common Mistakes to Avoid

| Mistake | Why It's Wrong |
|---------|----------------|
| Dividing units by number of habitats | Ignores actual trade ratios |
| Splitting cost 50/50 | Each habitat has different unit prices |
| Ignoring `paired_parts` field | This is THE source of truth |
| Using `units_supplied` for split | Use `stock_use` ratios instead |

---

## Debugging Checklist

1. **Check `paired_parts` exists and is valid JSON:**
   ```python
   print(f"paired_parts: {allocation.get('paired_parts')}")
   parts = json.loads(allocation["paired_parts"])
   print(f"Parsed: {parts}")
   ```

2. **Verify `stock_use` ratios sum to 1.0:**
   ```python
   total = sum(p["stock_use"] for p in parts)
   assert abs(total - 1.0) < 0.001, f"stock_use ratios don't sum to 1: {total}"
   ```

3. **Check individual habitat values:**
   ```python
   for part in parts:
       print(f"  Habitat: {part['habitat']}")
       print(f"  stock_use: {part['stock_use']}")
       print(f"  unit_price: {part['unit_price']}")
   ```

---

## Call Flow

```
Allocation with paired_parts JSON
         │
         ▼
┌─────────────────────────────────────────────┐
│ Parse JSON to get habitat entries           │
│ paired_parts = json.loads(row["paired_parts"])
└─────────────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────────┐
│ For each habitat in paired_parts:           │
│   ratio = part["stock_use"]  # e.g., 0.75   │
│   units = total_units * ratio               │
│   cost = total_cost * ratio                 │
└─────────────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────────┐
│ Populate CSV columns AV-CY with:            │
│   Slot 1 (AV-BB): First habitat             │
│   Slot 2 (BC-BI): Second habitat            │
│   Each with proportional units/cost         │
└─────────────────────────────────────────────┘
```

---

## Summary

**THE GOLDEN RULE:** Always use `stock_use` from `paired_parts` JSON for splitting - NEVER divide evenly.

```python
# ✅ CORRECT
ratio = part["stock_use"]  # 0.75, 0.25, etc.
habitat_units = total_units * ratio

# ❌ WRONG  
habitat_units = total_units / len(habitats)  # Don't do this!
```
