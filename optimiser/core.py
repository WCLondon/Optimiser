"""
optimiser/core.py

Core business logic for BNG Optimiser.
Pure functions extracted from the Streamlit app for reuse in Shiny.
"""

from functools import lru_cache
from typing import Dict, Any, List, Tuple, Optional
import re
import numpy as np
import pandas as pd
import requests


# ================= Constants =================
ADMIN_FEE_GBP = 500.0
SINGLE_BANK_SOFT_PCT = 0.01
LEDGER_AREA = "area"
LEDGER_HEDGE = "hedgerow"
LEDGER_WATER = "watercourse"

# Tier proximity ranking: lower is better (closer)
TIER_PROXIMITY_RANK = {"local": 0, "adjacent": 1, "far": 2}

NET_GAIN_LABEL = "Net Gain (Area)"
NET_GAIN_WATERCOURSE_LABEL = "Net Gain (Watercourses)"

# API URLs
POSTCODES_IO = "https://api.postcodes.io/postcodes/"
NOMINATIM_SEARCH = "https://nominatim.openstreetmap.org/search"
NCA_URL = ("https://services.arcgis.com/JJzESW51TqeY9uat/arcgis/rest/services/"
           "National_Character_Areas_England/FeatureServer/0")
LPA_URL = ("https://services1.arcgis.com/ESMARspQHYMw9BZ9/arcgis/rest/services/"
           "Local_Authority_Districts_December_2024_Boundaries_UK_BFC/FeatureServer/0")

UA = {"User-Agent": "WildCapital-Optimiser/1.0 (+contact@example.com)"}


# ================= String Utilities =================

def sstr(x) -> str:
    """Safely convert value to string."""
    if x is None:
        return ""
    if isinstance(x, float) and (np.isnan(x) or np.isinf(x)):
        return ""
    return str(x).strip()


def norm_name(s: str) -> str:
    """Normalize location name for matching."""
    t = sstr(s).lower()
    t = re.sub(r'\b(city of|royal borough of|metropolitan borough of)\b', '', t)
    t = re.sub(r'\b(council|borough|district|county|unitary authority|unitary|city)\b', '', t)
    t = t.replace("&", "and")
    t = re.sub(r'[^a-z0-9]+', '', t)
    return t


# ================= Habitat Classification =================

def is_hedgerow(name: str, backend: Optional[Dict[str, pd.DataFrame]] = None) -> bool:
    """Check if habitat is a hedgerow type."""
    name_str = sstr(name)
    
    # Check if it's the hedgerow net gain label
    if name_str == "Net Gain (Hedgerows)":
        return True
    
    # Check UmbrellaType column if backend is loaded
    if backend and "HabitatCatalog" in backend:
        catalog = backend["HabitatCatalog"]
        if "UmbrellaType" in catalog.columns:
            match = catalog[catalog["habitat_name"].astype(str).str.strip() == name_str]
            if not match.empty:
                umbrella_type = sstr(match.iloc[0]["UmbrellaType"]).lower()
                return umbrella_type == "hedgerow"
    
    # Fallback to text matching
    return "hedgerow" in name_str.lower()


def is_watercourse(name: str, backend: Optional[Dict[str, pd.DataFrame]] = None) -> bool:
    """Check if habitat is a watercourse type."""
    name_str = sstr(name)
    
    # Check UmbrellaType column if backend is loaded
    if backend and "HabitatCatalog" in backend:
        catalog = backend["HabitatCatalog"]
        if "UmbrellaType" in catalog.columns:
            match = catalog[catalog["habitat_name"].astype(str).str.strip() == name_str]
            if not match.empty:
                umbrella_type = sstr(match.iloc[0]["UmbrellaType"]).lower()
                return umbrella_type == "watercourse"
    
    # Fallback to text matching
    name_lower = name_str.lower()
    return "watercourse" in name_lower or "water" in name_lower


