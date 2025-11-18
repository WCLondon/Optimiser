"""
sales_quotes_csv.py - Generate CSV rows for Sales & Quotes Excel workbook.

This module converts optimiser allocation results into CSV data rows
that align with the Sales & Quotes Excel workbook column structure (A-BB).
"""

from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
import pandas as pd

# Import constants from optimizer_core
from optimizer_core import ADMIN_FEE_GBP, ADMIN_FEE_FRACTIONAL_GBP

# Import database functions
from repo import fetch_banks


# Cache for bank names to avoid repeated database queries
_bank_name_cache = None


def get_bank_id_from_database(bank_key: str) -> Optional[str]:
    """
    Get bank_id from the Banks table in the database by looking up BANK_KEY.
    
    Args:
        bank_key: Bank key/name from BANK_KEY column (e.g., "Nunthorpe", "Cobham")
    
    Returns:
        bank_id from database (e.g., "WC1P2B"), or None if not found
    """
    global _bank_name_cache
    
    # Load banks data from database (cached)
    # Cache maps BANK_KEY -> bank_id
    if _bank_name_cache is None:
        try:
            banks_df = fetch_banks()
            if banks_df is not None and not banks_df.empty:
                # Create mapping: BANK_KEY -> bank_id
                _bank_name_cache = {}
                for _, row in banks_df.iterrows():
                    bank_id = row.get('bank_id', '')
                    bank_key_val = row.get('BANK_KEY', '')
                    if bank_key_val and bank_id:
                        _bank_name_cache[str(bank_key_val).strip()] = str(bank_id).strip()
            else:
                _bank_name_cache = {}
        except Exception:
            # Database not available (e.g., in tests) - use empty cache
            _bank_name_cache = {}
    
    # Look up bank_id by BANK_KEY
    return _bank_name_cache.get(bank_key.strip())


# Bank reference to bank name mapping - Updated list from user
# Format: first 5 chars of bank_id + " - " + bank_name
VALID_BANK_COMBINATIONS = [
    ("WC1P6", "Central Bedfordshire"),
    ("WC1P4", "Barnsley"),
    ("WC1P6", "Denchworth"),
    ("WC1P2", "Horden"),
    ("WC1P2", "Stokesley"),
    ("WC1P5", "Bedford"),
    ("WC1P8", "Marbury"),
    ("WC1P2", "Nunthorpe"),
    ("WC1P7", "Fareham"),
    ("WC1P3", "Cobham"),
]


def get_standardized_bank_name(bank_key: str, bank_name: str) -> Tuple[str, str, str]:
    """
    Get standardized bank name format from Banks table in database.
    Uses format: first 5 chars of bank_id + " - " + BANK_KEY
    
    Args:
        bank_key: Bank reference from BANK_KEY column (e.g., "Nunthorpe", "Cobham")
        bank_name: Bank name (same as bank_key in most cases)
    
    Returns:
        Tuple of (standardized_bank_name, notes_for_column_S, source_display)
        - standardized_bank_name: Bank name from database or 'Other'
        - notes_for_column_S: Empty string or the actual bank name if using 'Other'
        - source_display: The full "ref - name" string for column AB
    """
    bank_key = bank_key.strip()
    bank_name = bank_name.strip()
    
    # Get bank_id from database by looking up the BANK_KEY
    bank_id = get_bank_id_from_database(bank_key)
    
    if bank_id:
        # Found in database - use first 5 chars of bank_id
        bank_id_short = bank_id[:5] if len(bank_id) >= 5 else bank_id
        return bank_key, "", f"{bank_id_short} - {bank_key}"
    else:
        # Not found in database - use 'Other' and put actual name in notes
        # Try to extract first 5 chars from bank_key
        bank_key_short = bank_key[:5] if len(bank_key) >= 5 else bank_key
        return "Other", bank_key, f"{bank_key_short} - Other"


