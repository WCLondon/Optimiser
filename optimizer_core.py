"""
optimizer_core.py - Pure Python optimization functions (NO Streamlit)

This module contains the core optimization logic extracted from app.py to allow
imports without triggering Streamlit UI code execution.
"""

import json
import re
import sys
import time
from datetime import datetime
from typing import Dict, Any, List, Tuple, Optional

import numpy as np
import pandas as pd
import requests

# Repository layer for reference/config tables
import repo

# Constants
ADMIN_FEE_GBP = 500.0  # Standard admin fee
ADMIN_FEE_FRACTIONAL_GBP = 300.0  # Admin fee for fractional quotes
SINGLE_BANK_SOFT_PCT = 0.01
GEOCODING_RATE_LIMIT_SECONDS = 0.15  # Rate limit between API calls
UA = {"User-Agent": "WildCapital-Optimiser/1.0 (+contact@example.com)"}
LEDGER_AREA = "area"
LEDGER_HEDGE = "hedgerow"
LEDGER_WATER = "watercourse"

# Tier proximity ranking: lower is better (closer)
TIER_PROXIMITY_RANK = {"local": 0, "adjacent": 1, "far": 2}

# Net Gain labels
NET_GAIN_LABEL = "Net Gain (Low-equivalent)"
NET_GAIN_HEDGEROW_LABEL = "Net Gain (Hedgerows)"
NET_GAIN_WATERCOURSE_LABEL = "Net Gain (Watercourses)"

POSTCODES_IO = "https://api.postcodes.io/postcodes/"
NOMINATIM_SEARCH = "https://nominatim.openstreetmap.org/search"
NCA_URL = ("https://services.arcgis.com/JJzESW51TqeY9uat/arcgis/rest/services/"
           "National_Character_Areas_England/FeatureServer/0")
LPA_URL = ("https://services1.arcgis.com/ESMARspQHYMw9BZ9/arcgis/rest/services/"
           "Local_Authority_Districts_December_2024_Boundaries_UK_BFC/FeatureServer/0")

# Watercourse catchment URLs for SRM calculation
WATERBODY_CATCHMENT_URL = ("https://environment.data.gov.uk/spatialdata/water-framework-directive-"
                          "river-waterbody-catchments-cycle-2/wfs")
OPERATIONAL_CATCHMENT_URL = ("https://environment.data.gov.uk/spatialdata/water-framework-directive-"
                            "river-operational-catchments-cycle-2/wfs")


# ================= String Helpers =================
def sstr(x) -> str:
    """Safe string conversion"""
    if x is None:
        return ""
    if isinstance(x, float) and (np.isnan(x) or np.isinf(x)):
        return ""
    return str(x).strip()


def norm_name(s: str) -> str:
    """Normalize name for matching (e.g., LPA/NCA names)"""
    t = sstr(s).lower()
    t = re.sub(r'\b(city of|royal borough of|metropolitan borough of)\b', '', t)
    t = re.sub(r'\b(council|borough|district|county|unitary authority|unitary|city)\b', '', t)
    t = t.replace("&", "and")
    t = re.sub(r'[^a-z0-9]+', '', t)
    return t


# ================= HTTP Helpers =================
def http_get(url, params=None, headers=None, timeout=25):
    """HTTP GET with error handling"""
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
    """HTTP POST with error handling"""
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
    """Safe JSON parsing"""
    try:
        return r.json()
    except Exception:
        preview = (r.text or "")[:300]
        raise RuntimeError(f"Invalid JSON from {r.url} (status {r.status_code}). Starts: {preview}")


# ================= Geocoding / lookups =================
def get_postcode_info(pc: str) -> Tuple[float, float, str]:
    """Geocode postcode to lat/lon using postcodes.io"""
    pc_clean = sstr(pc).replace(" ", "").upper()
    r = http_get(POSTCODES_IO + pc_clean)
    js = safe_json(r)
    if js.get("status") != 200 or not js.get("result"):
        raise RuntimeError(f"Postcode lookup failed for '{pc}'.")
    data = js["result"]
    return float(data["latitude"]), float(data["longitude"]), sstr(data.get("admin_district") or data.get("admin_county"))


def geocode_address(addr: str) -> Tuple[float, float]:
    """Geocode address to lat/lon"""
    r = http_get(NOMINATIM_SEARCH, params={"q": sstr(addr), "format": "jsonv2", "limit": 1, "addressdetails": 0})
    js = safe_json(r)
    if isinstance(js, list) and js:
        lat, lon = js[0]["lat"], js[0]["lon"]
        return float(lat), float(lon)
    r = http_get("https://photon.komoot.io/api/", params={"q": sstr(addr), "limit": 1})
    js = safe_json(r)
    feats = js.get("features") or []
    if feats:
        lon, lat = feats[0]["geometry"]["coordinates"]
        return float(lat), float(lon)
    raise RuntimeError("Address geocoding failed.")


def arcgis_point_query(layer_url: str, lat: float, lon: float, out_fields: str) -> Dict[str, Any]:
    """Query ArcGIS service for features at a point"""
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


def layer_intersect_names(layer_url: str, polygon_geom: Dict[str, Any], name_field: str) -> List[str]:
    """Get intersecting feature names from ArcGIS layer"""
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


def get_lpa_nca_for_point(lat: float, lon: float) -> Tuple[str, str]:
    """Get LPA/NCA for coordinates"""
    lpa = sstr((arcgis_point_query(LPA_URL, lat, lon, "LAD24NM").get("attributes") or {}).get("LAD24NM"))
    nca = sstr((arcgis_point_query(NCA_URL, lat, lon, "NCA_Name").get("attributes") or {}).get("NCA_Name"))
    return lpa, nca


def enrich_banks_with_geography(banks_df: pd.DataFrame) -> pd.DataFrame:
    """
    Geocode banks and add lpa_name/nca_name columns.
    This matches app.py's enrich_banks_geography() function.
    Only geocodes banks with empty lpa_name or nca_name.
    
    Args:
        banks_df: DataFrame with banks data
        
    Returns:
        DataFrame with enriched banks data including lpa_name and nca_name
        
    Side effects:
        - Makes API calls to postcodes.io and ArcGIS services for geocoding
        - Rate limits API calls with 0.15s delay after successful geocoding
        - Writes warnings to stderr for failed geocoding attempts
        - Does NOT persist changes to database (in-memory only)
    """
    df = banks_df.copy()
    
    # Ensure columns exist
    if "lpa_name" not in df.columns:
        df["lpa_name"] = ""
    if "nca_name" not in df.columns:
        df["nca_name"] = ""
    
    enriched_banks = []
    
    # Note: Using iterrows() to match app.py's enrich_banks_geography() logic exactly.
    # This ensures consistent behavior between app.py and optimizer_core.py.
    # Banks are typically few in number (< 100), so performance impact is minimal.
    for idx, row in df.iterrows():
        # Convert to dict for easier manipulation
        bank = row.to_dict()
        
        # Check if already has geography data (using sstr to handle empty strings/NaN)
        lpa_now = sstr(bank.get("lpa_name"))
        nca_now = sstr(bank.get("nca_name"))
        
        if lpa_now and nca_now:
            # Already enriched, skip
            enriched_banks.append(bank)
            continue
        
        # Try to get postcode
        postcode = sstr(bank.get('postcode'))
        if not postcode:
            # No postcode, can't geocode
            enriched_banks.append(bank)
            continue
        
        try:
            # Geocode postcode to lat/lon
            lat, lon, _ = get_postcode_info(postcode)
            if lat and lon:
                # Look up LPA/NCA
                lpa_name, nca_name = get_lpa_nca_for_point(lat, lon)
                # Only update if empty
                if not lpa_now:
                    bank['lpa_name'] = lpa_name
                if not nca_now:
                    bank['nca_name'] = nca_name
                
                # Rate limit only after successful API calls
                time.sleep(GEOCODING_RATE_LIMIT_SECONDS)
        except Exception as e:
            bank_name = sstr(bank.get('bank_name', 'Unknown'))
            sys.stderr.write(f"Warning: Failed to geocode bank {bank_name}: {e}\n")
        
        enriched_banks.append(bank)
    
    return pd.DataFrame(enriched_banks)


