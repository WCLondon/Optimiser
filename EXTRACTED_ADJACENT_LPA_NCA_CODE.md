# Extracted Adjacent LPA/NCA Calculation Code

This document contains the exact code from `app.py` that calculates adjacent LPAs (Local Planning Authorities) and NCAs (National Character Areas), along with an explanation of the flow.

---

## Overview: How Adjacent LPA/NCA Calculation Works

The system calculates "adjacent" (neighboring) LPAs and NCAs to determine the **tier** for pricing. The pricing tiers are:
- **Local**: Bank is in the same LPA or NCA as the target site
- **Adjacent**: Bank is in a neighboring LPA or NCA (shares a boundary)  
- **Far**: Bank is not in the same or neighboring LPA/NCA

### Flow Summary

1. **User enters location** (via postcode/address or dropdown selection)
2. **System queries ArcGIS** to get the LPA/NCA geometry for that location
3. **System calculates neighbors** by finding all LPAs/NCAs that **intersect** (share a boundary) with the target geometry
4. **Neighbors are stored in session state** as lists
5. **During optimization**, the `tier_for_bank()` function checks if each bank's LPA/NCA is in the neighbor lists
6. **Pricing is selected** based on the tier (local → adjacent → far)

---

## 1. ArcGIS API URLs (app.py, lines 67-70)

```python
NCA_URL = ("https://services.arcgis.com/JJzESW51TqeY9uat/arcgis/rest/services/"
           "National_Character_Areas_England/FeatureServer/0")
LPA_URL = ("https://services1.arcgis.com/ESMARspQHYMw9BZ9/arcgis/rest/services/"
           "Local_Authority_Districts_December_2024_Boundaries_UK_BFC/FeatureServer/0")
```

---

## 2. Session State Variables (app.py, lines 100-103)

These store the calculated neighbor lists:

```python
# In init_session_state() defaults:
"lpa_neighbors": [],      # List of adjacent LPA names
"nca_neighbors": [],      # List of adjacent NCA names
"lpa_neighbors_norm": [], # Normalized versions of LPA neighbor names (for matching)
"nca_neighbors_norm": [], # Normalized versions of NCA neighbor names (for matching)
```

---

## 3. HTTP Helper Functions (app.py, lines 1338-1371)

These make the API requests to ArcGIS:

```python
def http_get(url, params=None, headers=None, timeout=25):
    try:
        r = requests.get(url, params=params or {}, headers=headers or UA, timeout=timeout)
        r.raise_for_status()
        return r
    except requests.exceptions.Timeout:
        raise RuntimeError(f"Timeout connecting to {url}")
    except requests.exceptions.ConnectionError:
        raise RuntimeError(f"Connection error to {url}")
    except requests.exceptions.HTTPError as e:
        raise RuntimeError(f"HTTP {e.response.status_code} error for {url}")
    except Exception as e:
        raise RuntimeError(f"HTTP error for {url}: {e}")


def http_post(url, data=None, headers=None, timeout=25):
    try:
        r = requests.post(url, data=data or {}, headers=headers or UA, timeout=timeout)
        r.raise_for_status()
        return r
    except requests.exceptions.Timeout:
        raise RuntimeError(f"Timeout connecting to {url}")
    except requests.exceptions.ConnectionError:
        raise RuntimeError(f"Connection error to {url}")
    except requests.exceptions.HTTPError as e:
        raise RuntimeError(f"HTTP {e.response.status_code} error for {url}")
    except Exception as e:
        raise RuntimeError(f"HTTP POST error for {url}: {e}")


def safe_json(r: requests.Response) -> Dict[str, Any]:
    try:
        return r.json()
    except Exception:
        preview = (r.text or "")[:300]
        raise RuntimeError(f"Invalid JSON from {r.url} (status {r.status_code}). Starts: {preview}")
```

---

## 4. Point Query - Get LPA/NCA for a Coordinate (app.py, lines 1444-1455)