def split_paired_habitat(habitat_type: str, units_supplied: float, effective_units: float, 
                         avg_effective_unit_price: float) -> List[Dict[str, Any]]:
    """
    DEPRECATED: Split a paired habitat (e.g., "Habitat A + Habitat B") into separate habitats.
    
    NOTE: This function is no longer used in the main CSV generation flow.
    The optimizer's split_paired_rows() function already splits paired allocations
    with accurate units, prices, and totals for each component based on stock_use ratios.
    
    This function does a simple 50/50 split which is NOT accurate for legal contracts.
    Use the optimizer's split data instead.
    
    Args:
        habitat_type: Habitat type string (may contain " + ")
        units_supplied: Total units supplied
        effective_units: Total effective units
        avg_effective_unit_price: Average effective unit price
    
    Returns:
        List of habitat dictionaries (1 if not paired, 2+ if paired with "+")
    """
    # Check if habitat contains " + " indicating it's paired
    if " + " in habitat_type:
        # Split by " + "
        parts = [p.strip() for p in habitat_type.split(" + ")]
        
        # WARNING: This splits evenly which may NOT match actual allocation!
        # The optimizer uses stock_use ratios and individual unit prices.
        num_parts = len(parts)
        units_per_part = units_supplied / num_parts
        effective_units_per_part = effective_units / num_parts
        
        # Create separate habitat entries
        result = []
        for part_name in parts:
            result.append({
                "type": part_name,
                "units_supplied": units_per_part,
                "effective_units": effective_units_per_part,
                "avg_effective_unit_price": avg_effective_unit_price
            })
        return result
    else:
        # Not paired, return as-is
        return [{
            "type": habitat_type,
            "units_supplied": units_supplied,
            "effective_units": effective_units,
            "avg_effective_unit_price": avg_effective_unit_price
        }]


def get_admin_fee_for_contract_size(contract_size: str) -> float:
    """
    Get the admin fee based on contract size.
    Fractional quotes get £300, all others get £500.
    """
    if str(contract_size).lower().strip() == "fractional":
        return ADMIN_FEE_FRACTIONAL_GBP
    return ADMIN_FEE_GBP


