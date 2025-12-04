# LPA/NCA-Based Quote Selection - Code Documentation

This document explains how the Optimiser repository allows users to run quotes by selecting an LPA (Local Planning Authority) and/or NCA (National Character Area), and how this affects bank pricing tiers.

## Overview

The system provides **two methods** for specifying a development site location:

1. **Option A: LPA/NCA Dropdown Selection** - User selects from a list (for promoters)
2. **Option B: Postcode/Address Lookup** - User enters a location (standard flow)

Both methods ultimately populate the same session state variables that drive pricing tier calculations.

---

## Key Session State Variables

```python
# Core location identifiers
st.session_state["target_lpa_name"]     # e.g., "Bedford"
st.session_state["target_nca_name"]     # e.g., "Bedfordshire and Cambridgeshire Claylands"

# Neighbor lists for adjacent tier calculation
st.session_state["lpa_neighbors"]       # e.g., ["Central Bedfordshire", "Milton Keynes"]
st.session_state["nca_neighbors"]       # e.g., ["The Fens", "South Suffolk and North Essex Clayland"]
st.session_state["lpa_neighbors_norm"]  # Normalized versions for matching
st.session_state["nca_neighbors_norm"]  # Normalized versions for matching

# Geometry for map display
st.session_state["lpa_geojson"]         # GeoJSON polygon for LPA boundary
st.session_state["nca_geojson"]         # GeoJSON polygon for NCA boundary

# Mode indicator
st.session_state["use_lpa_nca_dropdown"]  # True if using dropdown, False if using postcode
```

---

## Method A: LPA/NCA Dropdown Selection (app.py lines 2015-2160)

### Step 1: Fetch All LPAs/NCAs from ArcGIS

```python
# app.py lines 1472-1513
def fetch_all_lpas_from_arcgis() -> List[str]:
    """
    Fetch all unique LPA names from the ArcGIS LPA layer.
    Uses returnDistinctValues=true to get unique names.
    """
    params = {
        "f": "json",
        "where": "1=1",
        "outFields": "LAD24NM",
        "returnDistinctValues": "true",
        "returnGeometry": "false"
    }
    r = http_get(f"{LPA_URL}/query", params=params)
    features = r.json().get("features", [])
    lpas = [sstr((f.get("attributes") or {}).get("LAD24NM")) for f in features]
    return sorted({lpa for lpa in lpas if lpa})

def fetch_all_ncas_from_arcgis() -> List[str]:
    """Same pattern for NCAs, using NCA_Name field"""
    params = {
        "f": "json",
        "where": "1=1",
        "outFields": "NCA_Name",
        "returnDistinctValues": "true",
        "returnGeometry": "false"
    }
    r = http_get(f"{NCA_URL}/query", params=params)
    features = r.json().get("features", [])
    ncas = [sstr((f.get("attributes") or {}).get("NCA_Name")) for f in features]
    return sorted({nca for nca in ncas if nca})
```

### Step 2: Display Dropdown UI

```python
# app.py lines 2019-2086
st.markdown("**Option A: Select LPA/NCA directly (for promoters)**")
col_dropdown1, col_dropdown2 = st.columns(2)

# Cache LPA/NCA lists in session state
if st.session_state["all_lpas_list"] is None:
    st.session_state["all_lpas_list"] = fetch_all_lpas_from_arcgis()

if st.session_state["all_ncas_list"] is None:
    st.session_state["all_ncas_list"] = fetch_all_ncas_from_arcgis()

# Add custom option for typing your own
lpa_options = [""] + all_lpas + ["⌨️ Custom - Type your own"]
nca_options = [""] + all_ncas + ["⌨️ Custom - Type your own"]

with col_dropdown1:
    selected_lpa = st.selectbox("Select LPA", options=lpa_options)
    
with col_dropdown2:
    selected_nca = st.selectbox("Select NCA", options=nca_options)
```

### Step 3: Apply LPA/NCA Selection Button