This queries ArcGIS to find which LPA/NCA contains a given lat/lon point:

```python
def arcgis_point_query(layer_url: str, lat: float, lon: float, out_fields: str) -> Dict[str, Any]:
    geometry_dict = {"x": lon, "y": lat, "spatialReference": {"wkid": 4326}}
    params = {
        "f": "json", "where": "1=1",
        "geometry": json.dumps(geometry_dict), "geometryType": "esriGeometryPoint",
        "inSR": 4326, "spatialRel": "esriSpatialRelIntersects",
        "outFields": out_fields or "*", "returnGeometry": "true", "outSR": 4326
    }
    r = http_get(f"{layer_url}/query", params=params)
    js = safe_json(r)
    feats = js.get("features") or []
    return feats[0] if feats else {}
```

**How it works:**
1. Creates a point geometry from lat/lon
2. Queries ArcGIS with `esriSpatialRelIntersects` to find features containing that point
3. Returns the first matching feature (with geometry and attributes)

---

## 5. THE KEY FUNCTION: Calculate Neighbors via Polygon Intersection (app.py, lines 1457-1470)

**This is the core function that calculates adjacent/neighboring LPAs and NCAs:**

```python
def layer_intersect_names(layer_url: str, polygon_geom: Dict[str, Any], name_field: str) -> List[str]:
    if not polygon_geom:
        return []
    data = {
        "f": "json", "where": "1=1",
        "geometry": json.dumps(polygon_geom), "geometryType": "esriGeometryPolygon",
        "inSR": 4326, "spatialRel": "esriSpatialRelIntersects",
        "outFields": name_field, "returnGeometry": "false", "outSR": 4326,
        "geometryPrecision": 5,
    }
    r = http_post(f"{layer_url}/query", data=data)
    js = safe_json(r)
    names = [sstr((f.get("attributes") or {}).get(name_field)) for f in js.get("features", [])]
    return sorted({n for n in names if n})
```

**How it works:**
1. Takes the **polygon geometry** of the target LPA/NCA
2. Queries ArcGIS with `esriSpatialRelIntersects` to find all features that **share any boundary** with that polygon
3. Returns a sorted list of unique names (e.g., all LPA names that touch the target LPA)
4. The target LPA/NCA itself is included in the results (it intersects with itself), so it must be filtered out later

---

## 6. Name Normalization for Matching (app.py, lines 227-233)

Names are normalized to handle variations (e.g., "City of London" vs "London"):

```python
def norm_name(s: str) -> str:
    t = sstr(s).lower()
    t = re.sub(r'\b(city of|royal borough of|metropolitan borough of)\b', '', t)
    t = re.sub(r'\b(council|borough|district|county|unitary authority|unitary|city)\b', '', t)
    t = t.replace("&", "and")
    t = re.sub(r'[^a-z0-9]+', '', t)
    return t
```

**Example:**
- "City of London" → "london"
- "Royal Borough of Kensington and Chelsea" → "kensingtonandchelsea"

---

## 7. Convert ESRI Polygon to GeoJSON (app.py, lines 1374-1382)

```python
def esri_polygon_to_geojson(geom: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    if not geom or "rings" not in geom:
        return None
    rings = geom.get("rings") or []
    if not rings:
        return None
    if len(rings) == 1:
        return {"type": "Polygon", "coordinates": [rings[0]]}
    return {"type": "MultiPolygon", "coordinates": [[ring] for ring in rings]}
```

---

## 8. Query LPA by Name (app.py, lines 1516-1553)

Called when user selects LPA from dropdown:

```python
def query_lpa_by_name(lpa_name: str) -> Dict[str, Any]:
    """
    Query LPA geometry and neighbors by name.
    Returns dict with geometry, neighbors, and normalized neighbors.
    """
    try:
        # Query for the specific LPA by name
        params = {
            "f": "json",
            "where": f"LAD24NM = '{lpa_name}'",
            "outFields": "LAD24NM",
            "returnGeometry": "true",
            "outSR": 4326
        }
        r = http_get(f"{LPA_URL}/query", params=params)
        js = safe_json(r)
        features = js.get("features", [])
        
        if not features:
            return {"geometry": None, "neighbors": [], "neighbors_norm": []}
        
        feat = features[0]
        lpa_geom_esri = feat.get("geometry")
        lpa_gj = esri_polygon_to_geojson(lpa_geom_esri)
        
        # Get neighbors - THIS IS WHERE ADJACENT LPAs ARE CALCULATED
        lpa_nei = [n for n in layer_intersect_names(LPA_URL, lpa_geom_esri, "LAD24NM") if n != lpa_name]
        lpa_nei_norm = [norm_name(n) for n in lpa_nei]
        
        return {
            "geometry": lpa_gj,
            "geometry_esri": lpa_geom_esri,
            "neighbors": lpa_nei,
            "neighbors_norm": lpa_nei_norm
        }
    except Exception as e:
        st.warning(f"Could not fetch LPA geometry for {lpa_name}: {e}")
        return {"geometry": None, "neighbors": [], "neighbors_norm": []}
```

---

## 9. Query NCA by Name (app.py, lines 1555-1592)

Called when user selects NCA from dropdown:

```python
def query_nca_by_name(nca_name: str) -> Dict[str, Any]:
    """
    Query NCA geometry and neighbors by name.
    Returns dict with geometry, neighbors, and normalized neighbors.
    """
    try:
        # Query for the specific NCA by name
        params = {
            "f": "json",
            "where": f"NCA_Name = '{nca_name}'",
            "outFields": "NCA_Name",
            "returnGeometry": "true",
            "outSR": 4326
        }
        r = http_get(f"{NCA_URL}/query", params=params)
        js = safe_json(r)
        features = js.get("features", [])
        
        if not features:
            return {"geometry": None, "neighbors": [], "neighbors_norm": []}
        
        feat = features[0]
        nca_geom_esri = feat.get("geometry")
        nca_gj = esri_polygon_to_geojson(nca_geom_esri)
        
        # Get neighbors - THIS IS WHERE ADJACENT NCAs ARE CALCULATED
        nca_nei = [n for n in layer_intersect_names(NCA_URL, nca_geom_esri, "NCA_Name") if n != nca_name]
        nca_nei_norm = [norm_name(n) for n in nca_nei]
        
        return {
            "geometry": nca_gj,
            "geometry_esri": nca_geom_esri,
            "neighbors": nca_nei,
            "neighbors_norm": nca_nei_norm
        }
    except Exception as e:
        st.warning(f"Could not fetch NCA geometry for {nca_name}: {e}")
        return {"geometry": None, "neighbors": [], "neighbors_norm": []}
```

---

## 10. Full Site Lookup via Postcode/Address (app.py, lines 2175-2220)

This is called when user enters a postcode or address:

```python
def find_site(postcode: str, address: str):
    postcode = sstr(postcode)
    address = sstr(address)
    if sstr(postcode):
        lat, lon, _ = get_postcode_info(postcode)
    elif sstr(address):
        lat, lon = geocode_address(address)
    else:
        raise RuntimeError("Enter a postcode or an address.")
    
    # Query ArcGIS to get LPA and NCA that contain this point
    lpa_feat = arcgis_point_query(LPA_URL, lat, lon, "LAD24NM")
    nca_feat = arcgis_point_query(NCA_URL, lat, lon, "NCA_Name")
    t_lpa = sstr((lpa_feat.get("attributes") or {}).get("LAD24NM"))
    t_nca = sstr((nca_feat.get("attributes") or {}).get("NCA_Name"))
    lpa_geom_esri = lpa_feat.get("geometry")
    nca_geom_esri = nca_feat.get("geometry")
    lpa_gj = esri_polygon_to_geojson(lpa_geom_esri)
    nca_gj = esri_polygon_to_geojson(nca_geom_esri)
    
    # CALCULATE ADJACENT LPAs AND NCAs HERE
    lpa_nei = [n for n in layer_intersect_names(LPA_URL, lpa_geom_esri, "LAD24NM") if n != t_lpa]
    nca_nei = [n for n in layer_intersect_names(NCA_URL, nca_geom_esri, "NCA_Name") if n != t_nca]
    lpa_nei_norm = [norm_name(n) for n in lpa_nei]
    nca_nei_norm = [norm_name(n) for n in nca_nei]
    
    # Get watercourse catchments for site
    waterbody, operational = get_watercourse_catchments_for_point(lat, lon)
    
    # Update session state - store neighbors for later tier calculations
    st.session_state["target_lpa_name"] = t_lpa
    st.session_state["target_nca_name"] = t_nca
    st.session_state["lpa_neighbors"] = lpa_nei
    st.session_state["nca_neighbors"] = nca_nei
    st.session_state["lpa_neighbors_norm"] = lpa_nei_norm
    st.session_state["nca_neighbors_norm"] = nca_nei_norm
    st.session_state["target_lat"] = lat
    st.session_state["target_lon"] = lon
    st.session_state["lpa_geojson"] = lpa_gj
    st.session_state["nca_geojson"] = nca_gj
    st.session_state["target_waterbody"] = waterbody
    st.session_state["target_operational_catchment"] = operational
    # ...
    return t_lpa, t_nca
```

---

## 11. Dropdown Selection Handler (app.py, lines 2088-2123)

When user selects LPA/NCA from dropdown and clicks "Apply":

```python
# Apply LPA/NCA dropdown selection
if st.button("Apply LPA/NCA Selection", key="apply_lpa_nca_btn"):
    if st.session_state.get("selected_lpa_dropdown") or st.session_state.get("selected_nca_dropdown"):
        # Fetch geometries and neighbors from ArcGIS
        lpa_data = None
        nca_data = None
        
        if st.session_state.get("selected_lpa_dropdown"):
            lpa_name = st.session_state["selected_lpa_dropdown"]
            st.session_state["target_lpa_name"] = lpa_name
            with st.spinner(f"Fetching geometry for LPA: {lpa_name}..."):
                lpa_data = query_lpa_by_name(lpa_name)
        
        if st.session_state.get("selected_nca_dropdown"):
            nca_name = st.session_state["selected_nca_dropdown"]
            st.session_state["target_nca_name"] = nca_name
            with st.spinner(f"Fetching geometry for NCA: {nca_name}..."):
                nca_data = query_nca_by_name(nca_name)
        
        # Update session state with geometries and neighbors
        if lpa_data:
            st.session_state["lpa_geojson"] = lpa_data.get("geometry")
            st.session_state["lpa_neighbors"] = lpa_data.get("neighbors", [])
            st.session_state["lpa_neighbors_norm"] = lpa_data.get("neighbors_norm", [])
        else:
            st.session_state["lpa_geojson"] = None
            st.session_state["lpa_neighbors"] = []
            st.session_state["lpa_neighbors_norm"] = []
        
        if nca_data:
            st.session_state["nca_geojson"] = nca_data.get("geometry")
            st.session_state["nca_neighbors"] = nca_data.get("neighbors", [])
            st.session_state["nca_neighbors_norm"] = nca_data.get("neighbors_norm", [])
        else:
            st.session_state["nca_geojson"] = None
            st.session_state["nca_neighbors"] = []
            st.session_state["nca_neighbors_norm"] = []
```

---

## 12. THE TIER CALCULATION FUNCTION (app.py, lines 1717-1745)

This function uses the neighbor lists to determine pricing tier for each bank:

```python
def tier_for_bank(bank_lpa: str, bank_nca: str,
                  t_lpa: str, t_nca: str,
                  lpa_neigh: List[str], nca_neigh: List[str],
                  lpa_neigh_norm: Optional[List[str]] = None,
                  nca_neigh_norm: Optional[List[str]] = None) -> str:
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
        return "local"  # Local > Adjacent > Far
    elif lpa_neighbour or nca_neighbour:
        return "adjacent"  # Adjacent > Far
    else:
        return "far"
```

