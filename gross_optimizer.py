"""
gross_optimizer.py - Gross-Based Optimization Module

This module implements a more efficient optimization algorithm that uses GROSS units
from habitat banks instead of NET units. By accounting for baseline habitat losses
separately, we can:

1. Use customer's on-site surplus to offset bank baseline losses (cheaper)
2. Use any cheaper available habitat to cover baseline shortfalls
3. Only use NET units when baseline habitat = offset habitat (to avoid loops)

Algorithm Overview:
------------------
1. Parse metric to get surplus/deficit array
2. Rank deficits by cost (most expensive first = most efficient for us)
3. For each deficit:
   a. Try to offset with customer's on-site surplus first
   b. If not fully covered, allocate GROSS units from cheapest legal bank habitat
   c. Add proportional baseline loss as new deficit entry
   d. If baseline habitat = offset habitat, use NET units instead
4. Repeat until all deficits (including new baseline deficits) are covered
5. Return final allocation with breakdown

Key Concepts:
- GROSS Units: Total habitat units created at the bank
- BASELINE Units: Habitat units lost during creation (original land use)
- NET Units: GROSS - BASELINE = what was previously sold
- Baseline Ratio: BASELINE / GROSS = baseline cost per gross unit
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass, field
import json


@dataclass
class DeficitEntry:
    """Represents a single deficit that needs to be offset"""
    habitat: str
    units: float
    distinctiveness: str
    broader_type: str = ""
    source: str = "metric"  # "metric" or "baseline" 
    parent_allocation_id: Optional[str] = None  # If this is a baseline deficit, link to parent
    
    def __hash__(self):
        return hash((self.habitat, self.units, self.source))


@dataclass 
class SurplusEntry:
    """Represents available surplus (either on-site or from bank)"""
    habitat: str
    units_remaining: float
    distinctiveness: str
    broader_type: str = ""
    source: str = "on_site"  # "on_site" or "bank"


@dataclass
class AllocationRecord:
    """Records a single allocation of units to cover a deficit"""
    allocation_id: str
    deficit_habitat: str
    deficit_units: float
    supply_habitat: str
    supply_units: float
    supply_source: str  # "on_site_surplus", "bank_gross", "bank_net"
    bank_id: Optional[str] = None
    bank_name: Optional[str] = None
    inventory_id: Optional[str] = None
    unit_price: float = 0.0
    cost: float = 0.0
    baseline_habitat: Optional[str] = None
    baseline_units_incurred: float = 0.0  # New deficit created from baseline


@dataclass
class GrossOptimizationResult:
    """Result of gross-based optimization"""
    allocations: List[AllocationRecord]
    remaining_deficits: List[DeficitEntry]
    remaining_surplus: List[SurplusEntry]
    total_cost: float
    iterations: int
    allocation_log: List[str] = field(default_factory=list)


def get_distinctiveness_rank(dist_name: str, dist_levels: Dict[str, float]) -> float:
    """Get numeric rank for distinctiveness level"""
    key = str(dist_name).strip()
    return dist_levels.get(key, dist_levels.get(key.lower(), 0.0))


def can_offset_with_trading_rules(
    demand_habitat: str,
    demand_dist: str,
    demand_broader: str,
    supply_habitat: str,
    supply_dist: str,
    supply_broader: str,
    dist_levels: Dict[str, float]
) -> bool:
    """
    Check if supply can legally offset demand according to trading rules.
    
    Trading rules for area habitats:
    - Very High: Same habitat required (like-for-like)
    - High: Same habitat required (like-for-like)
    - Medium: High/Very High can offset; Medium only if same broad group
    - Low: Same distinctiveness or better
    """
    d_rank = get_distinctiveness_rank(demand_dist, dist_levels)
    s_rank = get_distinctiveness_rank(supply_dist, dist_levels)
    
    demand_dist_lower = str(demand_dist).lower()
    
    # Net Gain can be offset by anything
    if "net gain" in demand_habitat.lower():
        return True
    
    # Same habitat always works
    if demand_habitat == supply_habitat:
        return True
    
    # Very High / High: require same habitat
    if demand_dist_lower in ["very high", "high", "v.high"]:
        return demand_habitat == supply_habitat
    
    # Medium: same broad group OR higher distinctiveness
    if demand_dist_lower == "medium":
        same_group = demand_broader and supply_broader and demand_broader == supply_broader
        higher_dist = s_rank > d_rank
        return same_group or higher_dist
    
    # Low: same or better distinctiveness
    if demand_dist_lower in ["low", "very low", "v.low"]:
        return s_rank >= d_rank
    
    return False


def estimate_offset_cost(
    habitat: str,
    distinctiveness: str,
    pricing_df: pd.DataFrame,
    tier: str = "local",
    contract_size: str = "small"
) -> float:
    """
    Estimate the cost to offset a habitat using pricing data.
    Higher distinctiveness = more expensive = higher priority for efficient offsetting.
    """
    # Filter pricing for matching criteria
    matches = pricing_df[
        (pricing_df["habitat_name"].str.strip() == habitat.strip()) &
        (pricing_df["tier"].str.lower() == tier.lower()) &
        (pricing_df["contract_size"].str.lower() == contract_size.lower())
    ]
    
    if not matches.empty:
        return float(matches.iloc[0].get("price", 0.0))
    
    # Fallback: estimate based on distinctiveness
    dist_prices = {
        "Very High": 50000,
        "High": 35000,
        "Medium": 25000,
        "Low": 15000,
        "Very Low": 10000
    }
    return dist_prices.get(distinctiveness, 20000)


def optimize_gross(
    deficits: List[Dict[str, Any]],
    on_site_surplus: List[Dict[str, Any]],
    gross_inventory: pd.DataFrame,
    pricing_df: pd.DataFrame,
    catalog_df: pd.DataFrame,
    dist_levels: Dict[str, float],
    tier: str = "local",
    contract_size: str = "small",
    max_iterations: int = 100
) -> GrossOptimizationResult:
    """
    Main entry point for gross-based optimization.
    
    Args:
        deficits: List of deficit dicts with keys: habitat, units, distinctiveness, broader_type
        on_site_surplus: List of surplus dicts with keys: habitat, units, distinctiveness, broader_type
        gross_inventory: DataFrame with columns from GrossInventory table
        pricing_df: Pricing data for cost calculations
        catalog_df: Habitat catalog for trading rule lookups
        dist_levels: Distinctiveness level mapping (name -> numeric value)
        tier: Geographic tier for pricing (local/adjacent/far)
        contract_size: Contract size for pricing
        max_iterations: Maximum iterations to prevent infinite loops
        
    Returns:
        GrossOptimizationResult with allocations and remaining deficits
    """
    # Initialize working lists
    working_deficits = [
        DeficitEntry(
            habitat=d["habitat"],
            units=float(d["units"]),
            distinctiveness=d.get("distinctiveness", "Medium"),
            broader_type=d.get("broader_type", ""),
            source="metric"
        )
        for d in deficits if float(d.get("units", 0)) > 0
    ]
    
    working_surplus = [
        SurplusEntry(
            habitat=s["habitat"],
            units_remaining=float(s["units"]),
            distinctiveness=s.get("distinctiveness", "Medium"),
            broader_type=s.get("broader_type", ""),
            source="on_site"
        )
        for s in on_site_surplus if float(s.get("units", 0)) > 0
    ]
    
    # Make a copy of inventory to track remaining units
    inventory = gross_inventory.copy()
    if inventory.empty:
        # Handle empty inventory case
        inventory = pd.DataFrame(columns=[
            "unique_id", "bank_id", "bank_name", "baseline_habitat", "baseline_units",
            "new_habitat", "gross_units", "net_units", "remaining_units", "remaining_gross"
        ])
    elif "remaining_gross" not in inventory.columns:
        inventory["remaining_gross"] = inventory["remaining_units"].copy()
    
    allocations: List[AllocationRecord] = []
    allocation_log: List[str] = []
    allocation_id_counter = 0
    
    iteration = 0
    
    while working_deficits and iteration < max_iterations:
        iteration += 1
        
        # Sort deficits by cost (most expensive first = most efficient for us)
        working_deficits.sort(
            key=lambda d: -estimate_offset_cost(d.habitat, d.distinctiveness, pricing_df, tier, contract_size)
        )
        
        # Take the most expensive deficit
        current_deficit = working_deficits.pop(0)
        
        if current_deficit.units <= 1e-9:
            continue
            
        allocation_log.append(
            f"Iteration {iteration}: Processing deficit {current_deficit.habitat} "
            f"({current_deficit.units:.4f} units, {current_deficit.distinctiveness})"
        )
        
        units_needed = current_deficit.units
        
        # Step 1: Try to offset with on-site surplus first
        for surplus in working_surplus:
            if units_needed <= 1e-9:
                break
                
            if surplus.units_remaining <= 1e-9:
                continue
            
            # Check trading rules
            if not can_offset_with_trading_rules(
                current_deficit.habitat, current_deficit.distinctiveness, current_deficit.broader_type,
                surplus.habitat, surplus.distinctiveness, surplus.broader_type,
                dist_levels
            ):
                continue
            
            # Allocate from surplus
            units_to_use = min(units_needed, surplus.units_remaining)
            surplus.units_remaining -= units_to_use
            units_needed -= units_to_use
            
            allocation_id_counter += 1
            allocations.append(AllocationRecord(
                allocation_id=f"alloc_{allocation_id_counter}",
                deficit_habitat=current_deficit.habitat,
                deficit_units=units_to_use,
                supply_habitat=surplus.habitat,
                supply_units=units_to_use,
                supply_source="on_site_surplus",
                cost=0.0  # On-site surplus is free
            ))
            
            allocation_log.append(
                f"  -> Used {units_to_use:.4f} on-site surplus ({surplus.habitat}) "
                f"to offset {current_deficit.habitat}"
            )
        
        if units_needed <= 1e-9:
            continue
        
        # Step 2: Allocate from bank gross inventory
        # Find eligible inventory rows
        eligible_inventory = []
        
        for _, inv_row in inventory.iterrows():
            if inv_row.get("remaining_gross", 0) <= 1e-9:
                continue
            
            supply_habitat = str(inv_row.get("new_habitat", ""))
            
            # Look up distinctiveness from catalog
            cat_match = catalog_df[catalog_df["habitat_name"].str.strip() == supply_habitat.strip()]
            if cat_match.empty:
                continue
            
            supply_dist = str(cat_match.iloc[0].get("distinctiveness_name", "Medium"))
            supply_broader = str(cat_match.iloc[0].get("broader_type", ""))
            
            # Check trading rules
            if not can_offset_with_trading_rules(
                current_deficit.habitat, current_deficit.distinctiveness, current_deficit.broader_type,
                supply_habitat, supply_dist, supply_broader,
                dist_levels
            ):
                continue
            
            # Get price for this inventory
            price = estimate_offset_cost(supply_habitat, supply_dist, pricing_df, tier, contract_size)
            
            eligible_inventory.append({
                "index": inv_row.name,
                "row": inv_row,
                "supply_habitat": supply_habitat,
                "supply_dist": supply_dist,
                "supply_broader": supply_broader,
                "price": price,
                "baseline_habitat": inv_row.get("baseline_habitat"),
                "baseline_ratio": (
                    float(inv_row.get("baseline_units", 0)) / float(inv_row.get("gross_units", 1))
                    if float(inv_row.get("gross_units", 0)) > 0 else 0
                )
            })
        
        if not eligible_inventory:
            # No eligible inventory - put deficit back (will remain unmet)
            current_deficit.units = units_needed
            working_deficits.append(current_deficit)
            allocation_log.append(f"  -> No eligible inventory found for {current_deficit.habitat}")
            continue
        
        # Sort by price (cheapest first)
        eligible_inventory.sort(key=lambda x: x["price"])
        
        # Allocate from cheapest eligible inventory
        for inv_info in eligible_inventory:
            if units_needed <= 1e-9:
                break
            
            inv_idx = inv_info["index"]
            inv_row = inv_info["row"]
            baseline_habitat = inv_info["baseline_habitat"]
            baseline_ratio = inv_info["baseline_ratio"]
            supply_habitat = inv_info["supply_habitat"]
            
            remaining_gross = inventory.loc[inv_idx, "remaining_gross"]
            
            # Check if baseline habitat = supply habitat (same habitat situation)
            same_habitat = (
                baseline_habitat and 
                str(baseline_habitat).strip().lower() == supply_habitat.strip().lower()
            )
            
            if same_habitat:
                # Use NET units instead to avoid infinite loop
                net_available = float(inv_row.get("net_units", 0)) - float(inv_row.get("allocated_units", 0))
                net_available = max(0, net_available)
                
                if net_available <= 1e-9:
                    continue
                
                units_to_use = min(units_needed, net_available)
                inventory.loc[inv_idx, "remaining_gross"] -= units_to_use
                units_needed -= units_to_use
                
                allocation_id_counter += 1
                cost = units_to_use * inv_info["price"]
                
                allocations.append(AllocationRecord(
                    allocation_id=f"alloc_{allocation_id_counter}",
                    deficit_habitat=current_deficit.habitat,
                    deficit_units=units_to_use,
                    supply_habitat=supply_habitat,
                    supply_units=units_to_use,
                    supply_source="bank_net",  # Using NET because baseline = supply
                    bank_id=str(inv_row.get("bank_id", "")),
                    bank_name=str(inv_row.get("bank_name", "")),
                    inventory_id=str(inv_row.get("unique_id", "")),
                    unit_price=inv_info["price"],
                    cost=cost,
                    baseline_habitat=None,
                    baseline_units_incurred=0  # No additional baseline with NET
                ))
                
                allocation_log.append(
                    f"  -> Used {units_to_use:.4f} NET units ({supply_habitat}) from {inv_row.get('bank_name')} "
                    f"(baseline=supply, avoiding loop) | Cost: £{cost:,.2f}"
                )
            else:
                # Use GROSS units and add baseline as new deficit
                if remaining_gross <= 1e-9:
                    continue
                
                units_to_use = min(units_needed, remaining_gross)
                baseline_units_incurred = units_to_use * baseline_ratio
                
                inventory.loc[inv_idx, "remaining_gross"] -= units_to_use
                units_needed -= units_to_use
                
                allocation_id_counter += 1
                cost = units_to_use * inv_info["price"]
                
                allocations.append(AllocationRecord(
                    allocation_id=f"alloc_{allocation_id_counter}",
                    deficit_habitat=current_deficit.habitat,
                    deficit_units=units_to_use,
                    supply_habitat=supply_habitat,
                    supply_units=units_to_use,
                    supply_source="bank_gross",
                    bank_id=str(inv_row.get("bank_id", "")),
                    bank_name=str(inv_row.get("bank_name", "")),
                    inventory_id=str(inv_row.get("unique_id", "")),
                    unit_price=inv_info["price"],
                    cost=cost,
                    baseline_habitat=baseline_habitat,
                    baseline_units_incurred=baseline_units_incurred
                ))
                
                allocation_log.append(
                    f"  -> Used {units_to_use:.4f} GROSS units ({supply_habitat}) from {inv_row.get('bank_name')} "
                    f"| Cost: £{cost:,.2f} | Baseline incurred: {baseline_units_incurred:.4f} units ({baseline_habitat})"
                )
                
                # Add baseline as new deficit if there's a baseline habitat
                if baseline_habitat and baseline_units_incurred > 1e-9:
                    # Look up baseline habitat distinctiveness
                    baseline_cat = catalog_df[catalog_df["habitat_name"].str.strip() == str(baseline_habitat).strip()]
                    baseline_dist = "Low"  # Default for baseline habitats (typically low-value crops, etc.)
                    baseline_broader = ""
                    if not baseline_cat.empty:
                        baseline_dist = str(baseline_cat.iloc[0].get("distinctiveness_name", "Low"))
                        baseline_broader = str(baseline_cat.iloc[0].get("broader_type", ""))
                    
                    new_baseline_deficit = DeficitEntry(
                        habitat=baseline_habitat,
                        units=baseline_units_incurred,
                        distinctiveness=baseline_dist,
                        broader_type=baseline_broader,
                        source="baseline",
                        parent_allocation_id=f"alloc_{allocation_id_counter}"
                    )
                    working_deficits.append(new_baseline_deficit)
                    
                    allocation_log.append(
                        f"  -> Added new baseline deficit: {baseline_habitat} "
                        f"({baseline_units_incurred:.4f} units, {baseline_dist})"
                    )
        
        # If still have unmet need, put back on list
        if units_needed > 1e-9:
            current_deficit.units = units_needed
            working_deficits.append(current_deficit)
    
    # Clean up remaining surplus
    remaining_surplus = [s for s in working_surplus if s.units_remaining > 1e-9]
    
    # Calculate total cost
    total_cost = sum(a.cost for a in allocations)
    
    return GrossOptimizationResult(
        allocations=allocations,
        remaining_deficits=working_deficits,
        remaining_surplus=remaining_surplus,
        total_cost=total_cost,
        iterations=iteration,
        allocation_log=allocation_log
    )


def format_allocation_summary(result: GrossOptimizationResult) -> pd.DataFrame:
    """Convert allocation results to a summary DataFrame"""
    if not result.allocations:
        return pd.DataFrame()
    
    records = []
    for alloc in result.allocations:
        records.append({
            "Allocation ID": alloc.allocation_id,
            "Deficit Habitat": alloc.deficit_habitat,
            "Deficit Units": alloc.deficit_units,
            "Supply Habitat": alloc.supply_habitat,
            "Supply Units": alloc.supply_units,
            "Supply Source": alloc.supply_source,
            "Bank": alloc.bank_name or "On-site",
            "Unit Price": alloc.unit_price,
            "Cost": alloc.cost,
            "Baseline Habitat": alloc.baseline_habitat or "",
            "Baseline Units Incurred": alloc.baseline_units_incurred
        })
    
    return pd.DataFrame(records)


def format_allocation_log(result: GrossOptimizationResult) -> str:
    """Format allocation log as readable text"""
    lines = [
        "=" * 80,
        "GROSS-BASED OPTIMIZATION LOG",
        "=" * 80,
        ""
    ]
    lines.extend(result.allocation_log)
    lines.append("")
    lines.append("-" * 80)
    lines.append(f"Total iterations: {result.iterations}")
    lines.append(f"Total allocations: {len(result.allocations)}")
    lines.append(f"Total cost: £{result.total_cost:,.2f}")
    
    if result.remaining_deficits:
        lines.append("")
        lines.append("REMAINING UNMET DEFICITS:")
        for d in result.remaining_deficits:
            lines.append(f"  - {d.habitat}: {d.units:.4f} units ({d.source})")
    
    lines.append("=" * 80)
    
    return "\n".join(lines)