```python
# app.py lines 2088-2160
if st.button("Apply LPA/NCA Selection", key="apply_lpa_nca_btn"):
    # Query LPA geometry and neighbors
    if st.session_state.get("selected_lpa_dropdown"):
        lpa_name = st.session_state["selected_lpa_dropdown"]
        st.session_state["target_lpa_name"] = lpa_name
        lpa_data = query_lpa_by_name(lpa_name)
    
    # Query NCA geometry and neighbors  
    if st.session_state.get("selected_nca_dropdown"):
        nca_name = st.session_state["selected_nca_dropdown"]
        st.session_state["target_nca_name"] = nca_name
        nca_data = query_nca_by_name(nca_name)
    
    # Update session state with geometries and neighbors
    st.session_state["lpa_geojson"] = lpa_data.get("geometry")
    st.session_state["lpa_neighbors"] = lpa_data.get("neighbors", [])
    st.session_state["lpa_neighbors_norm"] = lpa_data.get("neighbors_norm", [])
    
    st.session_state["nca_geojson"] = nca_data.get("geometry")
    st.session_state["nca_neighbors"] = nca_data.get("neighbors", [])
    st.session_state["nca_neighbors_norm"] = nca_data.get("neighbors_norm", [])
```

### Step 4: Query LPA/NCA by Name (Get Geometry + Neighbors)

```python
# app.py lines 1516-1600
def query_lpa_by_name(lpa_name: str) -> Dict[str, Any]:
    """
    Query LPA geometry and neighbors by name.
    """
    params = {
        "f": "json",
        "where": f"LAD24NM = '{lpa_name}'",
        "outFields": "LAD24NM",
        "returnGeometry": "true"
    }
    r = http_get(f"{LPA_URL}/query", params=params)
    feat = r.json()["features"][0]
    
    lpa_geom_esri = feat.get("geometry")
    lpa_gj = esri_polygon_to_geojson(lpa_geom_esri)
    
    # Find adjacent LPAs using spatial intersection
    lpa_nei = [n for n in layer_intersect_names(LPA_URL, lpa_geom_esri, "LAD24NM") 
               if n != lpa_name]
    lpa_nei_norm = [norm_name(n) for n in lpa_nei]
    
    return {
        "geometry": lpa_gj,
        "geometry_esri": lpa_geom_esri,
        "neighbors": lpa_nei,
        "neighbors_norm": lpa_nei_norm
    }

def query_nca_by_name(nca_name: str) -> Dict[str, Any]:
    """Same pattern for NCAs"""
    # ... similar implementation ...
```

---

## Method B: Postcode/Address Lookup (app.py lines 2165-2230)

```python
# app.py lines 2173-2220
def find_site(postcode: str = None, address: str = None):
    """
    Look up site location via postcode or address.
    Uses Nominatim for geocoding, then queries ArcGIS for LPA/NCA.
    """
    # Geocode to lat/lon
    lat, lon = geocode(postcode or address)
    
    # Query ArcGIS for LPA and NCA at this point
    lpa_feat = arcgis_point_query(LPA_URL, lat, lon, "LAD24NM")
    nca_feat = arcgis_point_query(NCA_URL, lat, lon, "NCA_Name")
    
    t_lpa = sstr((lpa_feat.get("attributes") or {}).get("LAD24NM"))
    t_nca = sstr((nca_feat.get("attributes") or {}).get("NCA_Name"))
    
    lpa_geom_esri = lpa_feat.get("geometry")
    nca_geom_esri = nca_feat.get("geometry")
    
    # Get adjacent LPAs/NCAs via spatial intersection
    lpa_nei = [n for n in layer_intersect_names(LPA_URL, lpa_geom_esri, "LAD24NM") 
               if n != t_lpa]
    nca_nei = [n for n in layer_intersect_names(NCA_URL, nca_geom_esri, "NCA_Name") 
               if n != t_nca]
    
    # Store in session state
    st.session_state["target_lpa_name"] = t_lpa
    st.session_state["target_nca_name"] = t_nca
    st.session_state["lpa_neighbors"] = lpa_nei
    st.session_state["nca_neighbors"] = nca_nei
    st.session_state["lpa_neighbors_norm"] = [norm_name(n) for n in lpa_nei]
    st.session_state["nca_neighbors_norm"] = [norm_name(n) for n in nca_nei]
    st.session_state["lpa_geojson"] = esri_polygon_to_geojson(lpa_geom_esri)
    st.session_state["nca_geojson"] = esri_polygon_to_geojson(nca_geom_esri)
    
    # Mark that we're NOT using dropdown mode
    st.session_state["use_lpa_nca_dropdown"] = False
    
    return t_lpa, t_nca
```

---

## How LPA/NCA Affects Pricing Tiers