# ================= Ledger helpers =================
def get_umbrella_for(hab_name: str, catalog: pd.DataFrame) -> str:
    """Return 'hedgerow' | 'watercourse' | 'area' for a habitat name"""
    h = sstr(hab_name)
    if not h:
        return LEDGER_AREA
    if h == NET_GAIN_HEDGEROW_LABEL:
        return LEDGER_HEDGE
    if h == NET_GAIN_WATERCOURSE_LABEL:
        return LEDGER_WATER
    # Lookup in catalog
    m = catalog[catalog["habitat_name"].astype(str).str.strip() == h]
    umb = sstr(m.iloc[0]["UmbrellaType"]) if not m.empty and "UmbrellaType" in m.columns else ""
    umb = umb.lower()
    if umb == LEDGER_HEDGE:
        return LEDGER_HEDGE
    if umb == LEDGER_WATER:
        return LEDGER_WATER
    return LEDGER_AREA


def is_hedgerow(name: str) -> bool:
    """Check if habitat is hedgerow type"""
    n = sstr(name).lower()
    if "hedgerow" in n or "hedge row" in n:
        return True
    if name == NET_GAIN_HEDGEROW_LABEL:
        return True
    return False


def is_watercourse(name: str) -> bool:
    """Check if habitat is watercourse type"""
    n = sstr(name).lower()
    keywords = ["watercourse", "water course", "river", "stream", "canal", "ditch"]
    for kw in keywords:
        if kw in n:
            return True
    if name == NET_GAIN_WATERCOURSE_LABEL:
        return True
    return False


# ================= Tier calculation =================
def tier_for_bank(bank_lpa: str, bank_nca: str,
                  target_lpa: str, target_nca: str,
                  lpa_neigh: List[str], nca_neigh: List[str],
                  lpa_neigh_norm: List[str], nca_neigh_norm: List[str]) -> str:
    """Calculate tier (local/adjacent/far) for a bank
    
    Returns best (closest) category across both axes:
    - local: if LPA matches OR NCA matches
    - adjacent: if LPA is neighbor OR NCA is neighbor
    - far: otherwise
    """
    blpa_norm = norm_name(bank_lpa)
    bnca_norm = norm_name(bank_nca)
    tlpa_norm = norm_name(target_lpa)
    tnca_norm = norm_name(target_nca)
    
    # Evaluate LPA axis independently
    lpa_same = blpa_norm and tlpa_norm and blpa_norm == tlpa_norm
    lpa_neighbour = blpa_norm and blpa_norm in lpa_neigh_norm
    
    # Evaluate NCA axis independently  
    nca_same = bnca_norm and tnca_norm and bnca_norm == tnca_norm
    nca_neighbour = bnca_norm and bnca_norm in nca_neigh_norm
    
    # Return best (closest) category across both axes
    if lpa_same or nca_same:
        return "local"  # Local > Adjacent > Far
    elif lpa_neighbour or nca_neighbour:
        return "adjacent"  # Adjacent > Far
    else:
        return "far"


# ================= Contract size selection =================
def select_contract_size(total_units: float, present: List[str]) -> str:
    """Select contract size based on total units"""
    tiers = set([sstr(x).lower() for x in present])
    if "fractional" in tiers and total_units < 0.1: 
        return "fractional"
    if "small" in tiers and total_units < 2.5: 
        return "small"
    if "medium" in tiers and total_units < 15: 
        return "medium"
    # Fallback: select largest available size
    for t in ["large", "medium", "small", "fractional"]:
        if t in tiers: 
            return t
    return sstr(next(iter(present), "small")).lower()


def get_admin_fee_for_contract_size(contract_size: str) -> float:
    """Get admin fee for contract size"""
    size_lower = contract_size.lower()
    if size_lower == "fractional":
        return ADMIN_FEE_FRACTIONAL_GBP
    return ADMIN_FEE_GBP


def select_size_for_demand(demand_df: pd.DataFrame, pricing_df: pd.DataFrame) -> str:
    """Select contract size based on demand"""
    present = pricing_df["contract_size"].drop_duplicates().tolist()
    total = float(demand_df["units_required"].sum())
    return select_contract_size(total, present)


# ================= Discount Helpers =================
def apply_tier_up_discount(contract_size: str, available_sizes: List[str]) -> str:
    """Apply tier_up discount: move contract size one level up"""
    size_lower = contract_size.lower()
    available_lower = [s.lower() for s in available_sizes]
    
    size_hierarchy = ["fractional", "small", "medium", "large"]
    
    try:
        current_index = size_hierarchy.index(size_lower)
    except ValueError:
        return contract_size
    
    for next_index in range(current_index + 1, len(size_hierarchy)):
        next_size = size_hierarchy[next_index]
        if next_size in available_lower:
            return next_size
    
    return contract_size


def apply_percentage_discount(unit_price: float, discount_percentage: float) -> float:
    """Apply percentage discount to unit price"""
    return unit_price * (1.0 - discount_percentage / 100.0)


# ================= Bank Key normalization =================
def make_bank_key_col(df: pd.DataFrame, banks_df: pd.DataFrame) -> pd.DataFrame:
    """Add BANK_KEY column to dataframe"""
    out = df.copy()
    has_df_name = "bank_name" in out.columns and out["bank_name"].astype(str).str.strip().ne("").any()
    if not has_df_name:
        if "bank_id" in out.columns and "bank_id" in banks_df.columns and "bank_name" in banks_df.columns:
            m = banks_df[["bank_id","bank_name"]].drop_duplicates()
            out = out.merge(m, on="bank_id", how="left")
    if "bank_name" in out.columns:
        out["BANK_KEY"] = out["bank_name"].where(out["bank_name"].astype(str).str.strip().ne(""), out.get("bank_id"))
    else:
        out["BANK_KEY"] = out.get("bank_id")
    out["BANK_KEY"] = out["BANK_KEY"].map(sstr)
    return out


# ================= Trading Rules =================
def enforce_catalog_rules_official(demand_row, supply_row, dist_levels_map_local, explicit_rule: bool) -> bool:
    """Enforce catalog-based trading rules for area habitats"""
    dh = sstr(demand_row.get("habitat_name"))
    sh = sstr(supply_row.get("habitat_name"))
    
    # Net Gain label can be matched by any Low
    if dh == NET_GAIN_LABEL:
        s_key = sstr(supply_row.get("distinctiveness_key")).lower()
        return s_key == "low"
    
    # Exact habitat match always allowed
    if dh == sh:
        return True
    
    # Check distinctiveness trading rules
    d_key = sstr(demand_row.get("distinctiveness_key")).lower()
    s_key = sstr(supply_row.get("distinctiveness_key")).lower()
    
    # Same-or-higher distinctiveness
    if d_key not in dist_levels_map_local or s_key not in dist_levels_map_local:
        return False
    if dist_levels_map_local[s_key] < dist_levels_map_local[d_key]:
        return False
    
    # Special case: Low/Net Gain can be matched by any Low
    if d_key == "low" or dh == NET_GAIN_LABEL:
        return s_key == "low"
    
    # For other distinctiveness levels, require exact habitat match or explicit rule
    if not explicit_rule:
        return dh == sh
    
    return True


def enforce_hedgerow_rules(demand_row, supply_row, dist_levels_map_local) -> bool:
    """Enforce hedgerow trading rules"""
    dh = sstr(demand_row.get("habitat_name"))
    sh = sstr(supply_row.get("habitat_name"))
    
    # Net Gain (Hedgerows) can be matched by any hedgerow
    if dh == NET_GAIN_LABEL or dh == "Net Gain (Hedgerows)":
        return is_hedgerow(sh)
    
    # Exact match always allowed
    if dh == sh:
        return True
    
    # Check distinctiveness
    d_key = sstr(demand_row.get("distinctiveness_key")).lower()
    s_key = sstr(supply_row.get("distinctiveness_key")).lower()
    
    if d_key not in dist_levels_map_local or s_key not in dist_levels_map_local:
        return False
    if dist_levels_map_local[s_key] < dist_levels_map_local[d_key]:
        return False
    
    return True


def enforce_watercourse_rules(demand_row, supply_row, dist_levels_map_local) -> bool:
    """Enforce watercourse trading rules"""
    dh = sstr(demand_row.get("habitat_name"))
    sh = sstr(supply_row.get("habitat_name"))
    
    # Net Gain (Watercourses) can be matched by any watercourse
    if dh == NET_GAIN_WATERCOURSE_LABEL:
        return is_watercourse(sh)
    
    # Exact match always allowed
    if dh == sh:
        return True
    
    # Check distinctiveness
    d_key = sstr(demand_row.get("distinctiveness_key")).lower()
    s_key = sstr(supply_row.get("distinctiveness_key")).lower()
    
    if d_key not in dist_levels_map_local or s_key not in dist_levels_map_local:
        return False
    if dist_levels_map_local[s_key] < dist_levels_map_local[d_key]:
        return False
    
    return True


