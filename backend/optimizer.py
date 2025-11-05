"""
Optimizer integration for promoter form submissions
Integrates with the existing BNG optimizer to process metric files
"""

import sys
import os
from typing import Dict, Any, Optional
import pandas as pd

# Add parent directory to path to import main app modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import metric_reader
import repo


async def run_optimizer_for_metric(
    metric_file_path: str,
    site_address: Optional[str] = None,
    site_postcode: Optional[str] = None
) -> Dict[str, Any]:
    """
    Run the BNG optimizer for a given metric file
    
    This function:
    1. Reads the metric file
    2. Resolves location (LPA/NCA) from address or postcode
    3. Runs the optimizer
    4. Returns allocation results and totals
    
    Args:
        metric_file_path: Path to the uploaded metric file
        site_address: Optional site address
        site_postcode: Optional site postcode
    
    Returns:
        Dictionary containing:
            - total_cost: Total quote cost in GBP
            - allocation_results: Full allocation details (JSON)
            - target_lpa: Local Planning Authority
            - target_nca: National Character Area
    """
    
    # Read the metric file
    try:
        demand_data = metric_reader.read_bng_metric(metric_file_path)
    except Exception as e:
        raise ValueError(f"Failed to read metric file: {str(e)}")
    
    # Extract demand habitats
    demand_habitats = demand_data.get('area_habitats', [])
    hedgerow_habitats = demand_data.get('hedgerow_habitats', [])
    watercourse_habitats = demand_data.get('watercourse_habitats', [])
    
    if not demand_habitats and not hedgerow_habitats and not watercourse_habitats:
        raise ValueError("No habitat demand found in metric file")
    
    # Convert to DataFrame format expected by optimizer
    demand_df = pd.DataFrame(demand_habitats)
    
    # Resolve location (LPA/NCA) from address or postcode
    target_lpa, target_nca = await resolve_location(site_address, site_postcode)
    
    # Load reference data
    try:
        ref_tables = repo.load_all_tables()
        banks = ref_tables.get('banks', [])
        pricing = ref_tables.get('pricing', [])
        stock = ref_tables.get('stock', [])
        habitat_catalog = ref_tables.get('habitat_catalog', [])
        srm = ref_tables.get('srm', [])
    except Exception as e:
        raise ValueError(f"Failed to load reference data: {str(e)}")
    
    # For now, return a simplified result
    # In production, this would call the full optimizer logic
    # from the main app.py
    
    # Calculate basic total from demand
    total_units = sum(h.get('units_required', 0) for h in demand_habitats)
    
    # Simplified pricing (would use actual optimizer in production)
    # Assume average price of £10,000 per unit for demonstration
    average_price_per_unit = 10000.0
    total_cost = total_units * average_price_per_unit
    
    # Build allocation results
    allocation_results = {
        'demand': demand_habitats,
        'hedgerows': hedgerow_habitats,
        'watercourses': watercourse_habitats,
        'total_units': total_units,
        'allocations': []  # Would contain detailed bank allocations
    }
    
    return {
        'total_cost': total_cost,
        'allocation_results': allocation_results,
        'target_lpa': target_lpa,
        'target_nca': target_nca
    }


async def resolve_location(
    address: Optional[str] = None,
    postcode: Optional[str] = None
) -> tuple[Optional[str], Optional[str]]:
    """
    Resolve location to LPA and NCA
    
    Args:
        address: Site address
        postcode: Site postcode
    
    Returns:
        Tuple of (LPA name, NCA name)
    """
    import requests
    
    lpa_name = None
    nca_name = None
    lat = None
    lon = None
    
    # Try to geocode using postcode first (more reliable)
    if postcode:
        try:
            response = requests.get(
                f"https://api.postcodes.io/postcodes/{postcode.replace(' ', '')}",
                timeout=10
            )
            if response.status_code == 200:
                data = response.json()
                if data.get('result'):
                    lat = data['result']['latitude']
                    lon = data['result']['longitude']
                    # Note: postcodes.io provides admin_district which is similar to LPA
                    lpa_name = data['result'].get('admin_district')
        except Exception as e:
            print(f"Postcode lookup failed: {str(e)}")
    
    # Fall back to address geocoding if postcode didn't work
    if not lat and not lon and address:
        try:
            response = requests.get(
                "https://nominatim.openstreetmap.org/search",
                params={
                    'q': address,
                    'format': 'json',
                    'limit': 1
                },
                headers={'User-Agent': 'WildCapital-Optimiser/1.0'},
                timeout=10
            )
            if response.status_code == 200:
                results = response.json()
                if results:
                    lat = float(results[0]['lat'])
                    lon = float(results[0]['lon'])
        except Exception as e:
            print(f"Address geocoding failed: {str(e)}")
    
    # Look up NCA using coordinates (if available)
    if lat and lon:
        try:
            # Query NCA service
            nca_url = (
                "https://services.arcgis.com/JJzESW51TqeY9uat/arcgis/rest/services/"
                "National_Character_Areas_England/FeatureServer/0"
            )
            response = requests.get(
                f"{nca_url}/query",
                params={
                    'geometry': f"{lon},{lat}",
                    'geometryType': 'esriGeometryPoint',
                    'inSR': 4326,
                    'spatialRel': 'esriSpatialRelIntersects',
                    'returnGeometry': 'false',
                    'outFields': 'NAME',
                    'f': 'json'
                },
                timeout=10
            )
            if response.status_code == 200:
                data = response.json()
                features = data.get('features', [])
                if features:
                    nca_name = features[0]['attributes'].get('NAME')
        except Exception as e:
            print(f"NCA lookup failed: {str(e)}")
    
    return lpa_name, nca_name