def generate_sales_quotes_csv(
    quote_number: str,
    client_name: str,
    development_address: str,
    base_ref: str,
    introducer: Optional[str],
    today_date: datetime,
    local_planning_authority: str,
    national_character_area: str,
    allocations: List[Dict[str, Any]],
    contract_size: str = "small"
) -> str:
    """
    Generate CSV data rows (no headers) for the Sales & Quotes Excel workbook.
    
    One allocation = one row. For multi-bank (paired) allocations, generates
    one row per allocation and suffixes the Ref with letters (a, b, ...).
    
    Args:
        quote_number: Quote number (e.g., "1923")
        client_name: Client name (e.g., "David Evans")
        development_address: Single string for development address
        base_ref: Base reference (e.g., "BNG01640")
        introducer: Introducer name (or None for "Direct")
        today_date: Date for quote (will be formatted as DD/MM/YYYY)
        local_planning_authority: LPA name
        national_character_area: NCA name
        allocations: List of allocation dictionaries. Each allocation must have:
            - bank_ref: Bank reference (e.g., "WC1P2")
            - bank_name: Bank name (e.g., "Nunthorpe")
            - is_paired: Boolean - true if quote split across 2+ banks
            - spatial_relation: "adjacent" or "far"
            - spatial_multiplier_numeric: Spatial multiplier (e.g., 1.00)
            - allocation_total_credits: Total credits for this bank
            - contract_value_gbp: Contract value for this allocation
            - habitats: List (max 8) of habitat dicts with:
                - type: Habitat type name
                - units_supplied: Numeric units supplied
                - effective_units: Numeric effective units
                - avg_effective_unit_price: Average effective unit price
        contract_size: Contract size for admin fee calculation
    
    Returns:
        CSV string with one line per allocation (joined with \\n)
    """
    csv_rows = []
    
    # Determine admin fee
    admin_fee = get_admin_fee_for_contract_size(contract_size)
    
    # Format date as DD/MM/YYYY
    quote_date_str = today_date.strftime("%d/%m/%Y")
    
    # Determine if we have multiple allocations for ref suffixing
    num_allocations = len(allocations)
    
    for alloc_idx, allocation in enumerate(allocations):
        # Extract allocation fields
        bank_ref = str(allocation.get("bank_ref", "")).strip()
        bank_name = str(allocation.get("bank_name", "")).strip()
        is_paired = bool(allocation.get("is_paired", False))
        spatial_relation = str(allocation.get("spatial_relation", "")).strip().lower()
        spatial_multiplier_numeric = allocation.get("spatial_multiplier_numeric", 1.0)
        allocation_total_credits = allocation.get("allocation_total_credits", 0.0)
        contract_value_gbp = allocation.get("contract_value_gbp", 0.0)
        habitats = allocation.get("habitats", [])
        
        # NOTE: Habitats should already be split if they were paired allocations.
        # The optimizer's split_paired_rows() function handles this.
        # Each habitat in the list should represent one actual allocation with
        # accurate units, prices, and totals for legal contracts.
        
        # Limit to 8 habitats (as per spec)
        habitats = habitats[:8]
        
        # Get standardized bank name and check if we need to use 'Other'
        standardized_bank_name, bank_fallback_note, source_display = get_standardized_bank_name(bank_ref, bank_name)
        
        # Calculate totals for this row
        total_units = sum(h.get("effective_units" if is_paired else "units_supplied", 0.0) for h in habitats)
        total_credit_price = sum(
            h.get("effective_units" if is_paired else "units_supplied", 0.0) * h.get("avg_effective_unit_price", 0.0)
            for h in habitats
        )
        
        # Create CSV row with all columns A-CX
        # Total: 102 columns (A=0 to CX=101) - UPDATED after moving habitats left
        row = [""] * 102  # 102 columns from A to CX
        
        # Column A (index 0): blank
        
        # Column B (index 1): Client
        row[1] = client_name.strip()
        
        # Column C (index 2): Address
        row[2] = development_address.strip()
        
        # Column D (index 3): Ref
        # If multiple allocations, suffix with letters (a, b, c, ...)
        if num_allocations > 1:
            suffix = chr(ord('a') + alloc_idx)  # a, b, c, ...
            row[3] = f"{base_ref}{suffix}"
        else:
            row[3] = base_ref
        
        # Columns E-Q (indices 4-16): blank
        
        # Column R (index 17): blank
        
        # Column S (index 18): Notes / SRM manual
        # Priority 1: Bank fallback note (if using 'Other')
        # Priority 2: SRM logic based on pairing and spatial_relation
        if bank_fallback_note:
            # If bank is not in valid combinations, put the actual bank name here
            row[18] = bank_fallback_note
        elif is_paired:
            if spatial_relation == "far":
                row[18] = "SRM manual (0.5)"
            elif spatial_relation == "adjacent":
                row[18] = "SRM manual (0.75)"
            # else: blank
        # else: blank for non-paired
        
        # Columns T-AA (indices 19-26): blank
        
        # Column AB (index 27): Habitat Bank / Source of Mitigation
        # Use the standardized display format (first 5 chars + " - " + name)
        row[27] = source_display
        
        # Column AC (index 28): Spatial Multiplier
        if is_paired:
            # For paired allocations, use numeric 1
            row[28] = "1"
        else:
            # For non-paired, use formula
            if spatial_relation == "adjacent":
                row[28] = "=4/3"
            elif spatial_relation == "far":
                row[28] = "=2/1"
            else:
                # Default to 1 if relation not specified
                row[28] = "1"
        
        # Column AD (index 29): Total Units (CORRECT POSITION per user)
        row[29] = str(total_units)
        
        # Column AE (index 30): Contract Value (CORRECT POSITION per user)
        if alloc_idx == 0:
            contract_value = total_credit_price + admin_fee
        else:
            contract_value = total_credit_price
        row[30] = str(contract_value)
        
        # Column AF (index 31): blank
        
        # Column AG (index 32): Local Planning Authority (MOVED LEFT from 33)
        row[32] = local_planning_authority.strip()
        
        # Column AH (index 33): National Character Area (MOVED LEFT from 34)
        row[33] = national_character_area.strip()
        
        # Column AI (index 34): blank (MOVED LEFT from 35)
        
        # Column AJ (index 35): Introducer (MOVED LEFT from 36)
        row[35] = introducer.strip() if introducer else "Direct"
        
        # Column AK (index 36): Quote Date (MOVED LEFT from 37)
        row[36] = quote_date_str
        
        # Column AL (index 37): Quote Period (MOVED LEFT from 38, always "30")
        row[37] = "30"
        
        # Column AM (index 38): Quote Expiry (Formula: Quote Date + Quote Period)
        # Excel formula: =AK{row}+AL{row}
        # We need to calculate the actual row number (data rows start at row 1 in Excel if no headers)
        # Since we're generating multiple rows, we'll use a row-independent formula
        # Actually, we need the actual Excel row number. For now, we'll leave a placeholder formula
        # that assumes the CSV will be pasted starting at row 2 (row 1 would be headers)
        row_number = alloc_idx + 2  # Assuming paste starts at row 2
        row[38] = f"=AK{row_number}+AL{row_number}"
        
        # Columns AN-AP (indices 39-41): blank
        
        # Column AQ (index 42): Admin Fee (MOVED LEFT from 43, only on first row if multi-row)
        if alloc_idx == 0:
            row[42] = str(admin_fee)
        # else: blank for subsequent rows
        
        # Column AR (index 43): blank (Admin Fee was here, now moved to 42)
        
        # Column AS (index 44): Total Credit Price (CORRECT POSITION per user)
        row[44] = str(total_credit_price)
        row[44] = str(total_credit_price)
        
        # Column AT (index 45): Total Units (CORRECT POSITION per user)
        row[45] = str(total_units)
        
        # Note: Column AU (index 46) is now the start of habitats, NOT blank
        
        # Habitats 1-8 start at column AU (index 46) - MOVED LEFT from AV (47)
        # Each habitat has 7 columns: Type, # credits, blank, blank, Quoted Price, blank, Total Cost
        # Habitat 1: AU-BA (indices 46-52)
        # Habitat 2: BB-BH (indices 53-59)
        # Habitat 3: BI-BO (indices 60-66)
        # Habitat 4: BP-BV (indices 67-73)
        # Habitat 5: BW-CC (indices 74-80)
        # Habitat 6: CD-CJ (indices 81-87)
        # Habitat 7: CK-CQ (indices 88-94)
        # Habitat 8: CR-CX (indices 95-101)
        
        # Process all habitats (up to 8) - each habitat represents exact allocation data
        for hab_idx in range(min(len(habitats), 8)):
            habitat = habitats[hab_idx]
            
            # Calculate starting column index for this habitat
            # Habitat 1 starts at 46 (MOVED LEFT from 47), each habitat takes 7 columns
            base_idx = 46 + (hab_idx * 7)
            
            # Column 0: Type
            row[base_idx] = str(habitat.get("type", "")).strip()
            
            # Column 1: # credits
            # Use effective_units if paired, otherwise units_supplied
            if is_paired:
                units_value = habitat.get("effective_units", 0.0)
            else:
                units_value = habitat.get("units_supplied", 0.0)
            row[base_idx + 1] = str(units_value)
            
            # Column 2: blank (was ST)
            
            # Column 3: blank (was Standard Price)
            
            # Column 4: Quoted Price (avg_effective_unit_price)
            quoted_price = habitat.get("avg_effective_unit_price", 0.0)
            row[base_idx + 4] = str(quoted_price)
            
            # Column 5: blank (was Minimum)
            
            # Column 6: Total Cost (2 cells to the right of Quoted Price = units * quoted_price)
            habitat_total_cost = units_value * quoted_price
            row[base_idx + 6] = str(habitat_total_cost)
        
        # Convert row to CSV format
        # Escape fields that contain commas or quotes
        csv_fields = []
        for field in row:
            field_str = str(field)
            # If field contains comma, quote, or newline, wrap in quotes and escape quotes
            if ',' in field_str or '"' in field_str or '\n' in field_str:
                field_str = '"' + field_str.replace('"', '""') + '"'
            csv_fields.append(field_str)
        
        csv_rows.append(','.join(csv_fields))
    
    # Join all rows with newline
    return '\n'.join(csv_rows)