# ================= Load Backend =================
def load_backend() -> Dict[str, pd.DataFrame]:
    """Load all reference/config tables from database"""
    try:
        return repo.fetch_all_reference_tables()
    except Exception as e:
        raise RuntimeError(f"Failed to load reference tables from database: {e}")


def build_dist_levels_map(backend: Dict[str, pd.DataFrame]) -> Dict[str, float]:
    """
    Build distinctiveness levels map from backend DistinctivenessLevels table.
    This is used for trading rule enforcement.
    """
    dist_levels_map = {
        sstr(r["distinctiveness_name"]): float(r["level_value"])
        for _, r in backend["DistinctivenessLevels"].iterrows()
    }
    # Add lowercase versions for case-insensitive lookup
    dist_levels_map.update({k.lower(): v for k, v in list(dist_levels_map.items())})
    return dist_levels_map


# ================= Optimization Functions =================
# These will be added in the next step - they are very large
# For now, create placeholder stubs

def prepare_options(demand_df: pd.DataFrame,
                   chosen_size: str,
                   target_lpa: str, target_nca: str,
                   lpa_neigh: List[str], nca_neigh: List[str],
                   lpa_neigh_norm: List[str], nca_neigh_norm: List[str],
                   backend: Dict[str, pd.DataFrame],
                   promoter_discount_type: str = None,
                   promoter_discount_value: float = None) -> Tuple[List[dict], Dict[str, float], Dict[str, str]]:
    """Prepare options for area habitats - PLACEHOLDER"""
    # This is a complex function that will need to be extracted from app.py
    # For now, return empty structures
    return [], {}, {}


def prepare_hedgerow_options(demand_df: pd.DataFrame,
                             chosen_size: str,
                             target_lpa: str, target_nca: str,
                             lpa_neigh: List[str], nca_neigh: List[str],
                             lpa_neigh_norm: List[str], nca_neigh_norm: List[str],
                             backend: Dict[str, pd.DataFrame],
                             promoter_discount_type: str = None,
                             promoter_discount_value: float = None) -> Tuple[List[dict], Dict[str, float], Dict[str, str]]:
    """Prepare options for hedgerow habitats - PLACEHOLDER"""
    return [], {}, {}


def prepare_watercourse_options(demand_df: pd.DataFrame,
                                chosen_size: str,
                                target_lpa: str, target_nca: str,
                                lpa_neigh: List[str], nca_neigh: List[str],
                                lpa_neigh_norm: List[str], nca_neigh_norm: List[str],
                                backend: Dict[str, pd.DataFrame],
                                promoter_discount_type: str = None,
                                promoter_discount_value: float = None) -> Tuple[List[dict], Dict[str, float], Dict[str, str]]:
    """Build candidate options for watercourse ledger using UmbrellaType='watercourse'."""
    Banks = backend["Banks"].copy()
    Pricing = backend["Pricing"].copy()
    Catalog = backend["HabitatCatalog"].copy()
    Stock = backend["Stock"].copy()
    
    # Build dist_levels_map from backend
    dist_levels_map = build_dist_levels_map(backend)

    # Normalise strings
    for df, cols in [
        (Banks,   ["bank_id","bank_name","BANK_KEY","lpa_name","nca_name"]),
        (Catalog, ["habitat_name","broader_type","distinctiveness_name","UmbrellaType"]),
        (Stock,   ["habitat_name","stock_id","bank_id","quantity_available","BANK_KEY"]),
        (Pricing, ["habitat_name","contract_size","tier","bank_id","BANK_KEY","price"])
    ]:
        if not df.empty:
            for c in cols:
                if c in df.columns:
                    df[c] = df[c].map(sstr)

    # Ensure BANK_KEY exists on Stock
    Stock = make_bank_key_col(Stock, Banks)

    # Keep only watercourse habitats by UmbrellaType
    wc_catalog = Catalog[Catalog["UmbrellaType"].astype(str).str.lower() == "watercourse"]
    wc_habs = set(wc_catalog["habitat_name"].astype(str))

    stock_full = (
        Stock[Stock["habitat_name"].isin(wc_habs)]
        .merge(Banks[["bank_id","bank_name","lpa_name","nca_name"]].drop_duplicates(),
               on="bank_id", how="left")
        .merge(Catalog[["habitat_name","broader_type","distinctiveness_name","UmbrellaType"]],
               on="habitat_name", how="left")
    )

    # Apply tier_up discount to contract size if active
    pricing_contract_size = chosen_size
    if promoter_discount_type == "tier_up":
        available_sizes = Pricing["contract_size"].drop_duplicates().tolist()
        pricing_contract_size = apply_tier_up_discount(chosen_size, available_sizes)

    pricing_enriched = (
        Pricing[(Pricing["contract_size"] == pricing_contract_size) & (Pricing["habitat_name"].isin(wc_habs))]
        .merge(Catalog[["habitat_name","broader_type","distinctiveness_name","UmbrellaType"]],
               on="habitat_name", how="left")
    )

    options: List[dict] = []
    stock_caps: Dict[str, float] = {}
    stock_bankkey: Dict[str, str] = {}

    for demand_idx, demand_row in demand_df.iterrows():
        dem_hab = sstr(demand_row.get("habitat_name"))

        # Only handle watercourse demands (including NG watercourses)
        # Uses UmbrellaType to decide ledger
        if "UmbrellaType" in Catalog.columns:
            if dem_hab != NET_GAIN_WATERCOURSE_LABEL:
                m = Catalog[Catalog["habitat_name"].astype(str).str.strip() == dem_hab]
                umb = sstr(m.iloc[0]["UmbrellaType"]).lower() if not m.empty else ""
                if umb != "watercourse":
                    continue
        else:
            # Fallback: text heuristic (not ideal, but keeps behavior if column is missing)
            if dem_hab != NET_GAIN_WATERCOURSE_LABEL and not is_watercourse(dem_hab):
                continue

        demand_units = float(demand_row.get("units_required", 0.0))
        if demand_units <= 0:
            continue

        if dem_hab == NET_GAIN_WATERCOURSE_LABEL:
            demand_dist = "Low"     # NG trades like Low within this ledger
            demand_broader = ""
        else:
            cat_match = Catalog[Catalog["habitat_name"] == dem_hab]
            if cat_match.empty:
                continue
            demand_dist = sstr(cat_match.iloc[0]["distinctiveness_name"])
            demand_broader = sstr(cat_match.iloc[0]["broader_type"])

        demand_cat_row = pd.Series({
            "habitat_name": dem_hab,
            "distinctiveness_name": demand_dist,
            "broader_type": demand_broader
        })

        for _, supply_row in stock_full.iterrows():
            supply_hab = sstr(supply_row["habitat_name"])
            if supply_hab not in wc_habs:
                continue

            # Ledger-specific rule check
            if not enforce_watercourse_rules(demand_cat_row, supply_row, dist_levels_map):
                continue

            bank_key = sstr(supply_row["BANK_KEY"])
            stock_id = sstr(supply_row["stock_id"])
            qty_avail = float(supply_row.get("quantity_available", 0.0))
            if qty_avail <= 0:
                continue

            # For watercourses: Use LPA/NCA based tiering to estimate SRM
            # Without catchment data, we map geographic tier to SRM tier
            # local tier → SRM 1.0 (local catchment)
            # adjacent tier → SRM 4/3 (adjacent catchment) 
            # far tier → SRM 2.0 (national)
            geographic_tier = tier_for_bank(
                sstr(supply_row.get("lpa_name")), sstr(supply_row.get("nca_name")),
                target_lpa, target_nca,
                lpa_neigh, nca_neigh, lpa_neigh_norm, nca_neigh_norm
            )
            
            # Map geographic tier to SRM and unit multiplier
            if geographic_tier == "local":
                srm = 1.0
                unit_multiplier = 1.0  # 1x for local
                tier = "local"
            elif geographic_tier == "adjacent":
                srm = 4/3
                unit_multiplier = 4/3  # 4/3x for adjacent
                tier = "adjacent"
            else:  # far
                srm = 2.0
                unit_multiplier = 2.0  # 2x for national/far
                tier = "far"

            # Find exact price, else fallback to any watercourse price in same bank/tier
            pr_match = pricing_enriched[
                (pricing_enriched["BANK_KEY"] == bank_key) &
                (pricing_enriched["tier"] == tier) &
                (pricing_enriched["habitat_name"] == supply_hab)
            ]
            if pr_match.empty:
                pr_match = pricing_enriched[
                    (pricing_enriched["BANK_KEY"] == bank_key) &
                    (pricing_enriched["tier"] == tier)
                ]
                if pr_match.empty:
                    continue
                price = float(pr_match.iloc[0]["price"])
            else:
                price = float(pr_match.iloc[0]["price"])

            # Apply percentage discount if active
            if promoter_discount_type == "percentage" and promoter_discount_value:
                price = apply_percentage_discount(price, promoter_discount_value)

            options.append({
                "demand_idx": demand_idx,
                "demand_habitat": dem_hab,
                "supply_habitat": supply_hab,
                "bank_id": sstr(supply_row.get("bank_id", "")),
                "bank_name": sstr(supply_row.get("bank_name", "")),
                "BANK_KEY": bank_key,
                "stock_id": stock_id,
                "tier": tier,
                "srm": srm,  # Store SRM for reference
                "unit_price": price,
                "cost_per_unit": price,
                "stock_use": {stock_id: unit_multiplier},  # Apply SRM unit multiplier
                "type": "normal",
                "proximity": tier,
            })

            stock_caps[stock_id] = qty_avail
            stock_bankkey[stock_id] = bank_key

    return options, stock_caps, stock_bankkey


