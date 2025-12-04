# Extracted Optimizer Core: Multi-Ledger Bank Discovery for Hedgerows and Watercourses

This document explains how the optimizer core handles finding mitigation across different banks when hedgerow and watercourse habitats don't exist in the same bank as area habitats.

---

## Overview: Three-Ledger Architecture

The optimizer uses **three separate ledgers** to find supply options, because habitats are categorized by `UmbrellaType`:

| Ledger | UmbrellaType | Function | Line in optimizer_core.py |
|--------|--------------|----------|---------------------------|
| **Area** | (not hedgerow, not watercourse) | `prepare_options()` | 1867 |
| **Hedgerow** | `hedgerow` | `prepare_hedgerow_options()` | 2318 |
| **Watercourse** | `watercourse` | `prepare_watercourse_options()` | 721 |

**Key Insight:** Each ledger **searches ALL banks independently** for its habitat type. A bank with only area habitats will not be searched for hedgerows, and vice versa.

---

## 1. How the Optimizer Builds Options (optimizer_core.py, lines 2580-2619)

```python
# ---- Build options per ledger ----
# 1) Area (non-hedgerow, non-watercourse)
options_area, caps_area, bk_area = prepare_options(
    demand_df, chosen_size, target_lpa, target_nca,
    lpa_neigh, nca_neigh, lpa_neigh_norm, nca_neigh_norm,
    backend, promoter_discount_type, promoter_discount_value
)

# 2) Hedgerow
options_hedge, caps_hedge, bk_hedge = prepare_hedgerow_options(
    demand_df, chosen_size, target_lpa, target_nca,
    lpa_neigh, nca_neigh, lpa_neigh_norm, nca_neigh_norm,
    backend, promoter_discount_type, promoter_discount_value
)

# 3) Watercourse
options_water, caps_water, bk_water = prepare_watercourse_options(
    demand_df, chosen_size, target_lpa, target_nca,
    lpa_neigh, nca_neigh, lpa_neigh_norm, nca_neigh_norm,
    backend, promoter_discount_type, promoter_discount_value
)

# ---- Combine ledgers into one joint solve ----
options: List[dict] = []
options.extend(options_area)
options.extend(options_hedge)
options.extend(options_water)

stock_caps: Dict[str, float] = {}
stock_caps.update(caps_area)
stock_caps.update(caps_hedge)
stock_caps.update(caps_water)
```

**What This Means:**
1. Each `prepare_*_options()` function searches **ALL banks** in the database
2. Each function filters stock to only its habitat type (using `UmbrellaType`)
3. Results from all three ledgers are **combined** into a single `options` list
4. The optimizer then solves across all options simultaneously

---

## 2. Area Ledger: `prepare_options()` (lines 1867-2100)

**Filters Stock to Area Habitats Only:**
```python
# Filter to ONLY area habitats using UmbrellaType column
if "UmbrellaType" in stock_full.columns:
    stock_full = stock_full[
        (stock_full["UmbrellaType"].astype(str).str.strip().str.lower() != "hedgerow") &
        (stock_full["UmbrellaType"].astype(str).str.strip().str.lower() != "watercourse")
    ].copy()
```