def get_hedgerow_habitats(catalog_df: pd.DataFrame) -> List[str]:
    """Get list of hedgerow habitats from catalog."""
    if "UmbrellaType" in catalog_df.columns:
        hedgerow_df = catalog_df[catalog_df["UmbrellaType"].astype(str).str.strip().str.lower() == "hedgerow"]
        return sorted([sstr(x) for x in hedgerow_df["habitat_name"].dropna().unique().tolist()])
    else:
        all_habitats = [sstr(x) for x in catalog_df["habitat_name"].dropna().unique().tolist()]
        return sorted([h for h in all_habitats if is_hedgerow(h)])


def get_watercourse_habitats(catalog_df: pd.DataFrame) -> List[str]:
    """Get list of watercourse habitats from catalog."""
    if "UmbrellaType" in catalog_df.columns:
        watercourse_df = catalog_df[catalog_df["UmbrellaType"].astype(str).str.strip().str.lower() == "watercourse"]
        return sorted([sstr(x) for x in watercourse_df["habitat_name"].dropna().unique().tolist()])
    else:
        all_habitats = [sstr(x) for x in catalog_df["habitat_name"].dropna().unique().tolist()]
        return sorted([h for h in all_habitats if is_watercourse(h)])


def get_area_habitats(catalog_df: pd.DataFrame) -> List[str]:
    """Get list of area habitats from catalog."""
    if "UmbrellaType" in catalog_df.columns:
        area_df = catalog_df[
            (catalog_df["UmbrellaType"].astype(str).str.strip().str.lower() != "hedgerow") &
            (catalog_df["UmbrellaType"].astype(str).str.strip().str.lower() != "watercourse")
        ]
        return sorted([sstr(x) for x in area_df["habitat_name"].dropna().unique().tolist()])
    else:
        all_habitats = [sstr(x) for x in catalog_df["habitat_name"].dropna().unique().tolist()]
        return sorted([h for h in all_habitats if not is_hedgerow(h) and not is_watercourse(h)])


def get_umbrella_for(hab_name: str, catalog: pd.DataFrame) -> str:
    """Get umbrella type for a habitat."""
    if "UmbrellaType" in catalog.columns:
        match = catalog[catalog["habitat_name"].astype(str).str.strip() == hab_name]
        if not match.empty:
            u = sstr(match.iloc[0]["UmbrellaType"]).strip().lower()
            if u == "hedgerow":
                return LEDGER_HEDGE
            elif u == "watercourse":
                return LEDGER_WATER
    
    # Fallback logic
    if is_hedgerow(hab_name):
        return LEDGER_HEDGE
    if is_watercourse(hab_name):
        return LEDGER_WATER
    return LEDGER_AREA


# ================= HTTP Utilities =================

def http_get(url, params=None, headers=None, timeout=25):
    """HTTP GET with error handling."""
    if headers is None:
        headers = UA
    resp = requests.get(url, params=params, headers=headers, timeout=timeout)
    resp.raise_for_status()
    return resp


def http_post(url, data=None, headers=None, timeout=25):
    """HTTP POST with error handling."""
    if headers is None:
        headers = UA
    resp = requests.post(url, json=data, headers=headers, timeout=timeout)
    resp.raise_for_status()
    return resp


def safe_json(r: requests.Response) -> Dict[str, Any]:
    """Safely extract JSON from response."""
    try:
        return r.json()
    except Exception:
        return {}


# ================= Geographic Utilities =================