def optimise(demand_df: pd.DataFrame,
             target_lpa: str, target_nca: str,
             lpa_neigh: List[str], nca_neigh: List[str],
             lpa_neigh_norm: List[str], nca_neigh_norm: List[str],
             backend: Dict[str, pd.DataFrame] = None,
             promoter_discount_type: str = None,
             promoter_discount_value: float = None) -> Tuple[pd.DataFrame, float, str]:
    """
    Run PuLP optimization - MAIN OPTIMIZER
    
    Args:
        demand_df: DataFrame with habitat requirements (habitat_name, units_required)
        target_lpa: Target LPA name
        target_nca: Target NCA name
        lpa_neigh: List of neighboring LPA names
        nca_neigh: List of neighboring NCA names
        lpa_neigh_norm: Normalized neighboring LPA names
        nca_neigh_norm: Normalized neighboring NCA names
        backend: Backend data dictionary (if None, will load from database)
        promoter_discount_type: Optional promoter discount type ('tier_up', 'percentage', 'no_discount')
        promoter_discount_value: Optional promoter discount value
    
    Returns:
        Tuple of (allocation_df, total_cost, status_message)
    """
    # Load backend if not provided
    if backend is None:
        backend = load_backend()
    
    # PLACEHOLDER: Full optimization logic needs to be extracted from app.py
    # This is a complex function with ~400 lines of code
    raise NotImplementedError("optimise function needs full implementation - placeholder only")


def generate_client_report_table_fixed(alloc_df: pd.DataFrame, 
                                       demand_df: pd.DataFrame, 
                                       total_cost: float, 
                                       admin_fee: float,
                                       client_name: str = "", 
                                       ref_number: str = "",
                                       location: str = "",
                                       backend: Dict[str, pd.DataFrame] = None,
                                       manual_hedgerow_rows: List[dict] = None,
                                       manual_watercourse_rows: List[dict] = None,
                                       manual_area_rows: List[dict] = None,
                                       removed_allocation_rows: List[int] = None,
                                       promoter_name: str = None,
                                       promoter_discount_type: str = None,
                                       promoter_discount_value: float = None,
                                       suo_discount_fraction: float = 0.0) -> Tuple[pd.DataFrame, str]:
    """
    Generate client report table and email body
    
    Args:
        alloc_df: Allocation results DataFrame
        demand_df: Demand DataFrame
        total_cost: Total cost
        admin_fee: Admin fee
        client_name: Client name for report
        ref_number: Reference number for report
        location: Site location
        backend: Backend data dictionary (if None, will load from database)
        manual_hedgerow_rows: Manual hedgerow entries
        manual_watercourse_rows: Manual watercourse entries
        manual_area_rows: Manual area entries
        removed_allocation_rows: Removed allocation row IDs
        promoter_name: Promoter name
        promoter_discount_type: Discount type
        promoter_discount_value: Discount value
        suo_discount_fraction: SUO discount fraction
    
    Returns:
        Tuple of (report_df, email_body)
    """
    # Load backend if not provided
    if backend is None:
        backend = load_backend()
    
    # PLACEHOLDER: Full report generation logic needs to be extracted from app.py
    # This is a large function with complex formatting logic
    raise NotImplementedError("generate_client_report_table_fixed function needs full implementation - placeholder only")
