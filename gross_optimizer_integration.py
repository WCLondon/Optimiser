"""
gross_optimizer_integration.py - Integration layer between gross optimizer and app.py

This module provides helper functions to:
1. Convert metric file surplus/deficit data to gross optimizer format
2. Run gross optimization using the new algorithm
3. Convert results back to the format expected by the existing app workflow
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Any, Optional
from dataclasses import dataclass

# Import the gross optimizer
from gross_optimizer import (
    optimize_gross,
    GrossOptimizationResult,
    format_allocation_summary,
    format_allocation_log
)


def prepare_deficits_from_metric(
    metric_requirements: Dict[str, Any],
    catalog_df: pd.DataFrame
) -> List[Dict[str, Any]]:
    """
    Convert metric requirements into deficit format for gross optimizer.
    
    Args:
        metric_requirements: Output from parse_metric_requirements()
        catalog_df: Habitat catalog with distinctiveness and broader_type
        
    Returns:
        List of deficit dicts with habitat, units, distinctiveness, broader_type
    """
    deficits = []
    
    # Process area habitats
    if "area" in metric_requirements and not metric_requirements["area"].empty:
        area_df = metric_requirements["area"]
        for _, row in area_df.iterrows():
            habitat = str(row.get("habitat", "")).strip()
            units = float(row.get("units", 0))
            
            if units <= 0 or not habitat:
                continue
            
            # Look up distinctiveness, broader_type and UmbrellaType from catalog
            cat_match = catalog_df[catalog_df["habitat_name"].str.strip() == habitat]
            if not cat_match.empty:
                distinctiveness = str(cat_match.iloc[0].get("distinctiveness_name", "Medium"))
                broader_type = str(cat_match.iloc[0].get("broader_type", ""))
                # Verify ledger type from catalog's UmbrellaType
                catalog_umbrella = str(cat_match.iloc[0].get("UmbrellaType", "area")).lower().strip()
            else:
                # Handle Net Gain labels
                if "net gain" in habitat.lower():
                    distinctiveness = "Low"
                    broader_type = "Any"
                else:
                    distinctiveness = "Medium"
                    broader_type = ""
                catalog_umbrella = "area"
            
            deficits.append({
                "habitat": habitat,
                "units": units,
                "distinctiveness": distinctiveness,
                "broader_type": broader_type,
                "category": "area",  # From metric section
                "ledger_type": catalog_umbrella if catalog_umbrella in ["area", "hedgerow", "watercourse"] else "area"
            })
    
    # Process hedgerow habitats
    if "hedgerows" in metric_requirements and not metric_requirements["hedgerows"].empty:
        hedge_df = metric_requirements["hedgerows"]
        for _, row in hedge_df.iterrows():
            habitat = str(row.get("habitat", "")).strip()
            units = float(row.get("units", 0))
            
            if units <= 0 or not habitat:
                continue
            
            cat_match = catalog_df[catalog_df["habitat_name"].str.strip() == habitat]
            if not cat_match.empty:
                distinctiveness = str(cat_match.iloc[0].get("distinctiveness_name", "Medium"))
                broader_type = str(cat_match.iloc[0].get("broader_type", ""))
            else:
                if "net gain" in habitat.lower():
                    distinctiveness = "Low"
                    broader_type = "Hedgerow"
                else:
                    distinctiveness = "Medium"
                    broader_type = "Hedgerow"
            
            deficits.append({
                "habitat": habitat,
                "units": units,
                "distinctiveness": distinctiveness,
                "broader_type": broader_type,
                "category": "hedgerow",
                "ledger_type": "hedgerow"  # Force hedgerow ledger
            })
    
    # Process watercourse habitats
    if "watercourses" in metric_requirements and not metric_requirements["watercourses"].empty:
        water_df = metric_requirements["watercourses"]
        for _, row in water_df.iterrows():
            habitat = str(row.get("habitat", "")).strip()
            units = float(row.get("units", 0))
            
            if units <= 0 or not habitat:
                continue
            
            cat_match = catalog_df[catalog_df["habitat_name"].str.strip() == habitat]
            if not cat_match.empty:
                distinctiveness = str(cat_match.iloc[0].get("distinctiveness_name", "Medium"))
                broader_type = str(cat_match.iloc[0].get("broader_type", ""))
            else:
                if "net gain" in habitat.lower():
                    distinctiveness = "Low"
                    broader_type = "Watercourse"
                else:
                    distinctiveness = "Medium"
                    broader_type = "Watercourse"
            
            deficits.append({
                "habitat": habitat,
                "units": units,
                "distinctiveness": distinctiveness,
                "broader_type": broader_type,
                "category": "watercourse",
                "ledger_type": "watercourse"  # Force watercourse ledger
            })
    
    return deficits


def prepare_surplus_from_metric(
    metric_requirements: Dict[str, Any],
    catalog_df: pd.DataFrame
) -> List[Dict[str, Any]]:
    """
    Convert metric surplus data into format for gross optimizer.
    
    Args:
        metric_requirements: Output from parse_metric_requirements()
        catalog_df: Habitat catalog with distinctiveness and broader_type
        
    Returns:
        List of surplus dicts with habitat, units, distinctiveness, broader_type
    """
    surplus_list = []
    
    if "surplus" not in metric_requirements or metric_requirements["surplus"].empty:
        return surplus_list
    
    surplus_df = metric_requirements["surplus"]
    
    for _, row in surplus_df.iterrows():
        habitat = str(row.get("habitat", "")).strip()
        units = float(row.get("units_surplus", 0))
        
        if units <= 0 or not habitat:
            continue
        
        # Get distinctiveness from surplus data if available, else look up
        distinctiveness = str(row.get("distinctiveness", ""))
        broader_type = str(row.get("broad_group", ""))
        
        if not distinctiveness:
            cat_match = catalog_df[catalog_df["habitat_name"].str.strip() == habitat]
            if not cat_match.empty:
                distinctiveness = str(cat_match.iloc[0].get("distinctiveness_name", "Medium"))
                if not broader_type:
                    broader_type = str(cat_match.iloc[0].get("broader_type", ""))
            else:
                distinctiveness = "Medium"
        
        surplus_list.append({
            "habitat": habitat,
            "units": units,
            "distinctiveness": distinctiveness,
            "broader_type": broader_type
        })
    
    return surplus_list


def convert_gross_result_to_alloc_df(
    result: GrossOptimizationResult,
    demand_df: pd.DataFrame
) -> pd.DataFrame:
    """
    Convert gross optimization result to allocation DataFrame format
    compatible with the existing app workflow.
    
    Args:
        result: GrossOptimizationResult from optimize_gross()
        demand_df: Original demand DataFrame
        
    Returns:
        DataFrame in the format expected by the app (matching existing allocations)
    """
    records = []
    
    for alloc in result.allocations:
        # Skip on-site surplus allocations (they're free/internal)
        # Include them but mark appropriately
        is_bank_allocation = alloc.supply_source in ("bank_gross", "bank_net")
        
        records.append({
            "demand_habitat": alloc.deficit_habitat,
            "BANK_KEY": alloc.bank_id or "ON_SITE",
            "bank_name": alloc.bank_name or "On-Site Surplus",
            "bank_id": alloc.bank_id or "",
            "supply_habitat": alloc.supply_habitat,
            "allocation_type": alloc.supply_source,
            "tier": "local" if not is_bank_allocation else "gross",
            "units_supplied": alloc.supply_units,
            "unit_price": alloc.unit_price,
            "cost": alloc.cost,
            "price_source": "gross_optimizer",
            "price_habitat": alloc.supply_habitat,
            "baseline_habitat": alloc.baseline_habitat or "",
            "baseline_units_incurred": alloc.baseline_units_incurred,
            "inventory_id": alloc.inventory_id or ""
        })
    
    if not records:
        return pd.DataFrame(columns=[
            "demand_habitat", "BANK_KEY", "bank_name", "bank_id", "supply_habitat",
            "allocation_type", "tier", "units_supplied", "unit_price", "cost",
            "price_source", "price_habitat", "baseline_habitat", "baseline_units_incurred",
            "inventory_id"
        ])
    
    return pd.DataFrame(records)


def run_gross_optimization(
    demand_df: pd.DataFrame,
    metric_requirements: Dict[str, Any],
    gross_inventory: pd.DataFrame,
    pricing_df: pd.DataFrame,
    catalog_df: pd.DataFrame,
    dist_levels_df: pd.DataFrame,
    tier: str = "local",
    contract_size: str = "small",
    srm_multiplier: float = 1.0,
    max_iterations: int = 100
) -> Tuple[pd.DataFrame, float, str, GrossOptimizationResult]:
    """
    Run gross-based optimization and return results in app-compatible format.
    
    Args:
        demand_df: DataFrame with habitat_name and units_required columns
        metric_requirements: Full output from parse_metric_requirements()
        gross_inventory: GrossInventory table data
        pricing_df: Pricing table data
        catalog_df: HabitatCatalog table data
        dist_levels_df: DistinctivenessLevels table data
        tier: Geographic tier for pricing
        contract_size: Contract size for pricing
        srm_multiplier: Spatial Risk Multiplier (1.0=local, 4/3=adjacent, 2.0=far)
        max_iterations: Maximum iterations for optimizer
        
    Returns:
        Tuple of (allocation_df, total_cost, contract_size, raw_result)
    """
    # Build distinctiveness levels dict
    dist_levels = {}
    if not dist_levels_df.empty:
        for _, row in dist_levels_df.iterrows():
            name = str(row.get("distinctiveness_name", "")).strip()
            level = float(row.get("level_value", 0))
            if name:
                dist_levels[name] = level
    
    # Default distinctiveness levels if table is empty
    if not dist_levels:
        dist_levels = {
            "Very Low": 0.0,
            "Low": 2.0,
            "Medium": 4.0,
            "High": 6.0,
            "Very High": 8.0
        }
    
    # Prepare deficits from demand_df (if metric requirements not available)
    # or use metric requirements directly
    if metric_requirements:
        deficits = prepare_deficits_from_metric(metric_requirements, catalog_df)
        surplus = prepare_surplus_from_metric(metric_requirements, catalog_df)
    else:
        # Convert demand_df to deficits
        deficits = []
        for _, row in demand_df.iterrows():
            habitat = str(row.get("habitat_name", "")).strip()
            units = float(row.get("units_required", 0))
            
            if units <= 0 or not habitat:
                continue
            
            cat_match = catalog_df[catalog_df["habitat_name"].str.strip() == habitat]
            if not cat_match.empty:
                distinctiveness = str(cat_match.iloc[0].get("distinctiveness_name", "Medium"))
                broader_type = str(cat_match.iloc[0].get("broader_type", ""))
            else:
                distinctiveness = "Medium"
                broader_type = ""
            
            deficits.append({
                "habitat": habitat,
                "units": units,
                "distinctiveness": distinctiveness,
                "broader_type": broader_type
            })
        surplus = []
    
    # Run gross optimization
    result = optimize_gross(
        deficits=deficits,
        on_site_surplus=surplus,
        gross_inventory=gross_inventory,
        pricing_df=pricing_df,
        catalog_df=catalog_df,
        dist_levels=dist_levels,
        tier=tier,
        contract_size=contract_size,
        srm_multiplier=srm_multiplier,
        max_iterations=max_iterations
    )
    
    # Convert result to allocation DataFrame
    alloc_df = convert_gross_result_to_alloc_df(result, demand_df)
    
    return (alloc_df, result.total_cost, contract_size, result)


def generate_gross_optimization_summary(result: GrossOptimizationResult) -> str:
    """
    Generate a human-readable summary of the gross optimization.
    
    Args:
        result: GrossOptimizationResult from optimize_gross()
        
    Returns:
        Formatted summary string
    """
    lines = []
    lines.append("=" * 60)
    lines.append("GROSS-BASED OPTIMIZATION SUMMARY")
    lines.append("=" * 60)
    lines.append("")
    
    # Count allocations by type
    on_site_count = sum(1 for a in result.allocations if a.supply_source == "on_site_surplus")
    bank_gross_count = sum(1 for a in result.allocations if a.supply_source == "bank_gross")
    bank_net_count = sum(1 for a in result.allocations if a.supply_source == "bank_net")
    
    on_site_units = sum(a.supply_units for a in result.allocations if a.supply_source == "on_site_surplus")
    bank_gross_units = sum(a.supply_units for a in result.allocations if a.supply_source == "bank_gross")
    bank_net_units = sum(a.supply_units for a in result.allocations if a.supply_source == "bank_net")
    
    lines.append(f"Total iterations: {result.iterations}")
    lines.append(f"Total allocations: {len(result.allocations)}")
    lines.append(f"Total cost: £{result.total_cost:,.2f}")
    lines.append("")
    
    lines.append("Allocation Breakdown:")
    lines.append(f"  - On-site surplus: {on_site_count} allocations ({on_site_units:.4f} units, £0 cost)")
    lines.append(f"  - Bank GROSS: {bank_gross_count} allocations ({bank_gross_units:.4f} units)")
    lines.append(f"  - Bank NET: {bank_net_count} allocations ({bank_net_units:.4f} units)")
    lines.append("")
    
    # Baseline impacts
    total_baseline_incurred = sum(a.baseline_units_incurred for a in result.allocations)
    if total_baseline_incurred > 0:
        lines.append(f"Total baseline units incurred: {total_baseline_incurred:.4f}")
        
        # Group by baseline habitat
        baseline_by_habitat = {}
        for a in result.allocations:
            if a.baseline_habitat and a.baseline_units_incurred > 0:
                key = a.baseline_habitat
                baseline_by_habitat[key] = baseline_by_habitat.get(key, 0) + a.baseline_units_incurred
        
        if baseline_by_habitat:
            lines.append("Baseline by habitat:")
            for hab, units in sorted(baseline_by_habitat.items(), key=lambda x: -x[1]):
                lines.append(f"  - {hab}: {units:.4f} units")
    
    if result.remaining_deficits:
        lines.append("")
        lines.append("⚠️ REMAINING UNMET DEFICITS:")
        for d in result.remaining_deficits:
            lines.append(f"  - {d.habitat}: {d.units:.4f} units ({d.distinctiveness}, {d.source})")
    
    lines.append("=" * 60)
    
    return "\n".join(lines)


def is_gross_optimization_available(gross_inventory: pd.DataFrame) -> bool:
    """
    Check if gross-based optimization can be used.
    
    Args:
        gross_inventory: GrossInventory table data
        
    Returns:
        True if gross inventory has data, False otherwise
    """
    return gross_inventory is not None and not gross_inventory.empty
