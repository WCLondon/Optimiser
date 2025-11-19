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
        # Note: We now use ST (Stock Take) = spatial_multiplier × # credits
        # For paired allocations, spatial_multiplier = 1
        # For non-paired allocations, spatial_multiplier varies based on tier
        
        # Get the numeric spatial multiplier for calculations
        if is_paired:
            sm_numeric = 1.0
        else:
            sm_numeric = spatial_multiplier_numeric
        
        total_st = 0.0  # Total Stock Take (sum of ST values)
        total_credit_price = 0.0  # Total price including SRM
        
        for h in habitats:
            # Get # credits (units_supplied for non-paired, effective_units for paired)
            if is_paired:
                credits = h.get("effective_units", 0.0)
            else:
                credits = h.get("units_supplied", 0.0)
            
            # Calculate ST = spatial_multiplier × # credits
            st = sm_numeric * credits
            total_st += st
            
            # Calculate price = ST × Quoted Price
            quoted_price = h.get("avg_effective_unit_price", 0.0)
            total_credit_price += st * quoted_price
        
        total_units = total_st
        
        # Create CSV row with all columns A-CY
        # Total: 103 columns (A=0 to CY=102)
        row = [""] * 103  # 103 columns from A to CY
        
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
        
        # Column S (index 18): blank
        
        # Column T (index 19): Notes / SRM manual
        # Priority 1: Bank fallback note (if using 'Other')
        # Priority 2: SRM logic based on pairing and spatial_relation
        if bank_fallback_note:
            # If bank is not in valid combinations, put the actual bank name here
            row[19] = bank_fallback_note
        elif is_paired:
            if spatial_relation == "far":
                row[19] = "SRM manual (0.5)"
            elif spatial_relation == "adjacent":
                row[19] = "SRM manual (0.75)"
            # else: blank
        # else: blank for non-paired
        
        # Columns U-AB (indices 20-27): blank
        
        # Column AC (index 28): Habitat Bank / Source of Mitigation
        # Use the standardized display format (first 5 chars + " - " + name)
        row[28] = source_display
        
        # Column AD (index 29): Spatial Multiplier
        if is_paired:
            # For paired allocations, use numeric 1
            row[29] = "1"
        else:
            # For non-paired, use formula
            if spatial_relation == "adjacent":
                row[29] = "=4/3"
            elif spatial_relation == "far":
                row[29] = "=2/1"
            else:
                # Default to 1 if relation not specified
                row[29] = "1"
        
        # Column AE (index 30): Total Units
        row[30] = f"{total_units:.2f}"
        
        # Column AF (index 31): Contract Value
        if alloc_idx == 0:
            contract_value = total_credit_price + admin_fee
        else:
            contract_value = total_credit_price
        row[31] = f"{contract_value:.2f}"
        
        # Column AG (index 32): blank
        
        # Column AH (index 33): Local Planning Authority
        row[33] = local_planning_authority.strip()
        
        # Column AI (index 34): National Character Area
        row[34] = national_character_area.strip()
        
        # Column AJ (index 35): blank
        
        # Column AK (index 36): Introducer
        row[36] = introducer.strip() if introducer else "Direct"
        
        # Column AL (index 37): Quote Date
        row[37] = quote_date_str
        
        # Column AM (index 38): Quote Period (always "30")
        row[38] = "30"
        
        # Column AN (index 39): Quote Expiry (Formula: Quote Date + Quote Period)
        # Excel formula: =AL{row}+AM{row}
        # Row number is 1-based (first data row is row 1)
        row_number = alloc_idx + 1
        row[39] = f"=AL{row_number}+AM{row_number}"
        
        # Columns AO-AQ (indices 40-42): blank
        
        # Column AR (index 43): Admin Fee (only on first row if multi-row)
        if alloc_idx == 0:
            row[43] = f"{admin_fee:.2f}"
        # else: blank for subsequent rows
        
        # Column AS (index 44): blank
        
        # Column AT (index 45): Total Credit Price
        row[45] = f"{total_credit_price:.2f}"
        
        # Column AU (index 46): Total Units
        row[46] = f"{total_units:.2f}"
        
        # Note: Column AV (index 47) is now the start of habitats
        
        # Habitats 1-8 start at column AV (index 47)
        # Each habitat has 7 columns: Type, # credits, ST, blank, Quoted Price, blank, Price inc SRM
        # Habitat 1: AV-BB (indices 47-53)
        # Habitat 2: BC-BI (indices 54-60)
        # Habitat 3: BJ-BP (indices 61-67)
        # Habitat 4: BQ-BW (indices 68-74)
        # Habitat 5: BX-CD (indices 75-81)
        # Habitat 6: CE-CK (indices 82-88)
        # Habitat 7: CL-CR (indices 89-95)
        # Habitat 8: CS-CY (indices 96-102)
        
        # Get numeric spatial multiplier for ST calculation
        if is_paired:
            sm_numeric = 1.0
        else:
            sm_numeric = spatial_multiplier_numeric
        
        # Process all habitats (up to 8) - each habitat represents exact allocation data
        for hab_idx in range(min(len(habitats), 8)):
            habitat = habitats[hab_idx]
            
            # Calculate starting column index for this habitat
            # Habitat 1 starts at 47 (Column AV), each habitat takes 7 columns
            base_idx = 47 + (hab_idx * 7)
            
            # Column 0: Type
            row[base_idx] = str(habitat.get("type", "")).strip()
            
            # Column 1: # credits
            # Use effective_units if paired, otherwise units_supplied
            if is_paired:
                units_value = habitat.get("effective_units", 0.0)
            else:
                units_value = habitat.get("units_supplied", 0.0)
            row[base_idx + 1] = f"{units_value:.2f}"
            
            # Column 2: ST (Stock Take) = spatial_multiplier × # credits
            st = sm_numeric * units_value
            row[base_idx + 2] = f"{st:.2f}"
            
            # Column 3: blank (was Standard Price)
            
            # Column 4: Quoted Price (avg_effective_unit_price)
            quoted_price = habitat.get("avg_effective_unit_price", 0.0)
            row[base_idx + 4] = f"{quoted_price:.2f}"
            
            # Column 5: blank (was Minimum)
            
            # Column 6: Price inc SRM (Total Cost) = ST × Quoted Price
            habitat_total_cost = st * quoted_price
            row[base_idx + 6] = f"{habitat_total_cost:.2f}"
        
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
        # For paired allocations, split them into separate habitat columns
        habitats = []
        for _, row in bank_group.iterrows():
            habitat_type = str(row.get("supply_habitat", "")).strip()
            units_supplied = float(row.get("units_supplied", 0.0) or 0.0)
            allocation_type = str(row.get("allocation_type", "")).lower()
            
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
            
            # Check if this is a paired allocation that needs to be split
            if allocation_type == "paired" and "paired_parts" in row and row["paired_parts"]:
                try:
                    import json
                    paired_parts = json.loads(str(row["paired_parts"]))
                    if paired_parts and len(paired_parts) >= 2:
                        # Split the paired allocation into separate habitat entries
                        for idx, part in enumerate(paired_parts):
                            part_habitat = str(part.get("habitat", "")).strip()
                            stock_use = float(part.get("stock_use", 0.5))
                            part_unit_price = float(part.get("unit_price", 0.0))
                            
                            # Calculate units for this part based on stock_use ratio
                            part_units = units_supplied * stock_use
                            part_effective_units = effective_units * stock_use
                            
                            if part_habitat:
                                habitats.append({
                                    "type": part_habitat,
                                    "units_supplied": part_units,
                                    "effective_units": part_effective_units,
                                    "avg_effective_unit_price": part_unit_price
                                })
                    else:
                        # Fallback: split by " + " in habitat name
                        if " + " in habitat_type:
                            parts = [p.strip() for p in habitat_type.split(" + ")]
                            for part_name in parts:
                                habitats.append({
                                    "type": part_name,
                                    "units_supplied": units_supplied / len(parts),
                                    "effective_units": effective_units / len(parts),
                                    "avg_effective_unit_price": avg_effective_unit_price
                                })
                        else:
                            habitats.append({
                                "type": habitat_type,
                                "units_supplied": units_supplied,
                                "effective_units": effective_units,
                                "avg_effective_unit_price": avg_effective_unit_price
                            })
                except Exception:
                    # If parsing fails, add as single habitat
                    if habitat_type:
                        habitats.append({
                            "type": habitat_type,
                            "units_supplied": units_supplied,
                            "effective_units": effective_units,
                            "avg_effective_unit_price": avg_effective_unit_price
                        })
            elif habitat_type:  # Normal allocation or paired without paired_parts
                # Check if habitat name contains " + " and split if needed
                if " + " in habitat_type:
                    parts = [p.strip() for p in habitat_type.split(" + ")]
                    for part_name in parts:
                        habitats.append({
                            "type": part_name,
                            "units_supplied": units_supplied / len(parts),
                            "effective_units": effective_units / len(parts),
                            "avg_effective_unit_price": avg_effective_unit_price
                        })
                else:
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