def prepare_options(demand_df: pd.DataFrame,
                    chosen_size: str,
                    target_lpa: str, target_nca: str,
                    lpa_neigh: List[str], nca_neigh: List[str],
                    lpa_neigh_norm: List[str], nca_neigh_norm: List[str],
                    backend: Dict[str, pd.DataFrame],
                    promoter_discount_type: str = None,
                    promoter_discount_value: float = None) -> Tuple[List[dict], Dict[str, float], Dict[str, str]]:
    Banks = backend["Banks"].copy()
    Pricing = backend["Pricing"].copy()
    Catalog = backend["HabitatCatalog"].copy()
    Stock = backend["Stock"].copy()
    Trading = backend.get("TradingRules", pd.DataFrame())
    
    # Build dist_levels_map from backend
    dist_levels_map = build_dist_levels_map(backend)

    for df, cols in [
        (Banks, ["bank_id","bank_name","BANK_KEY","lpa_name","nca_name","lat","lon","postcode","address"]),
        (Catalog, ["habitat_name","broader_type","distinctiveness_name"]),
        (Stock, ["habitat_name","stock_id","bank_id","quantity_available","bank_name","BANK_KEY"]),
        (Pricing, ["habitat_name","contract_size","tier","bank_id","BANK_KEY","price","broader_type","distinctiveness_name","bank_name"]),
        (Trading, ["demand_habitat","allowed_supply_habitat","min_distinctiveness_name","companion_habitat"])
    ]:
        if not df.empty:
            for c in cols:
                if c in df.columns:
                    df[c] = df[c].map(sstr)

    Stock = make_bank_key_col(Stock, Banks)

    stock_full = Stock.merge(
        Banks[["bank_id","bank_name","lpa_name","nca_name"]],
        on="bank_id", how="left"
    ).merge(Catalog, on="habitat_name", how="left")
    stock_full = stock_full[~stock_full["habitat_name"].map(is_hedgerow)].copy()

    # Use promoter discount settings from parameters (already in function signature)
    
    # Apply tier_up discount to contract size if active
    pricing_contract_size = chosen_size
    if promoter_discount_type == "tier_up":
        available_sizes = Pricing["contract_size"].drop_duplicates().tolist()
        pricing_contract_size = apply_tier_up_discount(chosen_size, available_sizes)
    
    pricing_cs = Pricing[Pricing["contract_size"] == pricing_contract_size].copy()

    pc_join = pricing_cs.merge(
        Catalog[["habitat_name","broader_type","distinctiveness_name"]],
        on="habitat_name", how="left", suffixes=("", "_cat")
    )
    pc_join["broader_type_eff"] = np.where(pc_join["broader_type"].astype(str).str.len()>0,
                                           pc_join["broader_type"], pc_join["broader_type_cat"])
    pc_join["distinctiveness_name_eff"] = np.where(pc_join["distinctiveness_name"].astype(str).str.len()>0,
                                                   pc_join["distinctiveness_name"], pc_join["distinctiveness_name_cat"])
    for c in ["broader_type_eff", "distinctiveness_name_eff", "tier", "bank_id", "habitat_name", "BANK_KEY", "bank_name"]:
        if c in pc_join.columns:
            pc_join[c] = pc_join[c].map(sstr)
    pricing_enriched = pc_join[~pc_join["habitat_name"].map(is_hedgerow)].copy()

    def dval(name: Optional[str]) -> float:
        key = sstr(name)
        return dist_levels_map.get(key, dist_levels_map.get(key.lower(), -1e9))

    def find_price_for_supply(bank_key: str,
                              supply_habitat: str,
                              tier: str,
                              demand_broader: str,
                              demand_dist: str) -> Optional[Tuple[float, str, str]]:
        # Exact row first
        pr_exact = pricing_enriched[(pricing_enriched["BANK_KEY"] == bank_key) &
                                    (pricing_enriched["tier"] == tier) &
                                    (pricing_enriched["habitat_name"] == supply_habitat)]
        if not pr_exact.empty:
            r = pr_exact.sort_values("price").iloc[0]
            return float(r["price"]), "exact", sstr(r["habitat_name"])

        d_key = sstr(demand_dist).lower()

        # Low / Net Gain — cheapest per bank/tier as proxy if exact not present
        if d_key == "low":
            grp = pricing_enriched[(pricing_enriched["BANK_KEY"] == bank_key) &
                                   (pricing_enriched["tier"] == tier)]
            if not grp.empty:
                r = grp.sort_values("price").iloc[0]
                return float(r["price"]), "any-low-proxy", sstr(r["habitat_name"])
            return None

        if d_key == "medium":
            d_num = dval(demand_dist)
            grp = pricing_enriched[(pricing_enriched["BANK_KEY"] == bank_key) &
                                   (pricing_enriched["tier"] == tier)]
            grp = grp[(grp["broader_type_eff"].astype(str).str.len() > 0) &
                      (grp["distinctiveness_name_eff"].astype(str).str.len() > 0)]
            if grp.empty:
                return None
            grp_same = grp[grp["broader_type_eff"].map(sstr) == sstr(demand_broader)].copy()
            if not grp_same.empty:
                grp_same["_dval"] = grp_same["distinctiveness_name_eff"].map(dval)
                grp_same = grp_same[grp_same["_dval"] >= d_num]
                if not grp_same.empty:
                    r = grp_same.sort_values("price").iloc[0]
                    return float(r["price"]), "group-proxy", sstr(r["habitat_name"])
            grp_any_higher = grp.assign(_dval=grp["distinctiveness_name_eff"].map(dval))
            grp_any_higher = grp_any_higher[grp_any_higher["_dval"] > d_num]
            if not grp_any_higher.empty:
                r = grp_any_higher.sort_values("price").iloc[0]
                return float(r["price"]), "group-proxy", sstr(r["habitat_name"])
            return None

        return None  # High/Very High: exact only

    def find_catalog_name(substr: str) -> Optional[str]:
        m = Catalog[Catalog["habitat_name"].str.contains(substr, case=False, na=False)]
        return sstr(m["habitat_name"].iloc[0]) if not m.empty else None

    ORCHARD_NAME = find_catalog_name("Traditional Orchard")
    SCRUB_NAME = find_catalog_name("Mixed Scrub") or find_catalog_name("scrub") or find_catalog_name("bramble")

    options: List[dict] = []
    stock_caps: Dict[str, float] = {}
    stock_bankkey: Dict[str, str] = {}
    for _, s in Stock.iterrows():
        stock_caps[sstr(s["stock_id"])] = float(s.get("quantity_available", 0) or 0.0)
        stock_bankkey[sstr(s["stock_id"])] = sstr(s.get("BANK_KEY") or s.get("bank_id"))

    for di, drow in demand_df.iterrows():
        dem_hab = sstr(drow["habitat_name"])
        
        # Skip hedgerow demand in area habitat options (hedgerows handled separately)
        if is_hedgerow(dem_hab):
            continue

        if dem_hab == NET_GAIN_LABEL:
            d_broader = ""
            d_dist = "Low"
        else:
            dcat = Catalog[Catalog["habitat_name"] == dem_hab]
            d_broader = sstr(dcat["broader_type"].iloc[0]) if not dcat.empty else ""
            d_dist = sstr(dcat["distinctiveness_name"].iloc[0]) if not dcat.empty else ""

        # Candidate stock by legality
        cand_parts = []
        explicit = False
        if "TradingRules" in backend and not backend["TradingRules"].empty and dem_hab in set(backend["TradingRules"]["demand_habitat"].astype(str)):
            explicit = True
            for _, rule in backend["TradingRules"][backend["TradingRules"]["demand_habitat"] == dem_hab].iterrows():
                sh = sstr(rule["allowed_supply_habitat"])
                if is_hedgerow(sh):
                    continue
                s_min = sstr(rule.get("min_distinctiveness_name"))
                df_s = stock_full[stock_full["habitat_name"] == sh].copy()
                if s_min:
                    df_s = df_s[df_s["distinctiveness_name"].map(lambda x: dist_levels_map.get(sstr(x), -1e9)) >=
                                dist_levels_map.get(sstr(s_min), -1e9)]
                if not df_s.empty: cand_parts.append(df_s)

        if not cand_parts:
            key = sstr(d_dist).lower()
            if key == "low" or dem_hab == NET_GAIN_LABEL:
                df_s = stock_full.copy()
            elif key == "medium":
                same_group = stock_full["broader_type"].fillna("").astype(str).map(sstr).eq(d_broader)
                higher_dist = stock_full["distinctiveness_name"].map(lambda x: dist_levels_map.get(sstr(x), -1e9)) > \
                              dist_levels_map.get(sstr(d_dist), -1e9)
                df_s = stock_full[same_group | higher_dist].copy()
            else:
                df_s = stock_full[stock_full["habitat_name"] == dem_hab].copy()
            if not df_s.empty: cand_parts.append(df_s)

        if not cand_parts:
            continue

        candidates = pd.concat(cand_parts, ignore_index=True)
        candidates = candidates[~candidates["habitat_name"].map(is_hedgerow)].copy()

        # Single-habitat options
        for _, srow in candidates.iterrows():
            if not enforce_catalog_rules_official(
                pd.Series({"habitat_name": dem_hab, "broader_type": d_broader, "distinctiveness_name": d_dist}),
                srow, dist_levels_map, explicit_rule=explicit
            ):
                continue
            tier = tier_for_bank(
                srow.get("lpa_name",""), srow.get("nca_name",""),
                target_lpa, target_nca,
                lpa_neigh, nca_neigh, lpa_neigh_norm, nca_neigh_norm
            )
            
            bank_key = sstr(srow.get("BANK_KEY") or srow.get("bank_name") or srow.get("bank_id"))
            price_info = find_price_for_supply(
                bank_key=bank_key,
                supply_habitat=srow["habitat_name"],
                tier=tier,  # Use actual geographic tier (tier_up already applied to contract size)
                demand_broader=d_broader,
                demand_dist=d_dist,
            )
            if not price_info:
                continue

            unit_price, price_source, price_hab_used = price_info
            
            # Apply percentage discount if active
            if promoter_discount_type == "percentage" and promoter_discount_value:
                unit_price = apply_percentage_discount(unit_price, promoter_discount_value)
            
            cap = float(srow.get("quantity_available", 0) or 0.0)
            if cap <= 0:
                continue
            options.append({
                "type": "normal",
                "demand_idx": di,
                "demand_habitat": dem_hab,
                "BANK_KEY": bank_key,
                "bank_name": sstr(srow.get("bank_name")),
                "bank_id": sstr(srow.get("bank_id")),
                "supply_habitat": srow["habitat_name"],
                "tier": tier,  # Keep original tier for reporting
                "proximity": tier,
                "unit_price": float(unit_price),  # Use discounted price
                "stock_use": {sstr(srow["stock_id"]): 1.0},
                "price_source": price_source,
                "price_habitat": price_hab_used,
            })

        # Paired allocations for ANY demand at ADJACENT and FAR tiers
        # When SRM > 1.0, pairing with a cheaper habitat can reduce effective cost
        banks_keys = stock_full["BANK_KEY"].dropna().unique().tolist()
        for bk in banks_keys:
            # Get stock rows for the demand habitat at this bank
            demand_rows = candidates[candidates["BANK_KEY"] == bk].copy()
            if demand_rows.empty:
                continue
            
            # Process each demand habitat stock entry (includes substitutes from trading rules)
            for _, d_stock in demand_rows.iterrows():
                cap_d = float(d_stock.get("quantity_available", 0) or 0.0)
                if cap_d <= 0:
                    continue
                
                # Get supply habitat name (may be different from demand if it's a substitute)
                supply_hab = sstr(d_stock["habitat_name"])
                
                # Get "companion" candidates: any area habitat with positive stock
                # excluding the supply habitat itself to avoid self-pairing
                companion_candidates = stock_full[
                    (stock_full["BANK_KEY"] == bk) &
                    (stock_full["habitat_name"] != supply_hab) &
                    (~stock_full["habitat_name"].map(is_hedgerow)) &
                    (stock_full["quantity_available"].astype(float) > 0)
                ].copy()
                
                if companion_candidates.empty:
                    continue
                
                # For each tier (adjacent and far), find the best companion
                for target_tier in ["adjacent", "far"]:
                    # Check if supply habitat is at this tier
                    tier_demand = tier_for_bank(
                        sstr(d_stock.get("lpa_name")), sstr(d_stock.get("nca_name")),
                        target_lpa, target_nca, lpa_neigh, nca_neigh, lpa_neigh_norm, nca_neigh_norm
                    )
                    # Only create paired options for the actual tier of the supply habitat
                    if tier_demand != target_tier:
                        continue
                    
                    # Get supply habitat price at this tier (not demand habitat - use actual supply)
                    pi_demand = find_price_for_supply(bk, supply_hab, target_tier, d_broader, d_dist)
                    if not pi_demand:
                        continue
                    price_demand = float(pi_demand[0])
                    
                    # Find companion candidates at this tier with valid prices
                    tier_companion_candidates = []
                    for _, comp_row in companion_candidates.iterrows():
                        tier_test = tier_for_bank(
                            sstr(comp_row.get("lpa_name")), sstr(comp_row.get("nca_name")),
                            target_lpa, target_nca, lpa_neigh, nca_neigh, lpa_neigh_norm, nca_neigh_norm
                        )
                        if tier_test != target_tier:
                            continue
                        
                        # Check if we can price this companion (use proxy pricing for flexibility)
                        pi_comp = find_price_for_supply(bk, comp_row["habitat_name"], target_tier, d_broader, d_dist)
                        if not pi_comp:
                            continue
                        
                        tier_companion_candidates.append({
                            "row": comp_row,
                            "price": float(pi_comp[0]),
                            "price_info": pi_comp,
                            "cap": float(comp_row.get("quantity_available", 0) or 0.0)
                        })
                    
                    if not tier_companion_candidates:
                        continue
                    
                    # Sort by price (ascending) - select the CHEAPEST companion
                    tier_companion_candidates.sort(key=lambda x: (x["price"], -x["cap"]))
                    best_companion = tier_companion_candidates[0]
                    
                    price_companion = best_companion["price"]
                    comp_row = best_companion["row"]
                    pi_comp = best_companion["price_info"]
                    
                    # Calculate blended price and stock_use based on tier
                    # SRM is already baked into pricing, so we use weighted average
                    # Adjacent: 3/4 main component + 1/4 companion
                    # Far: 1/2 main component + 1/2 companion
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
                    
                    # Apply percentage discount if active (to blended price)
                    if promoter_discount_type == "percentage" and promoter_discount_value:
                        blended_price = apply_percentage_discount(blended_price, promoter_discount_value)
                    
                    # Always add paired option and let optimizer choose the best allocation
                    options.append({
                        "type": "paired",
                        "demand_idx": di,
                        "demand_habitat": dem_hab,  # Keep original demand habitat for matching
                        "BANK_KEY": bk,
                        "bank_name": sstr(d_stock.get("bank_name")),
                        "bank_id": sstr(d_stock.get("bank_id")),
                        "supply_habitat": f"{pi_demand[2]} + {pi_comp[2]}",  # Use pricing habitats
                        "tier": target_tier,
                        "proximity": target_tier,
                        "unit_price": blended_price,
                        "stock_use": {sstr(d_stock["stock_id"]): stock_use_demand, sstr(comp_row["stock_id"]): stock_use_companion},
                        "price_source": "paired",
                        "price_habitat": f"{pi_demand[2]} + {pi_comp[2]}",
                        "paired_parts": [
                            {"habitat": pi_demand[2], "unit_price": price_demand, "stock_use": stock_use_demand},
                            {"habitat": pi_comp[2], "unit_price": price_companion, "stock_use": stock_use_companion},
                        ],
                    })

    return options, stock_caps, stock_bankkey


