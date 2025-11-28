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
    ledger_type: str = "area"  # "area", "hedgerow", or "watercourse"
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
    ledger_type: str = "area"  # "area", "hedgerow", or "watercourse"
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
    dist_levels: Dict[str, float],
    demand_ledger: str = "area",
    supply_ledger: str = "area"
) -> bool:
    """
    Check if supply can legally offset demand according to trading rules.
    
    CRITICAL: No inter-ledger trading allowed!
    - Area habitats can only offset Area habitats
    - Hedgerow habitats can only offset Hedgerow habitats
    - Watercourse habitats can only offset Watercourse habitats
    
    Trading rules within each ledger:
    - Very High: Same habitat required (like-for-like)
    - High: Same habitat required (like-for-like)
    - Medium: High/Very High can offset; Medium only if same broad group
    - Low: Same distinctiveness or better
    """
    # FIRST CHECK: Ledger type must match (no inter-ledger trading!)
    demand_ledger_norm = str(demand_ledger).lower().strip()
    supply_ledger_norm = str(supply_ledger).lower().strip()
    
    if demand_ledger_norm != supply_ledger_norm:
        return False  # Cannot trade between different ledgers
    
    d_rank = get_distinctiveness_rank(demand_dist, dist_levels)
    s_rank = get_distinctiveness_rank(supply_dist, dist_levels)
    
    demand_dist_lower = str(demand_dist).lower()
    
    # Net Gain can be offset by anything (within same ledger)
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
    srm_multiplier: float = 1.0,
    max_iterations: int = 100
) -> GrossOptimizationResult:
    """
    Main entry point for gross-based optimization with deferred baseline bucket.
    
    Algorithm:
    1. Process all metric deficits using on-site surplus first (no SRM - it's customer's own)
    2. For remaining deficits, allocate bank GROSS units with SRM penalty applied to supply
       - SRM is a penalty on what WE provide: to cover 1 unit of deficit, we provide SRM units
       - local (SRM=1): 1 unit covers 1 unit deficit
       - adjacent (SRM=4/3): 4/3 units covers 1 unit deficit  
       - far (SRM=2): 2 units covers 1 unit deficit
    3. Accumulate baseline losses from GROSS allocations into a "baseline bucket"
    4. At the end, resolve baseline bucket with cheapest available (using on-site surplus or NET)
    
    Args:
        deficits: List of deficit dicts with keys: habitat, units, distinctiveness, broader_type
        on_site_surplus: List of surplus dicts with keys: habitat, units, distinctiveness, broader_type
        gross_inventory: DataFrame with columns from GrossInventory table
        pricing_df: Pricing data for cost calculations
        catalog_df: Habitat catalog for trading rule lookups
        dist_levels: Distinctiveness level mapping (name -> numeric value)
        tier: Geographic tier for pricing (local/adjacent/far)
        contract_size: Contract size for pricing
        srm_multiplier: Spatial Risk Multiplier applied to units WE supply
            - 1.0 = local (no penalty)
            - 4/3 = adjacent (we provide 4/3 units per 1 unit of deficit)
            - 2.0 = far (we provide 2 units per 1 unit of deficit)
        max_iterations: Maximum iterations to prevent infinite loops
        
    Returns:
        GrossOptimizationResult with allocations and remaining deficits
    """
    # Initialize working lists for metric deficits (Phase 1)
    metric_deficits = [
        DeficitEntry(
            habitat=d["habitat"],
            units=float(d["units"]),
            distinctiveness=d.get("distinctiveness", "Medium"),
            broader_type=d.get("broader_type", ""),
            ledger_type=d.get("ledger_type", d.get("category", "area")),  # Support both keys
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
            ledger_type=s.get("ledger_type", s.get("category", "area")),  # Support both keys
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
    
    # Baseline bucket - accumulates baseline losses to process at the end
    # Key is (habitat, ledger_type) tuple to track ledger separately
    baseline_bucket: Dict[Tuple[str, str], float] = {}  # (habitat, ledger_type) -> total units
    
    allocation_log.append("=" * 60)
    allocation_log.append("PHASE 1: Processing metric deficits")
    allocation_log.append("=" * 60)
    
    # ========== PHASE 1: Process all metric deficits ==========
    # Sort deficits by cost (most expensive first = most efficient for us)
    metric_deficits.sort(
        key=lambda d: -estimate_offset_cost(d.habitat, d.distinctiveness, pricing_df, tier, contract_size)
    )
    
    for current_deficit in metric_deficits:
        if current_deficit.units <= 1e-9:
            continue
            
        allocation_log.append(
            f"\nProcessing: {current_deficit.habitat} "
            f"({current_deficit.units:.4f} units, {current_deficit.distinctiveness})"
        )
        
        units_needed = current_deficit.units
        
        # Step 1: Try to offset with on-site surplus first (FREE, no SRM)
        for surplus in working_surplus:
            if units_needed <= 1e-9:
                break
                
            if surplus.units_remaining <= 1e-9:
                continue
            
            # Check trading rules (including ledger type match)
            if not can_offset_with_trading_rules(
                current_deficit.habitat, current_deficit.distinctiveness, current_deficit.broader_type,
                surplus.habitat, surplus.distinctiveness, surplus.broader_type,
                dist_levels,
                demand_ledger=current_deficit.ledger_type,
                supply_ledger=surplus.ledger_type
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
                f"  -> Used {units_to_use:.4f} on-site surplus ({surplus.habitat}) - FREE"
            )
        
        if units_needed <= 1e-9:
            continue
        
        # Step 2: Allocate from bank inventory
        # SRM applies as a PENALTY on what WE supply:
        # - To cover 1 unit of deficit, we must provide (1 * SRM) units from our bank
        # - local (SRM=1): provide 1 unit to cover 1 unit deficit
        # - adjacent (SRM=4/3): provide 4/3 units to cover 1 unit deficit
        # - far (SRM=2): provide 2 units to cover 1 unit deficit
        
        # Find eligible inventory rows
        eligible_inventory = _find_eligible_inventory(
            current_deficit, inventory, catalog_df, pricing_df, dist_levels, tier, contract_size
        )
        
        if not eligible_inventory:
            allocation_log.append(f"  -> No eligible inventory found for {current_deficit.habitat}")
            # Will remain as unmet deficit
            continue
        
        allocation_log.append(f"  -> SRM penalty: {srm_multiplier:.4f}x (need {units_needed * srm_multiplier:.4f} supply units to cover {units_needed:.4f} deficit)")
        
        # Allocate from cheapest eligible inventory
        for inv_info in eligible_inventory:
            if units_needed <= 1e-9:
                break
            
            inv_idx = inv_info["index"]
            inv_row = inv_info["row"]
            baseline_habitat = inv_info["baseline_habitat"]
            baseline_ratio = inv_info["baseline_ratio"]
            supply_habitat = inv_info["supply_habitat"]
            supply_ledger = inv_info.get("supply_ledger", "area")  # Get ledger type
            
            remaining_gross = inventory.loc[inv_idx, "remaining_gross"]
            
            # Check if baseline habitat = supply habitat (same habitat situation)
            same_habitat = (
                baseline_habitat and 
                str(baseline_habitat).strip().lower() == supply_habitat.strip().lower()
            )
            
            if same_habitat:
                # Use NET units instead to avoid infinite loop
                net_available = float(inv_row.get("net_units", 0)) - float(inv_row.get("allocated_units", 0))
                net_available = max(0, min(net_available, remaining_gross))
                
                if net_available <= 1e-9:
                    continue
                
                # Calculate how much deficit we can cover with available NET units
                # We have `net_available` supply units, which covers `net_available / srm_multiplier` deficit units
                deficit_coverable = net_available / srm_multiplier
                deficit_to_cover = min(units_needed, deficit_coverable)
                supply_units_to_use = deficit_to_cover * srm_multiplier
                
                inventory.loc[inv_idx, "remaining_gross"] -= supply_units_to_use
                units_needed -= deficit_to_cover
                
                allocation_id_counter += 1
                cost = supply_units_to_use * inv_info["price"]
                
                allocations.append(AllocationRecord(
                    allocation_id=f"alloc_{allocation_id_counter}",
                    deficit_habitat=current_deficit.habitat,
                    deficit_units=deficit_to_cover,
                    supply_habitat=supply_habitat,
                    supply_units=supply_units_to_use,
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
                    f"  -> Used {supply_units_to_use:.4f} NET units ({supply_habitat}) from {inv_row.get('bank_name')} "
                    f"to cover {deficit_to_cover:.4f} deficit (SRM={srm_multiplier:.2f}) | Cost: £{cost:,.2f}"
                )
            else:
                # Use GROSS units and add baseline to bucket
                if remaining_gross <= 1e-9:
                    continue
                
                # Calculate how much deficit we can cover with available GROSS units
                # We have `remaining_gross` supply units, which covers `remaining_gross / srm_multiplier` deficit units
                deficit_coverable = remaining_gross / srm_multiplier
                deficit_to_cover = min(units_needed, deficit_coverable)
                supply_units_to_use = deficit_to_cover * srm_multiplier
                
                # Baseline incurred is based on supply units used (what we actually take from inventory)
                baseline_units_incurred = supply_units_to_use * baseline_ratio
                
                inventory.loc[inv_idx, "remaining_gross"] -= supply_units_to_use
                units_needed -= deficit_to_cover
                
                allocation_id_counter += 1
                cost = supply_units_to_use * inv_info["price"]
                
                allocations.append(AllocationRecord(
                    allocation_id=f"alloc_{allocation_id_counter}",
                    deficit_habitat=current_deficit.habitat,
                    deficit_units=deficit_to_cover,
                    supply_habitat=supply_habitat,
                    supply_units=supply_units_to_use,
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
                    f"  -> Used {supply_units_to_use:.4f} GROSS units ({supply_habitat}) from {inv_row.get('bank_name')} "
                    f"to cover {deficit_to_cover:.4f} deficit (SRM={srm_multiplier:.2f}) | Cost: £{cost:,.2f} | Baseline: {baseline_units_incurred:.4f} ({baseline_habitat})"
                )
                
                # Add baseline to bucket (don't process yet)
                # Key is (habitat, ledger_type) to track ledger separately
                if baseline_habitat and baseline_units_incurred > 1e-9:
                    bucket_key = (baseline_habitat, supply_ledger)
                    baseline_bucket[bucket_key] = baseline_bucket.get(bucket_key, 0) + baseline_units_incurred
    
    # ========== PHASE 2: Process baseline bucket ==========
    # NOTE: SRM does NOT apply to baseline bucket - it only applies to units we supply to customer
    # The baseline bucket is our internal tracking of habitat we've "consumed" from our bank
    allocation_log.append("")
    allocation_log.append("=" * 60)
    allocation_log.append("PHASE 2: Processing baseline bucket")
    allocation_log.append("(Note: SRM already applied in Phase 1 to supply units)")
    allocation_log.append("=" * 60)
    
    if baseline_bucket:
        total_baseline = sum(baseline_bucket.values())
        
        allocation_log.append(f"\nBaseline bucket summary:")
        allocation_log.append(f"  Total baseline to cover: {total_baseline:.4f} units")
        allocation_log.append(f"\nBaseline by habitat (with ledger type):")
        for (hab, ledger), units in sorted(baseline_bucket.items(), key=lambda x: -x[1]):
            allocation_log.append(f"  - {hab} ({ledger}): {units:.4f} units")
        
        # Convert baseline bucket to deficit entries (NO SRM - already accounted for)
        baseline_deficits = []
        for (baseline_habitat, baseline_ledger), baseline_units in baseline_bucket.items():
            
            # Look up baseline habitat distinctiveness
            baseline_cat = catalog_df[catalog_df["habitat_name"].str.strip() == str(baseline_habitat).strip()]
            baseline_dist = "Low"  # Default for baseline habitats
            baseline_broader = ""
            if not baseline_cat.empty:
                baseline_dist = str(baseline_cat.iloc[0].get("distinctiveness_name", "Low"))
                baseline_broader = str(baseline_cat.iloc[0].get("broader_type", ""))
            
            baseline_deficits.append(DeficitEntry(
                habitat=baseline_habitat,
                units=baseline_units,  # No SRM adjustment
                distinctiveness=baseline_dist,
                broader_type=baseline_broader,
                ledger_type=baseline_ledger,  # Preserve ledger type for inter-ledger check
                source="baseline_bucket"
            ))
        
        # Sort baseline deficits by cost (most expensive first)
        baseline_deficits.sort(
            key=lambda d: -estimate_offset_cost(d.habitat, d.distinctiveness, pricing_df, tier, contract_size)
        )
        
        # Process baseline deficits
        for baseline_deficit in baseline_deficits:
            if baseline_deficit.units <= 1e-9:
                continue
            
            allocation_log.append(
                f"\nProcessing baseline: {baseline_deficit.habitat} ({baseline_deficit.ledger_type}) "
                f"({baseline_deficit.units:.4f} units)"
            )
            
            units_needed = baseline_deficit.units
            
            # First try on-site surplus (still available, free)
            for surplus in working_surplus:
                if units_needed <= 1e-9:
                    break
                    
                if surplus.units_remaining <= 1e-9:
                    continue
                
                # Check trading rules (including ledger type match)
                if not can_offset_with_trading_rules(
                    baseline_deficit.habitat, baseline_deficit.distinctiveness, baseline_deficit.broader_type,
                    surplus.habitat, surplus.distinctiveness, surplus.broader_type,
                    dist_levels,
                    demand_ledger=baseline_deficit.ledger_type,
                    supply_ledger=surplus.ledger_type
                ):
                    continue
                
                # Allocate from surplus
                units_to_use = min(units_needed, surplus.units_remaining)
                surplus.units_remaining -= units_to_use
                units_needed -= units_to_use
                
                allocation_id_counter += 1
                allocations.append(AllocationRecord(
                    allocation_id=f"alloc_{allocation_id_counter}",
                    deficit_habitat=baseline_deficit.habitat,
                    deficit_units=units_to_use,
                    supply_habitat=surplus.habitat,
                    supply_units=units_to_use,
                    supply_source="on_site_surplus_baseline",
                    cost=0.0
                ))
                
                allocation_log.append(
                    f"  -> Used {units_to_use:.4f} on-site surplus ({surplus.habitat}) to cover baseline - FREE"
                )
            
            if units_needed <= 1e-9:
                continue
            
            # Then use bank inventory (NET only for baselines to avoid more baselines)
            eligible_inventory = _find_eligible_inventory(
                baseline_deficit, inventory, catalog_df, pricing_df, dist_levels, tier, contract_size
            )
            
            for inv_info in eligible_inventory:
                if units_needed <= 1e-9:
                    break
                
                inv_idx = inv_info["index"]
                inv_row = inv_info["row"]
                supply_habitat = inv_info["supply_habitat"]
                
                # For baseline bucket, always use NET to avoid creating more baselines
                remaining = inventory.loc[inv_idx, "remaining_gross"]
                net_available = float(inv_row.get("net_units", 0)) - float(inv_row.get("allocated_units", 0))
                net_available = max(0, min(net_available, remaining))
                
                if net_available <= 1e-9:
                    continue
                
                units_to_use = min(units_needed, net_available)
                inventory.loc[inv_idx, "remaining_gross"] -= units_to_use
                units_needed -= units_to_use
                
                allocation_id_counter += 1
                cost = units_to_use * inv_info["price"]
                
                allocations.append(AllocationRecord(
                    allocation_id=f"alloc_{allocation_id_counter}",
                    deficit_habitat=baseline_deficit.habitat,
                    deficit_units=units_to_use,
                    supply_habitat=supply_habitat,
                    supply_units=units_to_use,
                    supply_source="bank_net_baseline",
                    bank_id=str(inv_row.get("bank_id", "")),
                    bank_name=str(inv_row.get("bank_name", "")),
                    inventory_id=str(inv_row.get("unique_id", "")),
                    unit_price=inv_info["price"],
                    cost=cost,
                    baseline_habitat=None,
                    baseline_units_incurred=0
                ))
                
                allocation_log.append(
                    f"  -> Used {units_to_use:.4f} NET units ({supply_habitat}) from {inv_row.get('bank_name')} "
                    f"to cover baseline | Cost: £{cost:,.2f}"
                )
            
            # Track remaining unmet baseline
            if units_needed > 1e-9:
                allocation_log.append(f"  -> UNMET: {units_needed:.4f} units of {baseline_deficit.habitat}")
    else:
        allocation_log.append("\nNo baseline bucket to process (all allocations used NET or on-site surplus)")
    
    # ========== Calculate remaining deficits ==========
    remaining_deficits = []
    
    # Check original metric deficits
    for d in deficits:
        habitat = d["habitat"]
        original_units = float(d["units"])
        ledger = d.get("ledger_type", d.get("category", "area"))
        
        # Sum up what was allocated to this deficit
        allocated = sum(
            a.deficit_units for a in allocations 
            if a.deficit_habitat == habitat and a.supply_source in ("on_site_surplus", "bank_gross", "bank_net")
        )
        
        unmet = original_units - allocated
        if unmet > 1e-9:
            remaining_deficits.append(DeficitEntry(
                habitat=habitat,
                units=unmet,
                distinctiveness=d.get("distinctiveness", "Medium"),
                broader_type=d.get("broader_type", ""),
                ledger_type=ledger,
                source="metric_unmet"
            ))
    
    # Check baseline deficits (no SRM - already accounted for in Phase 1)
    for (baseline_habitat, baseline_ledger), baseline_units in baseline_bucket.items():
        
        # Sum up what was allocated to this baseline
        allocated = sum(
            a.deficit_units for a in allocations 
            if a.deficit_habitat == baseline_habitat and a.supply_source in ("on_site_surplus_baseline", "bank_net_baseline")
        )
        
        unmet = baseline_units - allocated  # No SRM adjustment
        if unmet > 1e-9:
            remaining_deficits.append(DeficitEntry(
                habitat=baseline_habitat,
                units=unmet,
                distinctiveness="Low",
                broader_type="",
                ledger_type=baseline_ledger,
                source="baseline_unmet"
            ))
    
    # Clean up remaining surplus
    remaining_surplus = [s for s in working_surplus if s.units_remaining > 1e-9]
    
    # Calculate total cost
    total_cost = sum(a.cost for a in allocations)
    
    allocation_log.append("")
    allocation_log.append("=" * 60)
    allocation_log.append(f"OPTIMIZATION COMPLETE")
    allocation_log.append(f"Total allocations: {len(allocations)}")
    allocation_log.append(f"Total cost: £{total_cost:,.2f}")
    if remaining_deficits:
        allocation_log.append(f"Remaining unmet deficits: {len(remaining_deficits)}")
    allocation_log.append("=" * 60)
    
    return GrossOptimizationResult(
        allocations=allocations,
        remaining_deficits=remaining_deficits,
        remaining_surplus=remaining_surplus,
        total_cost=total_cost,
        iterations=1,  # Single pass with deferred baseline
        allocation_log=allocation_log
    )


def _find_eligible_inventory(
    deficit: DeficitEntry,
    inventory: pd.DataFrame,
    catalog_df: pd.DataFrame,
    pricing_df: pd.DataFrame,
    dist_levels: Dict[str, float],
    tier: str,
    contract_size: str
) -> List[Dict[str, Any]]:
    """
    Find eligible inventory rows for a given deficit, sorted by price (cheapest first).
    Only returns inventory that matches the deficit's ledger type (no inter-ledger trading).
    """
    eligible = []
    
    for _, inv_row in inventory.iterrows():
        if inv_row.get("remaining_gross", 0) <= 1e-9:
            continue
        
        supply_habitat = str(inv_row.get("new_habitat", ""))
        
        # Get ledger type from inventory (default to 'area' for backward compatibility)
        supply_ledger = str(inv_row.get("ledger_type", "area")).lower().strip()
        
        # Look up distinctiveness from catalog
        cat_match = catalog_df[catalog_df["habitat_name"].str.strip() == supply_habitat.strip()]
        if cat_match.empty:
            continue
        
        supply_dist = str(cat_match.iloc[0].get("distinctiveness_name", "Medium"))
        supply_broader = str(cat_match.iloc[0].get("broader_type", ""))
        
        # Check trading rules (including ledger type match)
        if not can_offset_with_trading_rules(
            deficit.habitat, deficit.distinctiveness, deficit.broader_type,
            supply_habitat, supply_dist, supply_broader,
            dist_levels,
            demand_ledger=deficit.ledger_type,
            supply_ledger=supply_ledger
        ):
            continue
        
        # Get price for this inventory
        price = estimate_offset_cost(supply_habitat, supply_dist, pricing_df, tier, contract_size)
        
        eligible.append({
            "index": inv_row.name,
            "row": inv_row,
            "supply_habitat": supply_habitat,
            "supply_dist": supply_dist,
            "supply_broader": supply_broader,
            "supply_ledger": supply_ledger,
            "price": price,
            "baseline_habitat": inv_row.get("baseline_habitat"),
            "baseline_ratio": (
                float(inv_row.get("baseline_units", 0)) / float(inv_row.get("gross_units", 1))
                if float(inv_row.get("gross_units", 0)) > 0 else 0
            )
        })
    
    # Sort by price (cheapest first)
    eligible.sort(key=lambda x: x["price"])
    
    return eligible


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