def esri_polygon_to_geojson(geom: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Convert ESRI polygon to GeoJSON."""
    if not geom or "rings" not in geom:
        return None
    return {"type": "Polygon", "coordinates": geom["rings"]}


def get_postcode_info(pc: str) -> Tuple[float, float, str]:
    """Get coordinates and admin area for a UK postcode."""
    clean_pc = pc.strip().upper().replace(" ", "")
    r = http_get(POSTCODES_IO + clean_pc, timeout=10)
    j = safe_json(r)
    result = j.get("result", {})
    lat = result.get("latitude")
    lon = result.get("longitude")
    admin = result.get("admin_district", "")
    if lat and lon:
        return float(lat), float(lon), admin
    raise ValueError(f"Postcode {pc} not found")


def geocode_address(addr: str) -> Tuple[float, float]:
    """Geocode an address using Nominatim."""
    params = {
        "q": addr,
        "format": "json",
        "limit": 1,
        "countrycodes": "gb"
    }
    r = http_get(NOMINATIM_SEARCH, params=params, headers=UA, timeout=10)
    j = safe_json(r)
    if j and len(j) > 0:
        lat = float(j[0]["lat"])
        lon = float(j[0]["lon"])
        return lat, lon
    raise ValueError(f"Address {addr} not found")


def arcgis_point_query(layer_url: str, lat: float, lon: float, out_fields: str) -> Dict[str, Any]:
    """Query ArcGIS layer at a point."""
    params = {
        "geometry": f"{lon},{lat}",
        "geometryType": "esriGeometryPoint",
        "inSR": "4326",
        "outFields": out_fields,
        "returnGeometry": "true",
        "f": "json"
    }
    r = http_get(layer_url + "/query", params=params, timeout=20)
    j = safe_json(r)
    features = j.get("features", [])
    if features:
        return features[0].get("attributes", {}), features[0].get("geometry", {})
    return {}, {}


def layer_intersect_names(layer_url: str, polygon_geom: Dict[str, Any], name_field: str) -> List[str]:
    """Find features that intersect with a polygon."""
    payload = {
        "geometry": polygon_geom,
        "geometryType": "esriGeometryPolygon",
        "inSR": {"wkid": 4326},
        "spatialRel": "esriSpatialRelIntersects",
        "outFields": name_field,
        "returnGeometry": False,
        "f": "json"
    }
    r = http_post(layer_url + "/query", data=payload, timeout=30)
    j = safe_json(r)
    features = j.get("features", [])
    names = []
    for feat in features:
        attrs = feat.get("attributes", {})
        name = attrs.get(name_field)
        if name:
            names.append(sstr(name))
    return names


@lru_cache(maxsize=1)
def fetch_all_lpas_from_arcgis() -> List[str]:
    """Fetch all LPA names from ArcGIS (cached)."""
    params = {
        "where": "1=1",
        "outFields": "LAD24NM",
        "returnGeometry": "false",
        "f": "json"
    }
    r = http_get(LPA_URL + "/query", params=params, timeout=30)
    j = safe_json(r)
    features = j.get("features", [])
    lpas = []
    for feat in features:
        name = feat.get("attributes", {}).get("LAD24NM")
        if name:
            lpas.append(sstr(name))
    return sorted(list(set(lpas)))


@lru_cache(maxsize=1)
def fetch_all_ncas_from_arcgis() -> List[str]:
    """Fetch all NCA names from ArcGIS (cached)."""
    params = {
        "where": "1=1",
        "outFields": "NCA_Name",
        "returnGeometry": "false",
        "f": "json"
    }
    r = http_get(NCA_URL + "/query", params=params, timeout=30)
    j = safe_json(r)
    features = j.get("features", [])
    ncas = []
    for feat in features:
        name = feat.get("attributes", {}).get("NCA_Name")
        if name:
            ncas.append(sstr(name))
    return sorted(list(set(ncas)))


def query_lpa_by_name(lpa_name: str) -> Dict[str, Any]:
    """Query LPA by name from ArcGIS."""
    params = {
        "where": f"LAD24NM = '{lpa_name}'",
        "outFields": "LAD24NM",
        "returnGeometry": "true",
        "f": "json"
    }
    r = http_get(LPA_URL + "/query", params=params, timeout=20)
    j = safe_json(r)
    features = j.get("features", [])
    if features:
        return features[0]
    return {}


def query_nca_by_name(nca_name: str) -> Dict[str, Any]:
    """Query NCA by name from ArcGIS."""
    params = {
        "where": f"NCA_Name = '{nca_name}'",
        "outFields": "NCA_Name",
        "returnGeometry": "true",
        "f": "json"
    }
    r = http_get(NCA_URL + "/query", params=params, timeout=20)
    j = safe_json(r)
    features = j.get("features", [])
    if features:
        return features[0]
    return {}


def get_lpa_nca_for_point(lat: float, lon: float) -> Tuple[str, str]:
    """Get LPA and NCA for a point."""
    lpa_attrs, _ = arcgis_point_query(LPA_URL, lat, lon, "LAD24NM")
    nca_attrs, _ = arcgis_point_query(NCA_URL, lat, lon, "NCA_Name")
    lpa_name = lpa_attrs.get("LAD24NM", "")
    nca_name = nca_attrs.get("NCA_Name", "")
    return sstr(lpa_name), sstr(nca_name)


def get_catchment_geo_for_point(lat: float, lon: float) -> Tuple[str, Optional[Dict[str, Any]], str, Optional[Dict[str, Any]]]:
    """Get LPA/NCA names and geometry for a point."""
    lpa_attrs, lpa_geom = arcgis_point_query(LPA_URL, lat, lon, "LAD24NM")
    nca_attrs, nca_geom = arcgis_point_query(NCA_URL, lat, lon, "NCA_Name")
    lpa_name = sstr(lpa_attrs.get("LAD24NM", ""))
    nca_name = sstr(nca_attrs.get("NCA_Name", ""))
    lpa_geojson = esri_polygon_to_geojson(lpa_geom) if lpa_geom else None
    nca_geojson = esri_polygon_to_geojson(nca_geom) if nca_geom else None
    return lpa_name, lpa_geojson, nca_name, nca_geojson


# ================= Tier Calculation =================

def tier_for_bank(bank_lpa: str, bank_nca: str,
                  target_lpa: str, target_nca: str,
                  lpa_neighbors: List[str], nca_neighbors: List[str]) -> str:
    """Calculate tier (local/adjacent/far) for a bank."""
    bank_lpa_norm = norm_name(bank_lpa)
    bank_nca_norm = norm_name(bank_nca)
    target_lpa_norm = norm_name(target_lpa)
    target_nca_norm = norm_name(target_nca)
    
    lpa_match = (bank_lpa_norm == target_lpa_norm)
    nca_match = (bank_nca_norm == target_nca_norm)
    
    if lpa_match or nca_match:
        return "local"
    
    lpa_neighbors_norm = [norm_name(n) for n in lpa_neighbors]
    nca_neighbors_norm = [norm_name(n) for n in nca_neighbors]
    
    if bank_lpa_norm in lpa_neighbors_norm or bank_nca_norm in nca_neighbors_norm:
        return "adjacent"
    
    return "far"


# ================= Contract Size Selection =================

def select_contract_size(total_units: float, present: List[str]) -> str:
    """Select appropriate contract size based on total units."""
    if not present:
        return "Unknown"
    
    # Sort sizes to find the smallest that can accommodate the units
    sizes_sorted = sorted(present)
    
    # Extract numeric thresholds
    size_map = {}
    for s in sizes_sorted:
        if "<" in s:
            threshold = float(s.split("<")[1].strip())
            size_map[threshold] = s
        elif ">" in s or "+" in s:
            # For sizes like ">50" or "50+", use a large threshold
            size_map[float('inf')] = s
    
    # Find smallest size that fits
    for threshold in sorted(size_map.keys()):
        if total_units <= threshold:
            return size_map[threshold]
    
    # If no size fits, return the largest
    return sizes_sorted[-1] if sizes_sorted else "Unknown"


# ================= Discount Application =================

def apply_tier_up_discount(contract_size: str, available_sizes: List[str]) -> str:
    """Apply tier-up discount by selecting next larger contract size."""
    if not available_sizes or contract_size not in available_sizes:
        return contract_size
    
    sizes_sorted = sorted(available_sizes)
    current_idx = sizes_sorted.index(contract_size)
    
    if current_idx < len(sizes_sorted) - 1:
        return sizes_sorted[current_idx + 1]
    
    return contract_size


def apply_percentage_discount(unit_price: float, discount_percentage: float) -> float:
    """Apply percentage discount to unit price."""
    return unit_price * (1 - discount_percentage / 100.0)


# ================= Data Loading and Preparation =================

@lru_cache(maxsize=1)
def load_backend_cached(backend_path: str = None) -> Dict[str, pd.DataFrame]:
    """Load backend data from Excel file (cached)."""
    # This would load from a file - placeholder for now
    # In practice, this would be called with the actual file path
    raise NotImplementedError("Backend loading should be implemented with actual file path")


def make_bank_key_col(df: pd.DataFrame, banks_df: pd.DataFrame) -> pd.DataFrame:
    """Add BANK_KEY column to dataframe by matching bank names."""
    if "BANK_KEY" in df.columns:
        return df
    
    if "bank_name" not in df.columns or banks_df.empty:
        return df
    
    df = df.copy()
    bank_map = {}
    if "bank_name" in banks_df.columns and "BANK_KEY" in banks_df.columns:
        for _, row in banks_df.iterrows():
            name = sstr(row["bank_name"]).strip().lower()
            key = sstr(row["BANK_KEY"]).strip()
            if name and key:
                bank_map[name] = key
    
    def lookup_key(name_val):
        name_str = sstr(name_val).strip().lower()
        return bank_map.get(name_str, "")
    
    df["BANK_KEY"] = df["bank_name"].apply(lookup_key)
    return df


def normalise_pricing(pr_df: pd.DataFrame) -> pd.DataFrame:
    """Normalize pricing dataframe."""
    pr_df = pr_df.copy()
    
    # Ensure required columns exist
    required_cols = ["habitat_name", "tier", "contract_size", "unit_price"]
    for col in required_cols:
        if col not in pr_df.columns:
            pr_df[col] = None
    
    # Normalize strings
    if "habitat_name" in pr_df.columns:
        pr_df["habitat_name"] = pr_df["habitat_name"].astype(str).str.strip()
    if "tier" in pr_df.columns:
        pr_df["tier"] = pr_df["tier"].astype(str).str.strip().str.lower()
    if "contract_size" in pr_df.columns:
        pr_df["contract_size"] = pr_df["contract_size"].astype(str).str.strip()
    
    # Ensure numeric unit_price
    if "unit_price" in pr_df.columns:
        pr_df["unit_price"] = pd.to_numeric(pr_df["unit_price"], errors="coerce")
    
    return pr_df


# ================= Bank Geography Enrichment =================

def bank_row_to_latlon(row: pd.Series) -> Optional[Tuple[float, float, str]]:
    """Extract lat/lon from bank row."""
    lat = None
    lon = None
    bank_key = sstr(row.get("BANK_KEY", ""))
    
    # Try different column names for coordinates
    for lat_col in ["Latitude", "latitude", "lat", "LAT"]:
        if lat_col in row.index and pd.notna(row[lat_col]):
            try:
                lat = float(row[lat_col])
                break
            except (ValueError, TypeError):
                pass
    
    for lon_col in ["Longitude", "longitude", "lon", "LON", "long"]:
        if lon_col in row.index and pd.notna(row[lon_col]):
            try:
                lon = float(row[lon_col])
                break
            except (ValueError, TypeError):
                pass
    
    if lat is not None and lon is not None:
        return lat, lon, bank_key
    return None


def enrich_banks_geography(banks_df: pd.DataFrame, force_refresh: bool = False) -> pd.DataFrame:
    """Enrich banks dataframe with LPA/NCA information."""
    banks_df = banks_df.copy()
    
    # Add LPA/NCA columns if they don't exist
    if "bank_lpa" not in banks_df.columns:
        banks_df["bank_lpa"] = ""
    if "bank_nca" not in banks_df.columns:
        banks_df["bank_nca"] = ""
    
    # Only enrich rows that need it
    for idx, row in banks_df.iterrows():
        if force_refresh or not row.get("bank_lpa") or not row.get("bank_nca"):
            coords = bank_row_to_latlon(row)
            if coords:
                lat, lon, _ = coords
                try:
                    lpa_name, nca_name = get_lpa_nca_for_point(lat, lon)
                    banks_df.at[idx, "bank_lpa"] = lpa_name
                    banks_df.at[idx, "bank_nca"] = nca_name
                except Exception:
                    pass
    
    return banks_df