def prepare_hedgerow_options(demand_df: pd.DataFrame,
                              chosen_size: str,
                              target_lpa: str, target_nca: str,
                              lpa_neigh: List[str], nca_neigh: List[str],
                              lpa_neigh_norm: List[str], nca_neigh_norm: List[str],
                              backend: Dict[str, pd.DataFrame],
                              promoter_discount_type: str = None,
                              promoter_discount_value: float = None) -> Tuple[List[dict], Dict[str, float], Dict[str, str]]:
    """Prepare hedgerow unit options using specific hedgerow trading rules"""
    Banks = backend["Banks"].copy()
    Pricing = backend["Pricing"].copy()
    Catalog = backend["HabitatCatalog"].copy()
    Stock = backend["Stock"].copy()
    
    # Build dist_levels_map from backend
    dist_levels_map = build_dist_levels_map(backend)
    
    for df, cols in [
        (Banks, ["bank_id","bank_name","BANK_KEY","lpa_name","nca_name"]),
        (Catalog, ["habitat_name","broader_type","distinctiveness_name"]),
        (Stock, ["habitat_name","stock_id","bank_id","quantity_available"]),
        (Pricing, ["habitat_name","contract_size","tier","bank_id","BANK_KEY","price"])
    ]:
        if not df.empty:
            for c in cols:
                if c in df.columns:
                    df[c] = df[c].map(sstr)
    
    Stock = make_bank_key_col(Stock, Banks)
    
    # Filter for ONLY hedgerow habitats
    # Ensure bank_name is available from Banks
    banks_cols = ["bank_id"]
    for col in ["bank_name", "lpa_name", "nca_name"]:
        if col in Banks.columns:
            banks_cols.append(col)
    
    stock_full = Stock.merge(
        Banks[banks_cols].drop_duplicates(),
        on="bank_id", how="left"
    ).merge(Catalog, on="habitat_name", how="left")
    
    # Ensure bank_name exists (fallback to BANK_KEY if not present)
    if "bank_name" not in stock_full.columns:
        if "BANK_KEY" in stock_full.columns:
            stock_full["bank_name"] = stock_full["BANK_KEY"]
        else:
            stock_full["bank_name"] = stock_full["bank_id"]
    
    stock_full = stock_full[stock_full["habitat_name"].map(is_hedgerow)].copy()
    
    # Use promoter discount settings from parameters (already in function signature)
    
    # Apply tier_up discount to contract size if active
    pricing_contract_size = chosen_size
    if promoter_discount_type == "tier_up":
        available_sizes = Pricing["contract_size"].drop_duplicates().tolist()
        pricing_contract_size = apply_tier_up_discount(chosen_size, available_sizes)
    
    pricing_cs = Pricing[Pricing["contract_size"] == pricing_contract_size].copy()
    pricing_enriched = pricing_cs.merge(
        Catalog[["habitat_name","broader_type","distinctiveness_name"]],
        on="habitat_name", how="left"
    )
    pricing_enriched = pricing_enriched[pricing_enriched["habitat_name"].map(is_hedgerow)].copy()
    
    options = []
    stock_caps = {}
    stock_bankkey = {}
    
    for demand_idx, demand_row in demand_df.iterrows():
        dem_hab = sstr(demand_row.get("habitat_name"))
        
        # Skip non-hedgerow demand (but include hedgerow net gain)
        if not is_hedgerow(dem_hab):
            continue
        
        demand_units = float(demand_row.get("units_required", 0.0))
        if demand_units <= 0:
            continue
        
        # Get demand distinctiveness
        if dem_hab == "Net Gain (Hedgerows)":
            demand_dist = "Low"  # Hedgerow Net Gain trades like Low for hedgerows
            demand_broader = ""
        else:
            cat_match = Catalog[Catalog["habitat_name"] == dem_hab]
            if cat_match.empty:
                continue
            demand_dist = sstr(cat_match.iloc[0]["distinctiveness_name"])
            demand_broader = sstr(cat_match.iloc[0]["broader_type"])
        
        demand_cat_row = pd.Series({
            "habitat_name": dem_hab,
            "distinctiveness_name": demand_dist,
            "broader_type": demand_broader
        })
        
        # Find all eligible supply habitats
        for _, supply_row in stock_full.iterrows():
            supply_hab = sstr(supply_row["habitat_name"])
            
            # Check hedgerow trading rules
            if not enforce_hedgerow_rules(demand_cat_row, supply_row, dist_levels_map):
                continue
            
            bank_key = sstr(supply_row["BANK_KEY"])
            stock_id = sstr(supply_row["stock_id"])
            qty_avail = float(supply_row.get("quantity_available", 0.0))
            
            if qty_avail <= 0:
                continue
            
            tier = tier_for_bank(
                sstr(supply_row.get("lpa_name")), sstr(supply_row.get("nca_name")),
                target_lpa, target_nca,
                lpa_neigh, nca_neigh, lpa_neigh_norm, nca_neigh_norm
            )
            
            # Find price (tier_up already applied to contract size)
            pr_match = pricing_enriched[
                (pricing_enriched["BANK_KEY"] == bank_key) &
                (pricing_enriched["tier"] == tier) &
                (pricing_enriched["habitat_name"] == supply_hab)
            ]
            
            if pr_match.empty:
                # Try to find any price for this bank/tier as fallback
                pr_match = pricing_enriched[
                    (pricing_enriched["BANK_KEY"] == bank_key) &
                    (pricing_enriched["tier"] == tier)
                ]
                if pr_match.empty:
                    continue
                price = float(pr_match.iloc[0]["price"])
            else:
                price = float(pr_match.iloc[0]["price"])
            
            # Apply percentage discount if active
            if promoter_discount_type == "percentage" and promoter_discount_value:
                price = apply_percentage_discount(price, promoter_discount_value)
            
            options.append({
                "demand_idx": demand_idx,
                "demand_habitat": dem_hab,
                "supply_habitat": supply_hab,
                "bank_id": sstr(supply_row.get("bank_id", "")),
                "bank_name": sstr(supply_row.get("bank_name", "")),
                "BANK_KEY": bank_key,
                "stock_id": stock_id,
                "tier": tier,  # Keep original tier for reporting
                "unit_price": price,  # Use discounted price
                "cost_per_unit": price,
                "stock_use": {stock_id: 1.0},
                "type": "normal",          # <-- add this
                "proximity": tier   
            })
            
            stock_caps[stock_id] = qty_avail
            stock_bankkey[stock_id] = bank_key
    
    return options, stock_caps, stock_bankkey


