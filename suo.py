"""
Surplus Uplift Offset (SUO) Module

This module implements a post-trading step that reduces mitigation requirements
by using surplus units from high-distinctiveness habitats, accounting for:
- Distinctiveness filtering (Medium+ only)
- Headroom fraction (default 50%)
- Spatial Risk Multipliers (SRM) per site and/or line
- Multi-site allocation (greedy, lowest SRM first)
- Trading group compatibility (optional)

Usage:
    from suo import compute_suo, SUOConfig
    
    config = SUOConfig()
    results = compute_suo(requirements, surplus_supply, srm, config)
"""

from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple, Callable
import pandas as pd
import numpy as np


@dataclass
class SUOConfig:
    """Configuration for SUO computation"""
    headroom_fraction: float = 0.5
    min_distinctiveness: str = "Medium"
    round_to: float = 0.01
    allow_cross_group: bool = True
    group_compatibility_fn: Optional[Callable[[str, str], bool]] = None
    
    # Distinctiveness ordering for filtering
    distinctiveness_order: Dict[str, int] = None
    
    def __post_init__(self):
        if self.distinctiveness_order is None:
            self.distinctiveness_order = {
                "Very Low": 0,
                "Low": 1,
                "Medium": 2,
                "High": 3,
                "Very High": 4,
            }


def compute_suo(
    requirements: pd.DataFrame,
    surplus_supply: pd.DataFrame,
    srm: pd.DataFrame,
    config: Optional[SUOConfig] = None
) -> Tuple[pd.DataFrame, pd.DataFrame, Dict]:
    """
    Compute Surplus Uplift Offset (SUO) - reduce requirements using eligible surplus.
    
    Args:
        requirements: DataFrame with columns:
            - line_id: unique identifier for each requirement line
            - trading_group or broad_group: habitat grouping
            - units_needed: units required after trading
            
        surplus_supply: DataFrame with columns:
            - site_id: source site identifier
            - distinctiveness: habitat distinctiveness level
            - trading_group or broad_group: habitat grouping
            - units_surplus: surplus units available
            
        srm: DataFrame with SRM mapping, supports:
            - per-site: columns [site_id, srm]
            - per-(site,line): columns [site_id, line_id, srm]
            - per-tier: columns [tier, multiplier] (fallback)
            Defaults to 1.0 if no match found
            
        config: SUOConfig instance (uses defaults if None)
        
    Returns:
        Tuple of (requirements_reduced, allocation_ledger, suo_summary)
        
        requirements_reduced: DataFrame with columns:
            - line_id, units_needed_before, units_reduced_by, 
              units_needed_after, reduction_fraction_applied
              
        allocation_ledger: DataFrame with columns:
            - line_id, site_id, allocated_effective_units, 
              allocated_pre_srm_units, srm_used
              
        suo_summary: Dict with keys:
            - eligible_surplus: total eligible surplus
            - usable_units: total after headroom
            - effective_capacity: total after SRM
            - reduction_fraction_final: actual reduction applied
            - site_details: list of per-site summary dicts
    """
    if config is None:
        config = SUOConfig()
    
    # Edge case: no requirements
    if requirements.empty or requirements["units_needed"].sum() <= 0:
        return (
            requirements.assign(
                units_needed_before=requirements["units_needed"],
                units_reduced_by=0.0,
                units_needed_after=requirements["units_needed"],
                reduction_fraction_applied=0.0
            ),
            pd.DataFrame(columns=["line_id", "site_id", "allocated_effective_units", 
                                 "allocated_pre_srm_units", "srm_used"]),
            {
                "eligible_surplus": 0.0,
                "usable_units": 0.0,
                "effective_capacity": 0.0,
                "reduction_fraction_final": 0.0,
                "site_details": []
            }
        )
    
    # Step 1: Filter eligible surplus
    eligible_surplus = _filter_eligible_surplus(surplus_supply, config)
    
    if eligible_surplus.empty:
        # No eligible surplus - return unchanged requirements
        return (
            requirements.assign(
                units_needed_before=requirements["units_needed"],
                units_reduced_by=0.0,
                units_needed_after=requirements["units_needed"],
                reduction_fraction_applied=0.0
            ),
            pd.DataFrame(columns=["line_id", "site_id", "allocated_effective_units",
                                 "allocated_pre_srm_units", "srm_used"]),
            {
                "eligible_surplus": 0.0,
                "usable_units": 0.0,
                "effective_capacity": 0.0,
                "reduction_fraction_final": 0.0,
                "site_details": []
            }
        )
    
    # Step 2: Compute usable units (headroom)
    usable_supply = _compute_headroom(eligible_surplus, config)
    
    # Step 3: Compute effective capacity (SRM-aware)
    effective_supply = _compute_effective_capacity(usable_supply, srm)
    
    # Step 4: Compute initial reduction fraction
    R_total = requirements["units_needed"].sum()
    U_total = effective_supply["effective_capacity"].sum()
    reduction_fraction = min(U_total / R_total, 1.0) if R_total > 0 else 0.0
    
    # Step 5 & 6: Allocate and verify feasibility (with potential back-off)
    reduction_fraction_final, allocation_ledger = _allocate_and_verify(
        requirements, effective_supply, srm, reduction_fraction, config
    )
    
    # Step 7: Apply final reduction to requirements
    requirements_reduced = _apply_uniform_reduction(
        requirements, reduction_fraction_final, config
    )
    
    # Step 8: Generate summary
    suo_summary = {
        "eligible_surplus": eligible_surplus["units_surplus"].sum(),
        "usable_units": usable_supply["usable_units"].sum(),
        "effective_capacity": U_total,
        "reduction_fraction_final": reduction_fraction_final,
        "site_details": [
            {
                "site_id": row["site_id"],
                "usable_units": row["usable_units"],
                "effective_capacity": row["effective_capacity"],
                "srm": row["srm"]
            }
            for _, row in effective_supply.iterrows()
        ]
    }
    
    return requirements_reduced, allocation_ledger, suo_summary