**Only Processes Area Demands:**
- Skips demands where `UmbrellaType == "hedgerow"` or `UmbrellaType == "watercourse"`
- Returns empty options list for hedgerow/watercourse demands (they're handled by other functions)

---

## 3. Hedgerow Ledger: `prepare_hedgerow_options()` (lines 2318-2545)

**Filters Stock to Hedgerow Habitats Only:**
```python
# Filter to ONLY hedgerow habitats using UmbrellaType
if "UmbrellaType" in stock_full.columns:
    stock_full = stock_full[
        stock_full["UmbrellaType"].astype(str).str.strip().str.lower() == "hedgerow"
    ].copy()
else:
    # Fallback to keyword-based if UmbrellaType doesn't exist
    stock_full = stock_full[stock_full["habitat_name"].map(is_hedgerow)].copy()
```

**Only Processes Hedgerow Demands:**
```python
# Process ONLY hedgerow demands using UmbrellaType
if "UmbrellaType" in Catalog.columns:
    if dem_hab != NET_GAIN_HEDGEROW_LABEL:
        cat_match = Catalog[Catalog["habitat_name"].astype(str).str.strip() == dem_hab]
        if not cat_match.empty:
            umb = sstr(cat_match.iloc[0]["UmbrellaType"]).strip().lower()
            # Skip if not a hedgerow habitat
            if umb != "hedgerow":
                continue
```

**Hedgerow Trading Rules** (`enforce_hedgerow_rules()`, lines 576-605):
```python
def enforce_hedgerow_rules(demand_row, supply_row, dist_levels_map_local) -> bool:
    """Enforce hedgerow trading rules"""
    dh = sstr(demand_row.get("habitat_name", ""))
    sh = sstr(supply_row.get("habitat_name", ""))
    
    # Net Gain (Hedgerows) can be matched by any hedgerow
    if dh == "Net Gain (Hedgerows)":
        return is_hedgerow(sh)
    
    # For specific hedgerow demands, check distinctiveness rules
    # ...
```

---

## 4. Watercourse Ledger: `prepare_watercourse_options()` (lines 721-930)

**Filters Stock to Watercourse Habitats Only:**
```python
# Keep only watercourse habitats by UmbrellaType
wc_catalog = Catalog[Catalog["UmbrellaType"].astype(str).str.lower() == "watercourse"]
wc_habs = set(wc_catalog["habitat_name"].astype(str))

stock_full = (
    Stock[Stock["habitat_name"].isin(wc_habs)]
    .merge(Banks[["bank_id","bank_name","lpa_name","nca_name"]].drop_duplicates(),
           on="bank_id", how="left")
    ...
)
# Additional safety: exclude area habitats and hedgerows from watercourse ledger
stock_full = stock_full[~stock_full["habitat_name"].map(is_hedgerow)].copy()
```

**Only Processes Watercourse Demands:**
```python
# Only handle watercourse demands (including NG watercourses)
if "UmbrellaType" in Catalog.columns:
    if dem_hab != NET_GAIN_WATERCOURSE_LABEL:
        m = Catalog[Catalog["habitat_name"].astype(str).str.strip() == dem_hab]
        umb = sstr(m.iloc[0]["UmbrellaType"]).lower() if not m.empty else ""
        if umb != "watercourse":
            continue
```

**Watercourse Trading Rules** (`enforce_watercourse_rules()`, lines 607-700):
```python
def enforce_watercourse_rules(demand_row, supply_row, dist_levels_map_local) -> bool:
    """
    Enforce watercourse trading rules according to BNG requirements.
    
    Trading rules for watercourses:
    - Net Gain (Watercourses) can be matched by any watercourse habitat
    - Same habitat: can trade down distinctiveness (High→Medium→Low)
    - Different habitats: can only trade like-for-like or with higher distinctiveness
    - Very High watercourses require bespoke compensation
    """
```

---

## 5. What Happens When Banks Don't Have All Habitat Types

### Scenario: Demand includes Area + Hedgerow, but Bank A has only Area

```
Bank A: Grassland (area), Woodland (area)        ← No hedgerows
Bank B: Species-rich native hedgerow             ← Hedgerow only
Bank C: Rivers and streams                       ← Watercourse only
```

**Result:**
1. `prepare_options()` finds Bank A for area demands
2. `prepare_hedgerow_options()` finds Bank B for hedgerow demands
3. `prepare_watercourse_options()` finds Bank C for watercourse demands
4. Optimizer combines all options and allocates across different banks

**The allocation result will show:**
- Area habitats allocated from Bank A
- Hedgerow habitats allocated from Bank B
- Watercourse habitats allocated from Bank C

---

## 6. Error Detection: "No Legal Options"

If a ledger finds **zero options** for a demand, it raises an error:

```python
bad = [di for di, idxs in idx_by_dem.items() if len(idxs) == 0]
if bad:
    names = [sstr(demand_df.iloc[di]["habitat_name"]) for di in bad]
    error_msg = "No legal options for: " + ", ".join(names)
```

**Common Causes:**
1. **No stock in any bank** for that habitat type
2. **Habitat not in catalog** - name mismatch between demand and catalog
3. **Trading rules reject all supply** - distinctiveness requirements not met
4. **No pricing data** - habitat exists in stock but no pricing for current contract size/tier

---

## 7. Debug Information

The optimizer logs debug info when options are prepared:

```python
# Check for hedgerow/watercourse debug info from preparation functions
if hasattr(prepare_hedgerow_options, '_debug_info') and prepare_hedgerow_options._debug_info:
    debug_info.extend(prepare_hedgerow_options._debug_info)
    
if hasattr(prepare_watercourse_options, '_debug_info') and prepare_watercourse_options._debug_info:
    debug_info.extend(prepare_watercourse_options._debug_info)
```

**Debug output shows:**
- Which habitats couldn't be matched
- Sample habitats from catalog for comparison
- Number of options found per demand

---

## Complete Flow Diagram

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         DEMAND DATAFRAME                                 │
│  Contains: Area habitats, Hedgerow habitats, Watercourse habitats       │
└───────────────────────────────────┬─────────────────────────────────────┘
                                    │
        ┌───────────────────────────┼───────────────────────────┐
        │                           │                           │
        ▼                           ▼                           ▼
┌───────────────────┐   ┌───────────────────────┐   ┌───────────────────────┐
│  prepare_options  │   │ prepare_hedgerow_     │   │ prepare_watercourse_  │
│       (Area)      │   │      options          │   │       options         │
├───────────────────┤   ├───────────────────────┤   ├───────────────────────┤
│ Filters to:       │   │ Filters to:           │   │ Filters to:           │
│ UmbrellaType !=   │   │ UmbrellaType =        │   │ UmbrellaType =        │
│ "hedgerow" AND    │   │ "hedgerow"            │   │ "watercourse"         │
│ != "watercourse"  │   │                       │   │                       │
├───────────────────┤   ├───────────────────────┤   ├───────────────────────┤
│ Searches:         │   │ Searches:             │   │ Searches:             │
│ ALL BANKS that    │   │ ALL BANKS that have   │   │ ALL BANKS that have   │
│ have area stock   │   │ hedgerow stock        │   │ watercourse stock     │
├───────────────────┤   ├───────────────────────┤   ├───────────────────────┤
│ Uses:             │   │ Uses:                 │   │ Uses:                 │
│ enforce_supply_   │   │ enforce_hedgerow_     │   │ enforce_watercourse_  │
│ rules()           │   │ rules()               │   │ rules()               │
└─────────┬─────────┘   └──────────┬────────────┘   └──────────┬────────────┘
          │                        │                           │
          │    options_area        │    options_hedge          │    options_water
          │                        │                           │
          └────────────────────────┼───────────────────────────┘
                                   │
                                   ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                         COMBINED OPTIONS                                 │
│  options = options_area + options_hedge + options_water                  │
│  stock_caps = caps_area ∪ caps_hedge ∪ caps_water                        │
└───────────────────────────────────┬─────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                       LP SOLVER (PuLP/CBC)                               │
│  Minimizes total cost while respecting:                                  │
│    - Demand requirements (must fulfill each demand)                      │
│    - Stock capacities (can't exceed available units per bank)            │
│    - Cross-ledger independence (area/hedge/water handled separately)     │
└───────────────────────────────────┬─────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                         ALLOCATION RESULT                                │
│  Bank A: Area habitat X - 5 units                                        │
│  Bank B: Hedgerow habitat Y - 2 units                                    │
│  Bank C: Watercourse habitat Z - 3 units                                 │
│  (Different banks can provide different habitat types)                   │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## 8. Key Points for Copilot

### ✅ Correct Understanding:
1. **Each ledger searches ALL banks independently** - not just the banks used for area habitats
2. **Banks are not shared across ledgers** - a bank's hedgerow stock is only visible to `prepare_hedgerow_options()`
3. **Final allocation can span multiple banks** - area from Bank A, hedgerow from Bank B, watercourse from Bank C

### ❌ Common Misconceptions:
1. ❌ "Hedgerows must come from the same bank as area habitats" - **FALSE**
2. ❌ "If a bank has no hedgerow stock, hedgerow demand fails" - **FALSE** (other banks searched)
3. ❌ "Area and hedgerow options are mixed together" - **FALSE** (separate ledgers)

### Why Hedgerows/Watercourses Might Be "Ignored":
If hedgerow or watercourse demands are being ignored, check:
1. **Stock Table**: Does any bank have hedgerow/watercourse stock with `UmbrellaType = "hedgerow"` or `"watercourse"`?
2. **Pricing Table**: Is there pricing for hedgerow/watercourse habitats at the current contract size?
3. **Habitat Catalog**: Does the demand habitat name match exactly with catalog entries?
4. **Trading Rules**: Do the distinctiveness requirements allow the available supply?

---

## 9. Summary

| Component | Purpose | Searches |
|-----------|---------|----------|
| `prepare_options()` | Area habitats | All banks with area stock |
| `prepare_hedgerow_options()` | Hedgerow habitats | All banks with hedgerow stock |
| `prepare_watercourse_options()` | Watercourse habitats | All banks with watercourse stock |

**The optimizer DOES search different banks for hedgerows and watercourses.** If mitigation isn't being found, the issue is likely:
- Missing stock data in the database
- Missing pricing data for the habitat/contract_size/tier combination
- Habitat name mismatch between demand and catalog
- Trading rules rejecting available supply due to distinctiveness requirements
