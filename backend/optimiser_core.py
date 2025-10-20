"""
Core optimization logic extracted from app.py for use in FastAPI backend.
This module contains the pure business logic without any UI dependencies.
"""

import json
import re
from typing import Dict, Any, List, Tuple, Optional
import numpy as np
import pandas as pd
import requests

# Constants
ADMIN_FEE_GBP = 500.0
SINGLE_BANK_SOFT_PCT = 0.01
LEDGER_AREA = "area"
LEDGER_HEDGE = "hedgerow"
LEDGER_WATER = "watercourse"
TIER_PROXIMITY_RANK = {"local": 0, "adjacent": 1, "far": 2}
NET_GAIN_LABEL = "Net Gain (Area)"
NET_GAIN_HEDGEROW_LABEL = "Net Gain (Hedgerows)"
NET_GAIN_WATERCOURSE_LABEL = "Net Gain (Watercourses)"

# API endpoints
POSTCODES_IO = "https://api.postcodes.io/postcodes/"
NOMINATIM_SEARCH = "https://nominatim.openstreetmap.org/search"
NCA_URL = ("https://services.arcgis.com/JJzESW51TqeY9uat/arcgis/rest/services/"
           "National_Character_Areas_England/FeatureServer/0")
LPA_URL = ("https://services1.arcgis.com/ESMARspQHYMw9BZ9/arcgis/rest/services/"
           "Local_Authority_Districts_December_2024_Boundaries_UK_BFC/FeatureServer/0")

UA = {"User-Agent": "WildCapital-Optimiser/1.0 (+contact@example.com)"}

# Optional solver
try:
    import pulp
    _HAS_PULP = True
except Exception:
    _HAS_PULP = False


def sstr(x) -> str:
    """Safe string conversion"""
    if x is None:
        return ""
    if isinstance(x, float) and (np.isnan(x) or np.isinf(x)):
        return ""
    return str(x).strip()


def norm_name(s: str) -> str:
    """Normalize location names for matching"""
    t = sstr(s).lower()
    t = re.sub(r'\b(city of|royal borough of|metropolitan borough of)\b', '', t)
    t = re.sub(r'\b(council|borough|district|county|unitary authority|unitary|city)\b', '', t)
    t = t.replace("&", "and")
    t = re.sub(r'[^a-z0-9]+', '', t)
    return t


def run_quote(payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    Run the quote optimization with the given payload.
    
    Args:
        payload: Dictionary containing:
            - backend_data: Dict with Banks, Pricing, HabitatCatalog, Stock, etc.
            - demand: List of {habitat_name, units} dicts
            - location: Optional {postcode, address, lpa_name, nca_name}
            - contract_size: Optional specific size
            - options: Optional dict with use_promoter, etc.
    
    Returns:
        Dictionary with:
            - success: bool
            - allocations: List of allocation rows
            - total_cost: float
            - contract_size: str
            - summary: Dict with aggregated data
            - error: Optional error message
    """
    try:
        # Extract backend data
        backend = payload.get("backend_data", {})
        if not backend:
            return {"success": False, "error": "No backend data provided"}
        
        # Validate required sheets
        required_sheets = ["Banks", "Pricing", "HabitatCatalog", "Stock"]
        missing = [s for s in required_sheets if s not in backend]
        if missing:
            return {"success": False, "error": f"Missing required sheets: {missing}"}
        
        # Convert backend dict to DataFrames if needed
        for sheet_name in required_sheets:
            if isinstance(backend[sheet_name], dict):
                backend[sheet_name] = pd.DataFrame(backend[sheet_name])
        
        # Extract demand
        demand_list = payload.get("demand", [])
        if not demand_list:
            return {"success": False, "error": "No demand provided"}
        
        demand_df = pd.DataFrame(demand_list)
        if "habitat_name" not in demand_df.columns or "units" not in demand_df.columns:
            return {"success": False, "error": "Demand must have habitat_name and units"}
        
        demand_df.rename(columns={"units": "units_required"}, inplace=True)
        
        # Extract location info
        location = payload.get("location", {})
        target_lpa = location.get("lpa_name", "")
        target_nca = location.get("nca_name", "")
        lpa_neighbors = location.get("lpa_neighbors", [])
        nca_neighbors = location.get("nca_neighbors", [])
        lpa_neighbors_norm = location.get("lpa_neighbors_norm", [])
        nca_neighbors_norm = location.get("nca_neighbors_norm", [])
        
        # If postcode or address provided but no LPA/NCA, do lookup
        if not target_lpa and not target_nca:
            postcode = location.get("postcode", "")
            address = location.get("address", "")
            if postcode or address:
                try:
                    loc_result = find_location(postcode, address)
                    target_lpa = loc_result.get("lpa_name", "")
                    target_nca = loc_result.get("nca_name", "")
                    lpa_neighbors = loc_result.get("lpa_neighbors", [])
                    nca_neighbors = loc_result.get("nca_neighbors", [])
                    lpa_neighbors_norm = loc_result.get("lpa_neighbors_norm", [])
                    nca_neighbors_norm = loc_result.get("nca_neighbors_norm", [])
                except Exception as e:
                    # Continue with far tiers only
                    pass
        
        # Run optimization
        # NOTE: This would need the actual optimise() function from app.py
        # For now, return a placeholder structure
        
        return {
            "success": True,
            "allocations": [],
            "total_cost": 0.0,
            "contract_size": "small",
            "summary": {},
            "message": "Optimization logic needs to be fully extracted from app.py"
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }


def find_location(postcode: str, address: str) -> Dict[str, Any]:
    """
    Find location details (LPA, NCA, neighbors) from postcode or address.
    
    Returns:
        Dict with lpa_name, nca_name, lpa_neighbors, nca_neighbors, lat, lon
    """
    result = {
        "lpa_name": "",
        "nca_name": "",
        "lpa_neighbors": [],
        "nca_neighbors": [],
        "lpa_neighbors_norm": [],
        "nca_neighbors_norm": [],
        "lat": None,
        "lon": None
    }
    
    lat, lon = None, None
    
    # Try postcode first
    if sstr(postcode):
        try:
            resp = requests.get(POSTCODES_IO + postcode, headers=UA, timeout=10)
            if resp.status_code == 200:
                data = resp.json()
                if data.get("status") == 200 and "result" in data:
                    r = data["result"]
                    lat = r.get("latitude")
                    lon = r.get("longitude")
        except Exception:
            pass
    
    # Try address if postcode failed
    if lat is None and sstr(address):
        try:
            resp = requests.get(
                NOMINATIM_SEARCH,
                params={"q": address, "format": "json", "limit": 1},
                headers=UA,
                timeout=10
            )
            if resp.status_code == 200:
                results = resp.json()
                if results:
                    lat = float(results[0]["lat"])
                    lon = float(results[0]["lon"])
        except Exception:
            pass
    
    if lat is None or lon is None:
        return result
    
    result["lat"] = lat
    result["lon"] = lon
    
    # Look up LPA and NCA
    # This would need the actual ArcGIS API calls from app.py
    # Placeholder for now
    
    return result