def _filter_eligible_surplus(
    surplus_supply: pd.DataFrame,
    config: SUOConfig
) -> pd.DataFrame:
    """
    Filter surplus to only include habitats with distinctiveness >= MIN_DISTINCTIVENESS.
    
    Low distinctiveness surplus is excluded because it has the same baseline as the 
    original land, therefore it cannot be used to offset requirements.
    Only Medium, High, and Very High distinctiveness habitats represent genuine 
    ecological uplift that can offset baseline mitigation requirements.
    """
    if surplus_supply.empty:
        return surplus_supply.copy()
    
    # Get minimum level value
    min_level = config.distinctiveness_order.get(config.min_distinctiveness, 2)
    
    # Filter by distinctiveness
    def is_eligible(dist_name: str) -> bool:
        level = config.distinctiveness_order.get(str(dist_name), 0)
        return level >= min_level
    
    eligible = surplus_supply[
        surplus_supply["distinctiveness"].apply(is_eligible)
    ].copy()
    
    return eligible


def _compute_headroom(
    eligible_surplus: pd.DataFrame,
    config: SUOConfig
) -> pd.DataFrame:
    """
    Compute usable units = surplus * headroom_fraction.
    """
    result = eligible_surplus.copy()
    result["usable_units"] = result["units_surplus"] * config.headroom_fraction
    return result


def _compute_effective_capacity(
    usable_supply: pd.DataFrame,
    srm: pd.DataFrame
) -> pd.DataFrame:
    """
    Compute effective capacity = usable_units / SRM for each site.
    Uses site-level SRM (conservative: max over lines if per-line SRM varies).
    """
    result = usable_supply.copy()
    
    # Group by site_id to aggregate usable_units
    site_totals = result.groupby("site_id", as_index=False)["usable_units"].sum()
    
    # Map SRM per site
    site_totals["srm"] = site_totals["site_id"].apply(
        lambda site: _get_site_srm(site, srm)
    )
    
    # Compute effective capacity
    site_totals["effective_capacity"] = site_totals["usable_units"] / site_totals["srm"]
    
    return site_totals


def _get_site_srm(site_id: str, srm: pd.DataFrame) -> float:
    """
    Get SRM for a site. If per-line SRM exists, use max (conservative).
    Otherwise use site-level SRM or default to 1.0.
    """
    if srm.empty:
        return 1.0
    
    # Try site_id column
    if "site_id" in srm.columns:
        site_srms = srm[srm["site_id"] == site_id]
        if not site_srms.empty:
            # If there's a line_id column, take max SRM (conservative)
            if "srm" in site_srms.columns:
                return float(site_srms["srm"].max())
            elif "multiplier" in site_srms.columns:
                return float(site_srms["multiplier"].max())
    
    # Fallback to tier-based or default
    return 1.0


def _get_line_site_srm(line_id: str, site_id: str, srm: pd.DataFrame) -> float:
    """
    Get SRM for a specific (line_id, site_id) pair.
    Falls back to site-level SRM, then 1.0.
    """
    if srm.empty:
        return 1.0
    
    # Try exact (site_id, line_id) match
    if "site_id" in srm.columns and "line_id" in srm.columns:
        exact = srm[(srm["site_id"] == site_id) & (srm["line_id"] == line_id)]
        if not exact.empty:
            if "srm" in exact.columns:
                return float(exact["srm"].iloc[0])
            elif "multiplier" in exact.columns:
                return float(exact["multiplier"].iloc[0])
    
    # Fall back to site-level
    return _get_site_srm(site_id, srm)