### The `tier_for_bank()` Function (app.py lines 1717-1745)

This is the **core function** that determines pricing tier based on LPA/NCA matching:

```python
def tier_for_bank(bank_lpa: str, bank_nca: str,
                  t_lpa: str, t_nca: str,
                  lpa_neigh: List[str], nca_neigh: List[str],
                  lpa_neigh_norm: Optional[List[str]] = None,
                  nca_neigh_norm: Optional[List[str]] = None) -> str:
    """
    Determine pricing tier for a bank relative to target site.
    
    Returns: "local", "adjacent", or "far"
    """
    b_lpa = norm_name(bank_lpa)
    b_nca = norm_name(bank_nca)
    t_lpa_n = norm_name(t_lpa)
    t_nca_n = norm_name(t_nca)
    
    if lpa_neigh_norm is None:
        lpa_neigh_norm = [norm_name(x) for x in (lpa_neigh or [])]
    if nca_neigh_norm is None:
        nca_neigh_norm = [norm_name(x) for x in (nca_neigh or [])]
    
    # Evaluate LPA axis independently
    lpa_same = b_lpa and t_lpa_n and b_lpa == t_lpa_n
    lpa_neighbour = b_lpa and b_lpa in lpa_neigh_norm
    
    # Evaluate NCA axis independently  
    nca_same = b_nca and t_nca_n and b_nca == t_nca_n
    nca_neighbour = b_nca and b_nca in nca_neigh_norm
    
    # Return best (closest) category across both axes
    if lpa_same or nca_same:
        return "local"      # SRM = 1.0
    elif lpa_neighbour or nca_neighbour:
        return "adjacent"   # SRM = 4/3 ≈ 1.33
    else:
        return "far"        # SRM = 2.0
```

### Tier Logic:

| Condition | Tier | SRM Multiplier |
|-----------|------|----------------|
| Bank LPA = Target LPA OR Bank NCA = Target NCA | `local` | 1.0 |
| Bank LPA ∈ LPA neighbors OR Bank NCA ∈ NCA neighbors | `adjacent` | 4/3 ≈ 1.33 |
| Otherwise | `far` | 2.0 |

---

## How LPA/NCA Flows Through Optimization

### 1. User Selects LPA/NCA or Enters Postcode

Session state is populated with:
- `target_lpa_name`, `target_nca_name`
- `lpa_neighbors`, `nca_neighbors`
- `lpa_neighbors_norm`, `nca_neighbors_norm`

### 2. User Clicks "Optimise"

```python
# app.py lines 4126-4128
prepare_options(
    demand_df, chosen_size,
    sstr(st.session_state["target_lpa_name"]), 
    sstr(st.session_state["target_nca_name"]),
    [sstr(n) for n in st.session_state["lpa_neighbors"]], 
    [sstr(n) for n in st.session_state["nca_neighbors"]],
    st.session_state["lpa_neighbors_norm"], 
    st.session_state["nca_neighbors_norm"]
)
```

### 3. `prepare_options()` Calls `tier_for_bank()` for Each Bank

```python
# app.py lines 3228-3232
tier = tier_for_bank(
    srow.get("lpa_name",""), srow.get("nca_name",""),
    target_lpa, target_nca,
    lpa_neigh, nca_neigh, lpa_neigh_norm, nca_neigh_norm
)
```

### 4. Tier Determines Pricing via SRM

The tier ("local", "adjacent", "far") determines the Spatial Risk Multiplier (SRM):
- **Local:** SRM = 1.0 (no markup)
- **Adjacent:** SRM = 4/3 ≈ 1.33 (33% markup)
- **Far:** SRM = 2.0 (100% markup)

---

## Required Data for New Python Optimizer

For the new Python optimizer to support LPA/NCA-based quotes, it needs:

### Input Parameters

```python
# Required request parameters
{
    "target_lpa": "Bedford",                      # Target LPA name
    "target_nca": "Bedfordshire and Cambridgeshire Claylands",  # Target NCA name
    "lpa_neighbors": ["Central Bedfordshire", "Milton Keynes", ...],  # Adjacent LPAs
    "nca_neighbors": ["The Fens", "South Suffolk and North Essex Clayland", ...],  # Adjacent NCAs
    "lpa_neighbors_norm": ["central bedfordshire", "milton keynes", ...],  # Normalized
    "nca_neighbors_norm": ["the fens", "south suffolk and north essex clayland", ...]  # Normalized
}
```