def optimise(demand_df: pd.DataFrame,
             target_lpa: str, target_nca: str,
             lpa_neigh: List[str], nca_neigh: List[str],
             lpa_neigh_norm: List[str], nca_neigh_norm: List[str],
             backend: Dict[str, pd.DataFrame] = None,
             promoter_discount_type: str = None,
             promoter_discount_value: float = None
             ) -> Tuple[pd.DataFrame, float, str]:
    # Load backend if not provided
    if backend is None:
        backend = load_backend()
    
    # Enrich banks with LPA/NCA geography data (in-memory, not persisted)
    backend["Banks"] = enrich_banks_with_geography(backend["Banks"])
    
    # DEBUG: Log enriched bank geography
    sys.stderr.write(f"\n{'='*80}\n")
    sys.stderr.write(f"DEBUG: Bank Geography After Enrichment\n")
    sys.stderr.write(f"{'='*80}\n")
    for _, bank in backend["Banks"].iterrows():
        bank_name = sstr(bank.get('bank_name', 'Unknown'))
        lpa = sstr(bank.get('lpa_name', ''))
        nca = sstr(bank.get('nca_name', ''))
        postcode = sstr(bank.get('postcode', ''))
        sys.stderr.write(f"  {bank_name:30s} | PC: {postcode:10s} | LPA: {lpa:30s} | NCA: {nca}\n")
    sys.stderr.write(f"{'='*80}\n")
    sys.stderr.write(f"Target Location: LPA='{target_lpa}', NCA='{target_nca}'\n")
    sys.stderr.write(f"{'='*80}\n\n")
    
    # Pick contract size from total demand (unchanged)
    chosen_size = select_size_for_demand(demand_df, backend["Pricing"])

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

    stock_bankkey: Dict[str, str] = {}
    stock_bankkey.update(bk_area)
    stock_bankkey.update(bk_hedge)
    stock_bankkey.update(bk_water)

    if not options:
        raise RuntimeError("No feasible options. Check prices/stock/rules or location tiers.")
    
    # DEBUG: Log options summary by bank and tier
    sys.stderr.write(f"\n{'='*80}\n")
    sys.stderr.write(f"DEBUG: Generated Options Summary\n")
    sys.stderr.write(f"{'='*80}\n")
    sys.stderr.write(f"Total options: {len(options)}\n\n")
    
    # Group options by bank and tier
    from collections import defaultdict
    options_by_bank_tier = defaultdict(list)
    for opt in options:
        bank_key = opt.get("BANK_KEY", "Unknown")
        bank_name = opt.get("bank_name", bank_key)
        tier = opt.get("tier", "unknown")
        key = f"{bank_name} ({tier})"
        options_by_bank_tier[key].append(opt)
    
    # Print summary
    for key in sorted(options_by_bank_tier.keys()):
        opts = options_by_bank_tier[key]
        avg_price = sum(o.get("unit_price", 0) for o in opts) / len(opts)
        sys.stderr.write(f"  {key:50s} | {len(opts):3d} options | Avg price: £{avg_price:,.0f}\n")
    
    sys.stderr.write(f"{'='*80}\n\n")

    # ---- Map options to each demand row ----
    idx_by_dem: Dict[int, List[int]] = {}
    dem_need: Dict[int, float] = {}
    for di, drow in demand_df.iterrows():
        idx_by_dem[di] = []
        dem_need[di] = float(drow["units_required"])

    for i, opt in enumerate(options):
        idx_by_dem[opt["demand_idx"]].append(i)

    bad = [di for di, idxs in idx_by_dem.items() if len(idxs) == 0]
    if bad:
        names = [sstr(demand_df.iloc[di]["habitat_name"]) for di in bad]
        raise RuntimeError("No legal options for: " + ", ".join(names))

    bank_keys = sorted({opt["BANK_KEY"] for opt in options})

    try:
        import pulp

        def build_problem(minimise_banks: bool = False, cost_cap: Optional[float] = None):
            prob = pulp.LpProblem("BNG_MinCost_OneOptionPerDemand", pulp.LpMinimize)
            x = [pulp.LpVariable(f"x_{i}", lowBound=0) for i in range(len(options))]
            z = [pulp.LpVariable(f"z_{i}", lowBound=0, upBound=1, cat="Binary") for i in range(len(options))]
            y = {b: pulp.LpVariable(f"y_{norm_name(b)}", lowBound=0, upBound=1, cat="Binary") for b in bank_keys}

            # Calculate tie-break metrics
            bank_capacity_total: Dict[str, float] = {b: 0.0 for b in bank_keys}
            for sid, cap in stock_caps.items():
                bkey = stock_bankkey.get(sid, "")
                if bkey in bank_capacity_total:
                    bank_capacity_total[bkey] += float(cap or 0.0)

            if minimise_banks:
                obj = pulp.lpSum([y[b] for b in bank_keys])
                eps = 1e-9  # Cost tie-break
                eps2 = 1e-12  # Proximity tie-break
                eps3 = 1e-17  # Capacity tie-break (much smaller to ensure proximity always dominates)
                # Secondary tie-break: cost
                obj += eps * pulp.lpSum([options[i]["unit_price"] * x[i] for i in range(len(options))])
                # Tertiary tie-break: prefer closer banks (local > adjacent > far)
                obj += eps2 * pulp.lpSum([TIER_PROXIMITY_RANK.get(options[i].get("tier", "far"), 2) * x[i] for i in range(len(options))])
                # Final tie-break: prefer higher-capacity banks
                obj += -eps3 * pulp.lpSum([bank_capacity_total[b] * y[b] for b in bank_keys])
            else:
                # Primary: minimize cost
                obj = pulp.lpSum([options[i]["unit_price"] * x[i] for i in range(len(options))])
                eps = 1e-9  # Proximity tie-break
                eps2 = 1e-14  # Capacity tie-break (much smaller to ensure proximity always dominates)
                # Secondary tie-break: prefer closer banks (local > adjacent > far)
                obj += eps * pulp.lpSum([TIER_PROXIMITY_RANK.get(options[i].get("tier", "far"), 2) * x[i] for i in range(len(options))])
                # Tertiary tie-break: prefer higher-capacity banks
                obj += -eps2 * pulp.lpSum([bank_capacity_total[b] * y[b] for b in bank_keys])
            prob += obj

            # Hard limit: <= 2 banks
            prob += pulp.lpSum([y[b] for b in bank_keys]) <= 2

            # Link option selection to bank usage
            for i, opt in enumerate(options):
                prob += z[i] <= y[opt["BANK_KEY"]]

            # Exactly one option per demand; meet its units; bind x to z
            for di, idxs in idx_by_dem.items():
                need = dem_need[di]
                prob += pulp.lpSum([z[i] for i in idxs]) == 1
                prob += pulp.lpSum([x[i] for i in idxs]) == need
                for i in idxs:
                    prob += x[i] <= need * z[i]

            # Stock capacity constraints
            use_map: Dict[str, List[Tuple[int, float]]] = {}
            for i, opt in enumerate(options):
                for sid, coef in opt["stock_use"].items():
                    use_map.setdefault(sid, []).append((i, float(coef)))
            for sid, pairs in use_map.items():
                cap = float(stock_caps.get(sid, 0.0))
                prob += pulp.lpSum([coef * x[i] for (i, coef) in pairs]) <= cap

            # Optional cost cap (for stage B)
            if cost_cap is not None:
                prob += pulp.lpSum([options[i]["unit_price"] * x[i] for i in range(len(options))]) <= cost_cap + 1e-9

            return prob, x, z, y

        # Stage A: min cost
        probA, xA, zA, yA = build_problem(minimise_banks=False, cost_cap=None)
        probA.solve(pulp.PULP_CBC_CMD(msg=False))
        statusA = pulp.LpStatus[probA.status]
        if statusA not in ("Optimal", "Feasible"):
            raise RuntimeError("Optimiser infeasible.")
        best_cost = pulp.value(pulp.lpSum([options[i]["unit_price"] * xA[i] for i in range(len(options))])) or 0.0

        def enforce_minimum_delivery(alloc_df):
            """
            Ensure total units_supplied >= 0.01 by padding the cheapest habitat.
            If total < 0.01, add extra units to the cheapest habitat to reach 0.01 minimum.
            """
            if alloc_df.empty:
                return alloc_df, 0.0
            
            total_units = alloc_df["units_supplied"].sum()
            
            if total_units < 0.01:
                # Find the cheapest habitat (lowest unit_price)
                cheapest_idx = alloc_df["unit_price"].idxmin()
                shortage = 0.01 - total_units
                
                # Add shortage to the cheapest habitat
                alloc_df.loc[cheapest_idx, "units_supplied"] += shortage
                alloc_df.loc[cheapest_idx, "cost"] = alloc_df.loc[cheapest_idx, "units_supplied"] * alloc_df.loc[cheapest_idx, "unit_price"]
            
            # Recalculate total cost
            total_cost = float(alloc_df["cost"].sum())
            return alloc_df, total_cost

        def extract(xvars, zvars):
            rows, total_cost = [], 0.0
            for i in range(len(options)):
                qty = xvars[i].value() or 0.0
                sel = zvars[i].value() or 0.0
                if sel >= 0.5 and qty > 0:
                    opt = options[i]
                    row = {
                        "demand_habitat": opt["demand_habitat"],
                        "BANK_KEY": opt["BANK_KEY"],
                        "bank_name": opt.get("bank_name",""),
                        "bank_id": opt.get("bank_id",""),
                        "supply_habitat": opt["supply_habitat"],
                        "allocation_type": opt.get("type", "normal"),
                        "tier": opt["tier"],
                        "units_supplied": qty,
                        "unit_price": opt["unit_price"],
                        "cost": qty * opt["unit_price"],
                        "price_source": opt.get("price_source",""),
                        "price_habitat": opt.get("price_habitat",""),
                    }
                    if opt.get("type") == "paired" and "paired_parts" in opt:
                        row["paired_parts"] = json.dumps(opt["paired_parts"])
                    rows.append(row)
                    total_cost += qty * opt["unit_price"]
            
            # Apply minimum delivery enforcement
            alloc_df = pd.DataFrame(rows)
            alloc_df, total_cost = enforce_minimum_delivery(alloc_df)
            return alloc_df, float(total_cost)

        allocA, costA = extract(xA, zA)

        # Stage B: minimise #banks, but only if cost stays within numerical precision of Stage A
        # Use a very tight threshold (£10 or 0.01%, whichever is smaller) to ensure we prioritize
        # "always select cheapest" over bank minimization
        tight_threshold = min(10.0, best_cost * 0.0001)  # £10 or 0.01% of cost
        probB, xB, zB, yB = build_problem(minimise_banks=True, cost_cap=best_cost + tight_threshold)
        probB.solve(pulp.PULP_CBC_CMD(msg=False))
        statusB = pulp.LpStatus[probB.status]

        if statusB in ("Optimal", "Feasible"):
            allocB, costB = extract(xB, zB)

            def bank_count(df):
                return df["BANK_KEY"].nunique() if not df.empty else 0

            if bank_count(allocB) < bank_count(allocA):
                # Stage C: re-min cost with chosen banks fixed
                chosen_banks = list(allocB["BANK_KEY"].unique())
                probC, xC, zC, yC = build_problem(minimise_banks=False, cost_cap=None)
                for b in bank_keys:
                    if b not in chosen_banks:
                        probC += yC[b] == 0
                probC.solve(pulp.PULP_CBC_CMD(msg=False))
                statusC = pulp.LpStatus[probC.status]
                if statusC in ("Optimal", "Feasible"):
                    allocC, costC = extract(xC, zC)
                    return allocC, costC, chosen_size
                return allocB, costB, chosen_size

        return allocA, costA, chosen_size

    except Exception:
        # ---- Greedy fallback (unchanged) ----
        caps = stock_caps.copy()
        used_banks: List[str] = []

        def bank_ok(b):
            cand = set(used_banks); cand.add(b)
            return len(cand) <= 2

        rows = []
        total_cost = 0.0

        for di, drow in demand_df.iterrows():
            need = float(drow["units_required"])
            # Sort by price first, then by proximity (local > adjacent > far), then by capacity
            cand_idx = sorted(
                [i for i in range(len(options)) if options[i]["demand_idx"] == di],
                key=lambda i: (
                    options[i]["unit_price"],
                    TIER_PROXIMITY_RANK.get(options[i].get("tier", "far"), 2),
                    -sum(stock_caps.get(sid, 0.0) for sid in options[i]["stock_use"].keys())
                )
            )

            best_i = None
            best_cost = float('inf')
            for i in cand_idx:
                opt = options[i]
                bkey = opt["BANK_KEY"]
                if not bank_ok(bkey):
                    continue
                ok = True
                for sid, coef in opt["stock_use"].items():
                    req = coef * need
                    if caps.get(sid, 0.0) + 1e-9 < req:
                        ok = False
                        break
                if not ok:
                    continue
                this_cost = need * opt["unit_price"]
                if this_cost < best_cost - 1e-9:
                    best_cost = this_cost
                    best_i = i

            if best_i is None:
                name = sstr(drow["habitat_name"])
                raise RuntimeError(
                    f"Greedy fallback infeasible for '{name}' (no single option covers need within caps and bank limit)."
                )

            opt = options[best_i]
            bkey = opt["BANK_KEY"]
            for sid, coef in opt["stock_use"].items():
                caps[sid] = caps.get(sid, 0.0) - coef * need
            if bkey not in used_banks:
                used_banks.append(bkey)

            row = {
                "demand_habitat": opt["demand_habitat"],
                "BANK_KEY": opt["BANK_KEY"],
                "bank_name": opt.get("bank_name",""),
                "bank_id": opt.get("bank_id",""),
                "supply_habitat": opt["supply_habitat"],
                "allocation_type": opt.get("type", "normal"),
                "tier": opt["tier"],
                "units_supplied": need,
                "unit_price": opt["unit_price"],
                "cost": need * opt["unit_price"],
                "price_source": opt.get("price_source",""),
                "price_habitat": opt.get("price_habitat",""),
            }
            if opt.get("type") == "paired" and "paired_parts" in opt:
                row["paired_parts"] = json.dumps(opt["paired_parts"])
            rows.append(row)
            total_cost += need * opt["unit_price"]

        # Apply minimum delivery enforcement for greedy fallback
        alloc_df = pd.DataFrame(rows)
        alloc_df, total_cost = enforce_minimum_delivery(alloc_df)
        return alloc_df, float(total_cost), chosen_size