**Logic:**
- If bank is in **same** LPA OR same NCA → `"local"`
- Else if bank is in **neighbor** LPA OR neighbor NCA → `"adjacent"`
- Else → `"far"`

---

## 13. Usage in Optimization (app.py, line 3231 example)

The tier calculation is used during optimization to price each supply option:

```python
tier = tier_for_bank(
    sstr(stk.get("lpa_name")), sstr(stk.get("nca_name")),
    target_lpa, target_nca, 
    lpa_neigh, nca_neigh, 
    lpa_neigh_norm, nca_neigh_norm
)
```

---

## Complete Call Flow Diagram

```
┌─────────────────────────────────────────────────────────────────────────┐
│                        USER ENTERS LOCATION                              │
├─────────────────────────────────────────────────────────────────────────┤
│  Option A: Postcode/Address        │  Option B: LPA/NCA Dropdown        │
│  find_site()                       │  "Apply LPA/NCA Selection" button  │
└───────────────┬─────────────────────┴───────────────┬───────────────────┘
                │                                     │
                ▼                                     ▼
┌───────────────────────────────────┐  ┌─────────────────────────────────┐
│  arcgis_point_query()             │  │  query_lpa_by_name()            │
│  - Find LPA/NCA containing point  │  │  query_nca_by_name()            │
│  - Get geometry (polygon)         │  │  - Query by name                │
└───────────────┬───────────────────┘  │  - Get geometry (polygon)       │
                │                      └───────────────┬─────────────────┘
                ▼                                      │
┌───────────────────────────────────────────────────────────────────────┐
│                    layer_intersect_names()                             │
│  - Input: polygon geometry of target LPA/NCA                          │
│  - Query: esriSpatialRelIntersects (find all polygons sharing border)  │
│  - Output: List of all LPA/NCA names that touch the boundary           │
│  - Filter: Remove the target itself (it intersects with itself)        │
└───────────────────────────────────┬───────────────────────────────────┘
                                    │
                                    ▼
┌───────────────────────────────────────────────────────────────────────┐
│                    Store in Session State                              │
│  st.session_state["lpa_neighbors"] = lpa_nei                          │
│  st.session_state["nca_neighbors"] = nca_nei                          │
│  st.session_state["lpa_neighbors_norm"] = [norm_name(n) for n in ...]  │
│  st.session_state["nca_neighbors_norm"] = [norm_name(n) for n in ...]  │
└───────────────────────────────────┬───────────────────────────────────┘
                                    │
                                    ▼
┌───────────────────────────────────────────────────────────────────────┐
│                         OPTIMIZATION                                   │
│  For each bank/habitat supply option:                                  │
│    tier = tier_for_bank(bank_lpa, bank_nca, target_lpa, target_nca,   │
│                         lpa_neighbors, nca_neighbors)                  │
│                                                                        │
│  Result: "local" | "adjacent" | "far"                                  │
│  Used for: Selecting correct price tier from Pricing table             │
└───────────────────────────────────────────────────────────────────────┘
```

---

## Summary

1. **`layer_intersect_names()`** is the core function - it uses ArcGIS's spatial intersection query to find all LPAs/NCAs that share a boundary with the target polygon

2. **Neighbors are calculated** when user:
   - Enters a postcode/address (via `find_site()`)
   - Selects from LPA/NCA dropdown (via `query_lpa_by_name()`/`query_nca_by_name()`)

3. **Neighbors are stored** in session state as both raw names and normalized versions

4. **During optimization**, `tier_for_bank()` checks if each bank's LPA/NCA is in the neighbor lists to determine pricing tier

5. **Tier logic**: Local (same) > Adjacent (neighbor) > Far (neither)
