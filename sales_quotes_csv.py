"""
sales_quotes_csv.py - Generate CSV rows for Sales & Quotes Excel workbook.

This module converts optimiser allocation results into CSV data rows
that align with the Sales & Quotes Excel workbook column structure (A-BB).
"""

from typing import List, Dict, Any, Optional
from datetime import datetime
import pandas as pd

# Import constants from optimizer_core
from optimizer_core import ADMIN_FEE_GBP, ADMIN_FEE_FRACTIONAL_GBP


# Bank reference to bank name mapping
BANK_NAME_MAPPING = {
    "WC1P6": "Denchworth",
    "WC1P5": "Bedford",
    "WC1P2": "Nunthorpe",  # Default for WC1P2 (can also be Stokesley or Horden)
    "WC1P3": "Cobham",
    "WC1P4": "Barnsley",
    "WC1P8": "Marbury",
}

# Alternative names for specific bank refs (when there are multiple locations)
BANK_NAME_ALTERNATIVES = {
    "WC1P2": ["Stokesley", "Nunthorpe", "Horden"],
    "WC1P6": ["Denchworth", "Central Bedfordshire"],
}


def get_standardized_bank_name(bank_ref: str, bank_name: str) -> tuple[str, str, str]:
    """
    Get standardized bank name from mapping, or return 'Other' with notes.
    
    Args:
        bank_ref: Bank reference (e.g., "WC1P2")
        bank_name: Bank name from optimizer (e.g., "Nunthorpe")
    
    Returns:
        Tuple of (standardized_bank_ref_name, notes_for_column_T, source_display)
        - standardized_bank_ref_name: Either the mapped name or 'Other'
        - notes_for_column_T: Empty string or the actual bank name if using 'Other'
        - source_display: The full "ref - name" string for column AC
    """
    bank_ref = bank_ref.strip()
    bank_name = bank_name.strip()
    
    # Check if bank_ref exists in mapping
    if bank_ref in BANK_NAME_MAPPING:
        mapped_name = BANK_NAME_MAPPING[bank_ref]
        
        # Check if the provided bank_name is in alternatives
        if bank_ref in BANK_NAME_ALTERNATIVES:
            alternatives = BANK_NAME_ALTERNATIVES[bank_ref]
            # If bank_name matches one of the alternatives, use it
            if bank_name in alternatives:
                return bank_name, "", f"{bank_ref} - {bank_name}"
        
        # Use the mapped name
        return mapped_name, "", f"{bank_ref} - {mapped_name}"
    
    # Bank not in mapping - use 'Other' and add to notes
    return "Other", bank_name, f"{bank_ref} - Other"