### Bank Data

Each bank record must have:
```python
{
    "bank_id": "WC1P5",
    "BANK_KEY": "Bedford",
    "lpa_name": "Bedford",      # ← Required for tier calculation
    "nca_name": "Bedfordshire and Cambridgeshire Claylands"  # ← Required for tier calculation
}
```

### Tier Calculation Implementation

```python
def tier_for_bank(bank_lpa: str, bank_nca: str,
                  target_lpa: str, target_nca: str,
                  lpa_neighbors: List[str], nca_neighbors: List[str],
                  lpa_neighbors_norm: List[str] = None,
                  nca_neighbors_norm: List[str] = None) -> str:
    """
    MUST be implemented in new optimizer exactly as shown above.
    """
    b_lpa = norm_name(bank_lpa)
    b_nca = norm_name(bank_nca)
    t_lpa_n = norm_name(target_lpa)
    t_nca_n = norm_name(target_nca)
    
    if lpa_neighbors_norm is None:
        lpa_neighbors_norm = [norm_name(x) for x in (lpa_neighbors or [])]
    if nca_neighbors_norm is None:
        nca_neighbors_norm = [norm_name(x) for x in (nca_neighbors or [])]
    
    # LPA axis
    lpa_same = b_lpa and t_lpa_n and b_lpa == t_lpa_n
    lpa_neighbour = b_lpa and b_lpa in lpa_neighbors_norm
    
    # NCA axis
    nca_same = b_nca and t_nca_n and b_nca == t_nca_n
    nca_neighbour = b_nca and b_nca in nca_neighbors_norm
    
    # Best tier wins
    if lpa_same or nca_same:
        return "local"
    elif lpa_neighbour or nca_neighbour:
        return "adjacent"
    else:
        return "far"

def norm_name(s: str) -> str:
    """Normalize name for comparison (lowercase, strip whitespace)"""
    return (s or "").lower().strip()
```

---

## Call Flow Diagram

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           USER INTERFACE                                     │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│   ┌─────────────────────┐        OR        ┌─────────────────────────────┐  │
│   │  Option A: Dropdown │                  │  Option B: Postcode/Address │  │
│   │  Select LPA: [___▼] │                  │  Enter: [SW1A 1AA______]    │  │
│   │  Select NCA: [___▼] │                  │  [🔍 Find Site]             │  │
│   │  [Apply LPA/NCA]    │                  │                             │  │
│   └─────────┬───────────┘                  └─────────────┬───────────────┘  │
│             │                                            │                   │
│             ▼                                            ▼                   │
│   ┌─────────────────────┐                  ┌─────────────────────────────┐  │
│   │ query_lpa_by_name() │                  │ find_site()                 │  │
│   │ query_nca_by_name() │                  │  ↓ geocode()                │  │
│   │                     │                  │  ↓ arcgis_point_query()     │  │
│   └─────────┬───────────┘                  └─────────────┬───────────────┘  │
│             │                                            │                   │
│             ▼                                            ▼                   │
│   ┌─────────────────────────────────────────────────────────────────────┐   │
│   │              layer_intersect_names() - ArcGIS Spatial Query          │   │
│   │              ↓ esriSpatialRelIntersects                              │   │
│   │              ↓ Returns all LPAs/NCAs sharing boundary                │   │
│   └─────────────────────────────────────────────────────────────────────┘   │
│                                        │                                     │
│                                        ▼                                     │
│   ┌─────────────────────────────────────────────────────────────────────┐   │
│   │                      SESSION STATE POPULATED                         │   │
│   │  target_lpa_name: "Bedford"                                          │   │
│   │  target_nca_name: "Bedfordshire and Cambridgeshire Claylands"        │   │
│   │  lpa_neighbors: ["Central Bedfordshire", "Milton Keynes", ...]       │   │
│   │  nca_neighbors: ["The Fens", ...]                                    │   │
│   │  lpa_neighbors_norm: ["central bedfordshire", "milton keynes", ...]  │   │
│   │  nca_neighbors_norm: ["the fens", ...]                               │   │
│   └─────────────────────────────────────────────────────────────────────┘   │
│                                        │                                     │
│                                        ▼                                     │
│   ┌─────────────────────────────────────────────────────────────────────┐   │
│   │                        USER CLICKS "OPTIMISE"                        │   │
│   └─────────────────────────────────────────────────────────────────────┘   │
│                                        │                                     │
│                                        ▼                                     │
│   ┌─────────────────────────────────────────────────────────────────────┐   │
│   │                         prepare_options()                            │   │
│   │   For each bank in Banks table:                                      │   │
│   │     tier = tier_for_bank(bank.lpa_name, bank.nca_name,               │   │
│   │                          target_lpa, target_nca,                     │   │
│   │                          lpa_neighbors, nca_neighbors, ...)          │   │
│   │                                                                      │   │
│   │   tier → SRM:                                                        │   │
│   │     "local"    → 1.0                                                 │   │
│   │     "adjacent" → 4/3 ≈ 1.33                                          │   │
│   │     "far"      → 2.0                                                 │   │
│   └─────────────────────────────────────────────────────────────────────┘   │
│                                        │                                     │
│                                        ▼                                     │
│   ┌─────────────────────────────────────────────────────────────────────┐   │
│   │                      LP SOLVER (pulp.LpProblem)                      │   │
│   │   Objective: Minimize Σ(cost × SRM × units)                          │   │
│   │   → Local banks preferred (lowest SRM)                               │   │
│   │   → Adjacent banks next                                              │   │
│   │   → Far banks last (highest SRM)                                     │   │
│   └─────────────────────────────────────────────────────────────────────┘   │
│                                        │                                     │
│                                        ▼                                     │
│   ┌─────────────────────────────────────────────────────────────────────┐   │
│   │                         ALLOCATION RESULT                            │   │
│   │   [{"bank_id": "WC1P5", "tier": "local", "cost": 24000, ...}, ...]   │   │
│   └─────────────────────────────────────────────────────────────────────┘   │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Debugging Checklist for New Optimizer