def generate_sales_quotes_csv_from_optimizer_output(
    quote_number: str,
    client_name: str,
    development_address: str,
    base_ref: str,
    introducer: Optional[str],
    today_date: datetime,
    local_planning_authority: str,
    national_character_area: str,
    alloc_df: pd.DataFrame,
    contract_size: str = "small"
) -> str:
    """
    Generate Sales & Quotes CSV from optimizer allocation DataFrame.
    
    This is a convenience wrapper that converts the optimizer's site_hab_totals DataFrame
    (which has paired habitats already split into constituent parts) into CSV format.
    
    Args:
        quote_number: Quote number
        client_name: Client name
        development_address: Development address
        base_ref: Base reference number
        introducer: Introducer name (or None)
        today_date: Quote date
        local_planning_authority: LPA name
        national_character_area: NCA name
        alloc_df: site_hab_totals DataFrame from optimizer with columns:
            - BANK_KEY: Bank reference (e.g., "WC1P2-001")
            - bank_name: Bank name (e.g., "Nunthorpe")
            - supply_habitat: Habitat type (already split if it was paired)
            - tier: "adjacent", "far", or "local"
            - allocation_type: "paired" or "normal" (indicates original pairing)
            - units_supplied: Units for this specific habitat
            - effective_units: Effective units (with SRM applied)
            - avg_effective_unit_price: Average effective unit price
            - cost: Total cost for this habitat
        contract_size: Contract size for admin fee
    
    Returns:
        CSV string ready for download/copy
    """
    # Group allocations by bank
    # Each bank gets its own row in the CSV
    
    allocations = []
    
    # Group by bank
    if alloc_df.empty:
        return ""
    
    # Determine which column has the bank reference
    bank_ref_col = "BANK_KEY" if "BANK_KEY" in alloc_df.columns else "bank_ref"
    if bank_ref_col not in alloc_df.columns:
        bank_ref_col = "bank_id"
    
    # Group by bank
    for bank_key, bank_group in alloc_df.groupby(bank_ref_col):
        bank_name = bank_group["bank_name"].iloc[0] if "bank_name" in bank_group.columns else str(bank_key)
        
        # Determine if this is a paired allocation
        allocation_types = bank_group.get("allocation_type", pd.Series(["normal"] * len(bank_group)))
        is_paired = any(str(t).lower() == "paired" for t in allocation_types)
        
        # Get tier (spatial relation)
        tiers = bank_group.get("tier", pd.Series(["far"] * len(bank_group)))
        tier = str(tiers.iloc[0]).lower() if not tiers.empty else "far"
        
        # Map tier to spatial_relation
        if tier == "local":
            spatial_relation = "adjacent"  # Local is closer than adjacent
        elif tier == "adjacent":
            spatial_relation = "adjacent"
        else:
            spatial_relation = "far"
        
        # Calculate spatial multiplier
        if tier == "local":
            spatial_multiplier_numeric = 1.0
        elif tier == "adjacent":
            spatial_multiplier_numeric = 4.0 / 3.0
        else:  # far
            spatial_multiplier_numeric = 2.0
        
        # Aggregate habitats for this bank
        # Note: site_hab_totals already has habitats split into constituent parts
        # with correct units based on stock_use ratios
        habitats = []
        for _, row in bank_group.iterrows():
            habitat_type = str(row.get("supply_habitat", "")).strip()
            units_supplied = float(row.get("units_supplied", 0.0) or 0.0)
            
            # Use pre-calculated effective_units if available
            if "effective_units" in row:
                effective_units = float(row.get("effective_units", 0.0) or 0.0)
            else:
                effective_units = units_supplied * spatial_multiplier_numeric
            
            # Use pre-calculated avg_effective_unit_price if available
            if "avg_effective_unit_price" in row:
                avg_effective_unit_price = float(row.get("avg_effective_unit_price", 0.0) or 0.0)
            else:
                total_cost = float(row.get("cost", 0.0) or 0.0)
                avg_effective_unit_price = total_cost / effective_units if effective_units > 0 else 0.0
            
            if habitat_type:  # Only add if habitat type is not empty
                habitats.append({
                    "type": habitat_type,
                    "units_supplied": units_supplied,
                    "effective_units": effective_units,
                    "avg_effective_unit_price": avg_effective_unit_price
                })
        
        # Limit to 8 habitats (as per spec)
        habitats = habitats[:8]
        
        # Calculate totals for this allocation
        allocation_total_credits = sum(h["effective_units"] for h in habitats)
        contract_value_gbp = bank_group["cost"].sum() if "cost" in bank_group.columns else 0.0
        
        allocations.append({
            "bank_ref": str(bank_key),
            "bank_name": bank_name,
            "is_paired": is_paired,
            "spatial_relation": spatial_relation,
            "spatial_multiplier_numeric": spatial_multiplier_numeric,
            "allocation_total_credits": allocation_total_credits,
            "contract_value_gbp": contract_value_gbp,
            "habitats": habitats
        })
    
    # Generate CSV
    return generate_sales_quotes_csv(
        quote_number=quote_number,
        client_name=client_name,
        development_address=development_address,
        base_ref=base_ref,
        introducer=introducer,
        today_date=today_date,
        local_planning_authority=local_planning_authority,
        national_character_area=national_character_area,
        allocations=allocations,
        contract_size=contract_size
    )