def _allocate_and_verify(
    requirements: pd.DataFrame,
    effective_supply: pd.DataFrame,
    srm: pd.DataFrame,
    initial_reduction_fraction: float,
    config: SUOConfig
) -> Tuple[float, pd.DataFrame]:
    """
    Allocate offset demand across sites, verify feasibility under SRM.
    If infeasible, recompute reduction_fraction downward (one back-off pass).
    
    Returns:
        (final_reduction_fraction, allocation_ledger)
    """
    # Sort sites by SRM (ascending) for greedy allocation
    sites_sorted = effective_supply.sort_values("srm").copy()
    
    # Compute offset demand for each line
    requirements_copy = requirements.copy()
    requirements_copy["offset_demand"] = (
        requirements_copy["units_needed"] * initial_reduction_fraction
    )
    
    # Try allocation
    allocation_ledger = []
    site_remaining = {row["site_id"]: row["usable_units"] 
                     for _, row in sites_sorted.iterrows()}
    
    for _, req_row in requirements_copy.iterrows():
        line_id = req_row["line_id"]
        offset_needed = req_row["offset_demand"]
        
        if offset_needed <= 1e-9:
            continue
        
        # Allocate from sites (greedy, lowest SRM first)
        remaining = offset_needed
        for _, site_row in sites_sorted.iterrows():
            site_id = site_row["site_id"]
            if remaining <= 1e-9:
                break
            
            # Get SRM for this (site, line) pair
            srm_val = _get_line_site_srm(line_id, site_id, srm)
            
            # Check group compatibility if needed
            if not config.allow_cross_group and config.group_compatibility_fn:
                # Get groups (if columns exist)
                site_group = _get_group(site_row, effective_supply)
                line_group = _get_group(req_row, requirements)
                if not config.group_compatibility_fn(site_group, line_group):
                    continue
            
            # Compute how much we can allocate from this site
            site_avail = site_remaining.get(site_id, 0.0)
            
            # Effective allocation is limited by remaining need
            allocated_effective = min(remaining, site_avail / srm_val)
            
            # Pre-SRM units consumed from site
            allocated_pre_srm = allocated_effective * srm_val
            
            if allocated_effective > 1e-9:
                allocation_ledger.append({
                    "line_id": line_id,
                    "site_id": site_id,
                    "allocated_effective_units": allocated_effective,
                    "allocated_pre_srm_units": allocated_pre_srm,
                    "srm_used": srm_val
                })
                
                site_remaining[site_id] -= allocated_pre_srm
                remaining -= allocated_effective
    
    # Check if we fully satisfied the reduction
    allocation_df = pd.DataFrame(allocation_ledger)
    
    if allocation_df.empty:
        # No allocation possible
        return 0.0, allocation_df
    
    # Sum allocated effective units per line
    allocated_by_line = allocation_df.groupby("line_id")["allocated_effective_units"].sum()
    
    # Check shortfall
    total_offset_allocated = allocated_by_line.sum()
    total_offset_intended = requirements_copy["offset_demand"].sum()
    
    if total_offset_allocated < total_offset_intended - 1e-6:
        # Back-off: recompute reduction_fraction
        R_total = requirements["units_needed"].sum()
        actual_reduction_fraction = total_offset_allocated / R_total if R_total > 0 else 0.0
        
        # Re-run allocation with corrected fraction
        return _allocate_and_verify(
            requirements, effective_supply, srm, actual_reduction_fraction, config
        )
    
    return initial_reduction_fraction, allocation_df


def _get_group(row: pd.Series, df: pd.DataFrame) -> str:
    """Extract trading_group or broad_group from row."""
    if "trading_group" in row and pd.notna(row["trading_group"]):
        return str(row["trading_group"])
    if "broad_group" in row and pd.notna(row["broad_group"]):
        return str(row["broad_group"])
    # Check dataframe columns if not in row
    if "trading_group" in df.columns:
        return ""
    if "broad_group" in df.columns:
        return ""
    return ""


def _apply_uniform_reduction(
    requirements: pd.DataFrame,
    reduction_fraction: float,
    config: SUOConfig
) -> pd.DataFrame:
    """
    Apply uniform reduction_fraction to all requirement lines.
    """
    result = requirements.copy()
    result["units_needed_before"] = result["units_needed"]
    result["units_reduced_by"] = result["units_needed"] * reduction_fraction
    result["units_needed_after"] = result["units_needed"] * (1 - reduction_fraction)
    
    # Round and clamp
    result["units_needed_after"] = result["units_needed_after"].apply(
        lambda x: max(0.0, round(x / config.round_to) * config.round_to)
    )
    result["units_reduced_by"] = result["units_needed_before"] - result["units_needed_after"]
    result["reduction_fraction_applied"] = reduction_fraction
    
    return result