def split_paired_habitat(habitat_type: str, units_supplied: float, effective_units: float, 
                         avg_effective_unit_price: float) -> List[Dict[str, Any]]:
    """
    Split a paired habitat (e.g., "Habitat A + Habitat B") into separate habitats.
    
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
        
        # Split units evenly (or could use more sophisticated logic if available)
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
        
        # Get standardized bank name and check if we need to use 'Other'
        standardized_bank_name, bank_fallback_note, source_display = get_standardized_bank_name(bank_ref, bank_name)
        
        # Split paired habitats (e.g., "Habitat A + Habitat B" becomes separate entries)
        expanded_habitats = []
        for habitat in habitats:
            habitat_type = habitat.get("type", "")
            units_supplied = habitat.get("units_supplied", 0.0)
            effective_units = habitat.get("effective_units", 0.0)
            avg_effective_unit_price = habitat.get("avg_effective_unit_price", 0.0)
            
            # Split if habitat contains " + "
            split_habitats = split_paired_habitat(
                habitat_type, units_supplied, effective_units, avg_effective_unit_price
            )
            expanded_habitats.extend(split_habitats)
        
        # Limit to 8 habitats (as per spec)
        expanded_habitats = expanded_habitats[:8]
        
        # Create CSV row with all columns A-CY
        # We need to create a list representing each column
        # A-BB (0-53) = 54 columns for basic fields
        # BC-CY (54-102) = 49 columns for habitats 2-8 (7 columns each)
        # Total: 103 columns (A=0 to CY=102)
        row = [""] * 103  # 103 columns from A to CY
        
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
        
        # Columns E-S (indices 4-18): blank (ignore)
        
        # Column T (index 19): Notes
        # Priority 1: Bank fallback note (if using 'Other')
        # Priority 2: SRM logic based on pairing and spatial_relation
        if bank_fallback_note:
            # If bank is not in mapping, put the actual bank name here
            row[19] = bank_fallback_note
        elif is_paired:
            if spatial_relation == "far":
                row[19] = "SRM manual (0.5)"
            elif spatial_relation == "adjacent":
                row[19] = "SRM manual (0.75)"
            # else: blank
        # else: blank for non-paired
        
        # Columns U-AB (indices 20-27): blank (ignore)
        
        # Column AC (index 28): Habitat Bank / Source of Mitigation
        # Use the standardized display format
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
        
        # Columns AE, AF, AG (indices 30-32): blank (ignore)
        
        # Column AH (index 33): Local Planning Authority
        row[33] = local_planning_authority.strip()
        
        # Column AI (index 34): National Character Area
        row[34] = national_character_area.strip()
        
        # Column AJ (index 35): blank (ignore)
        
        # Column AK (index 36): Introducer
        row[36] = introducer.strip() if introducer else "Direct"
        
        # Column AL (index 37): Quote Date
        row[37] = quote_date_str
        
        # Columns AM-AQ (indices 38-42): blank (ignore)
        
        # Column AR (index 43): Admin Fee
        row[43] = str(admin_fee)
        
        # Column AS (index 44): blank (ignore)
        
        # Columns AT-AU (indices 45-46): blank (ignore)
        
        # Habitats 1-8 start at column AV (index 47)
        # Each habitat has 7 columns: Type, # credits, ST, Standard Price, Quoted Price, Minimum, Price inc SM
        # We only populate: Type, # credits, and Quoted Price
        # Habitat 1: AV-BB (indices 47-53)
        # Habitat 2: BC-BI (indices 54-60)
        # Habitat 3: BJ-BP (indices 61-67)
        # Habitat 4: BQ-BW (indices 68-74)
        # Habitat 5: BX-CD (indices 75-81)
        # Habitat 6: CE-CK (indices 82-88)
        # Habitat 7: CL-CR (indices 89-95)
        # Habitat 8: CS-CY (indices 96-102)
        
        # Process all habitats (up to 8) - use expanded_habitats which has paired habitats split
        for hab_idx in range(min(len(expanded_habitats), 8)):
            habitat = expanded_habitats[hab_idx]
            
            # Calculate starting column index for this habitat
            # Habitat 1 starts at 47, each habitat takes 7 columns
            base_idx = 47 + (hab_idx * 7)
            
            # Column 0: Type
            row[base_idx] = str(habitat.get("type", "")).strip()
            
            # Column 1: # credits
            # Use effective_units if paired, otherwise units_supplied
            if is_paired:
                units_value = habitat.get("effective_units", 0.0)
            else:
                units_value = habitat.get("units_supplied", 0.0)
            row[base_idx + 1] = str(units_value)
            
            # Column 2: ST - leave blank (managed by Excel)
            
            # Column 3: Standard Price - leave blank (managed by Excel)
            
            # Column 4: Quoted Price (avg_effective_unit_price)
            row[base_idx + 4] = str(habitat.get("avg_effective_unit_price", 0.0))
            
            # Column 5: Minimum - leave blank (managed by Excel)
            
            # Column 6: Price inc SM - leave blank (managed by Excel)
        
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
    
    This is a convenience wrapper that converts the optimizer's DataFrame
    output into the format expected by generate_sales_quotes_csv().
    
    Args:
        quote_number: Quote number
        client_name: Client name
        development_address: Development address
        base_ref: Base reference number
        introducer: Introducer name (or None)
        today_date: Quote date
        local_planning_authority: LPA name
        national_character_area: NCA name
        alloc_df: Allocation DataFrame from optimizer with columns:
            - BANK_KEY or bank_ref: Bank reference
            - bank_name: Bank name
            - allocation_type: "paired" or "normal"
            - tier: "adjacent", "far", or "local"
            - supply_habitat: Habitat type
            - units_supplied: Units supplied
            - unit_price: Price per unit
            - cost: Total cost
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
        habitats = []
        for _, row in bank_group.iterrows():
            habitat_type = str(row.get("supply_habitat", "")).strip()
            units_supplied = float(row.get("units_supplied", 0.0) or 0.0)
            unit_price = float(row.get("unit_price", 0.0) or 0.0)
            
            # Calculate effective units
            effective_units = units_supplied * spatial_multiplier_numeric
            
            # Calculate avg effective unit price
            # effective_unit_price = total_cost / effective_units
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