If the new Python optimizer is not allowing quotes by LPA/NCA:

### 1. Check Input Parameters
```python
# Verify these are being passed to the optimizer
print("target_lpa:", request.target_lpa)
print("target_nca:", request.target_nca)
print("lpa_neighbors:", request.lpa_neighbors)
print("nca_neighbors:", request.nca_neighbors)
```

### 2. Check Bank Data Has LPA/NCA
```python
# Banks table must have lpa_name and nca_name columns
for bank in banks:
    print(f"Bank {bank['BANK_KEY']}: LPA={bank.get('lpa_name')}, NCA={bank.get('nca_name')}")
```

### 3. Check tier_for_bank() Is Called
```python
# Add logging in prepare_options()
tier = tier_for_bank(...)
print(f"Bank {bank_key}: tier={tier}")
```

### 4. Check SRM Is Applied
```python
# Verify SRM multiplier based on tier
srm = {"local": 1.0, "adjacent": 4/3, "far": 2.0}[tier]
print(f"Bank {bank_key}: tier={tier}, SRM={srm}")
```

### 5. API Endpoint Must Accept LPA/NCA Parameters
```python
# Request model should include:
class OptimiseRequest:
    target_lpa: str
    target_nca: str
    lpa_neighbors: List[str]
    nca_neighbors: List[str]
    lpa_neighbors_norm: Optional[List[str]] = None
    nca_neighbors_norm: Optional[List[str]] = None
```

---

## Key Code Locations

| Function | File | Lines | Purpose |
|----------|------|-------|---------|
| `fetch_all_lpas_from_arcgis()` | app.py | 1472-1491 | Get all LPA names from ArcGIS |
| `fetch_all_ncas_from_arcgis()` | app.py | 1494-1513 | Get all NCA names from ArcGIS |
| `query_lpa_by_name()` | app.py | 1516-1553 | Get LPA geometry + neighbors by name |
| `query_nca_by_name()` | app.py | 1555-1600 | Get NCA geometry + neighbors by name |
| `layer_intersect_names()` | app.py | 1457-1470 | Find adjacent LPAs/NCAs via spatial query |
| `tier_for_bank()` | app.py | 1717-1745 | **Core tier calculation** |
| LPA/NCA dropdown UI | app.py | 2015-2160 | User interface for dropdown selection |
| `find_site()` | app.py | 2173-2220 | Postcode/address lookup flow |
| `prepare_options()` | app.py | 3025-3390 | Creates options with tier for LP solver |
