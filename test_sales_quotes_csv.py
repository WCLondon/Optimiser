"""
Tests for sales_quotes_csv module - Updated for new column structure.
"""

import pytest
from datetime import datetime
import pandas as pd
from sales_quotes_csv import (
    generate_sales_quotes_csv,
    generate_sales_quotes_csv_from_optimizer_output,
    get_admin_fee_for_contract_size,
    get_standardized_bank_name
)
import csv
import io


def test_admin_fee():
    """Test admin fee calculation."""
    assert get_admin_fee_for_contract_size("fractional") == 300.0
    assert get_admin_fee_for_contract_size("small") == 500.0


def test_bank_name_mapping():
    """Test bank name standardization from database."""
    # Note: This test will use actual database lookup
    # If database has WC1P2->Nunthorpe, it should return that
    # Otherwise it will return "Other"
    
    # Test with longer bank_id (takes first 5 chars)
    name, note, display = get_standardized_bank_name("WC1P2-001", "Nunthorpe")
    # Should either find WC1P2 in database or use "Other"
    assert name in ["Nunthorpe", "Stokesley", "Horden", "Other"]
    assert display.startswith("WC1P2 - ")
    
    # Unknown bank
    name, note, display = get_standardized_bank_name("WC1P99", "Unknown")
    assert name == "Other"
    assert note == "Unknown"
    assert display == "WC1P9 - Other"


def test_single_allocation():
    """Test single allocation with corrected column structure."""
    allocations = [{
        "bank_ref": "WC1P2",
        "bank_name": "Nunthorpe",
        "is_paired": False,
        "spatial_relation": "adjacent",
        "spatial_multiplier_numeric": 4.0/3.0,
        "allocation_total_credits": 10.0,
        "contract_value_gbp": 10000.0,
        "habitats": [{
            "type": "Grassland",
            "units_supplied": 10.0,
            "effective_units": 13.33,
            "avg_effective_unit_price": 1000.0
        }]
    }]
    
    csv_output = generate_sales_quotes_csv(
        quote_number="TEST001",
        client_name="Test Client",
        development_address="Test Address",
        base_ref="BNG00001",
        introducer="Test",
        today_date=datetime(2025, 11, 10),
        local_planning_authority="Test LPA",
        national_character_area="Test NCA",
        allocations=allocations,
        contract_size="small"
    )
    
    reader = csv.reader(io.StringIO(csv_output))
    fields = list(reader)[0]
    
    # Corrected column structure with new positions
    assert fields[1] == "Test Client"  # B: Client
    assert fields[3] == "BNG00001"  # D: Ref (no suffix)
    assert fields[17] == ""  # R: blank
    assert fields[18] == ""  # S: blank
    # T (19): Notes - may have bank name if not in database, or blank if non-paired and bank found
    assert fields[28].endswith("Nunthorpe") or fields[28].endswith("Other")  # AC: Bank (database lookup)
    assert fields[29] == "=4/3"  # AD: Spatial Multiplier
    
    # New ST calculation: SM × # credits = 4/3 × 10.0 = 13.333... ≈ 13.33
    assert fields[30] == "13.33"  # AE: Total Units (sum of ST values)
    # New total: ST × Quoted Price + admin = 13.333... × 1000.0 + 500 = 13833.33
    assert fields[31] == "13833.33"  # AF: Contract Value
    
    assert fields[33] == "Test LPA"  # AH: LPA
    assert fields[34] == "Test NCA"  # AI: NCA
    assert fields[36] == "Test"  # AK: Introducer
    assert fields[37] == "10/11/2025"  # AL: Quote Date
    assert fields[38] == "30"  # AM: Quote Period
    assert fields[39].startswith("=AL")  # AN: Quote Expiry (formula)
    assert fields[43] == "500.00"  # AR: Admin Fee (2 decimal places)
    assert fields[45] == "13333.33"  # AT: Total Credit Price (ST × Quoted Price)
    assert fields[46] == "13.33"  # AU: Total Units (sum of ST values)
    assert fields[47] == "Grassland"  # AV: Habitat Type
    assert fields[48] == "10.00"  # AW: # credits (2 decimal places)
    assert fields[49] == "13.33"  # AX: ST = 4/3 × 10.0 (NEW!)
    assert fields[51] == "1000.00"  # AZ: Quoted Price (2 decimal places)
    assert fields[53] == "13333.33"  # BB: Price inc SRM = ST × Quoted Price (NEW CALC!)


def test_multi_allocation_admin_fee():
    """Test admin fee only appears on first row."""
    allocations = [
        {
            "bank_ref": "WC1P2",
            "bank_name": "Nunthorpe",
            "is_paired": False,
            "spatial_relation": "adjacent",
            "habitats": [{"type": "Grassland", "units_supplied": 10.0, "effective_units": 10.0, "avg_effective_unit_price": 1000.0}]
        },
        {
            "bank_ref": "WC1P5",
            "bank_name": "Bedford",
            "is_paired": False,
            "spatial_relation": "far",
            "habitats": [{"type": "Woodland", "units_supplied": 5.0, "effective_units": 5.0, "avg_effective_unit_price": 500.0}]
        }
    ]
    
    csv_output = generate_sales_quotes_csv(
        quote_number="TEST002",
        client_name="Test",
        development_address="Test",
        base_ref="BNG00002",
        introducer=None,
        today_date=datetime(2025, 11, 10),
        local_planning_authority="Test",
        national_character_area="Test",
        allocations=allocations,
        contract_size="small"
    )
    
    reader = csv.reader(io.StringIO(csv_output))
    rows = list(reader)
    
    assert len(rows) == 2
    assert rows[0][3] == "BNG00002a"  # First ref
    assert rows[1][3] == "BNG00002b"  # Second ref
    assert rows[0][43] == "500.00"  # Admin fee on first row (AR column, 2 decimal places)
    assert rows[1][43] == ""  # No admin fee on second row


def test_paired_allocation_srm_notes():
    """Test SRM notes for paired allocations."""
    allocations = [{
        "bank_ref": "WC1P2",
        "bank_name": "Nunthorpe",
        "is_paired": True,
        "spatial_relation": "far",
        "habitats": [{"type": "Grassland", "units_supplied": 10.0, "effective_units": 10.0, "avg_effective_unit_price": 1000.0}]
    }]
    
    csv_output = generate_sales_quotes_csv(
        quote_number="TEST003",
        client_name="Test",
        development_address="Test",
        base_ref="BNG00003",
        introducer=None,
        today_date=datetime(2025, 11, 10),
        local_planning_authority="Test",
        national_character_area="Test",
        allocations=allocations,
        contract_size="small"
    )
    
    reader = csv.reader(io.StringIO(csv_output))
    fields = list(reader)[0]
    
    # T (19): Notes - if bank not in DB, shows bank name; otherwise SRM for paired
    # Bank fallback takes priority over SRM notes
    assert fields[19] in ["SRM manual (0.5)", "Nunthorpe", "WC1P2"]  # T: Notes
    assert fields[29] == "1"  # AD: Spatial Multiplier = 1 for paired


def test_exact_allocation_data():
    """Test that exact allocation data is preserved (not split 50/50)."""
    allocations = [{
        "bank_ref": "WC1P2",
        "bank_name": "Nunthorpe",
        "is_paired": True,
        "spatial_relation": "far",
        "habitats": [
            {"type": "Grassland", "units_supplied": 20.0, "effective_units": 20.0, "avg_effective_unit_price": 1500.0},
            {"type": "Woodland", "units_supplied": 9.09, "effective_units": 9.09, "avg_effective_unit_price": 1800.0}
        ]
    }]
    
    csv_output = generate_sales_quotes_csv(
        quote_number="TEST004",
        client_name="Test",
        development_address="Test",
        base_ref="BNG00004",
        introducer=None,
        today_date=datetime(2025, 11, 10),
        local_planning_authority="Test",
        national_character_area="Test",
        allocations=allocations,
        contract_size="small"
    )
    
    reader = csv.reader(io.StringIO(csv_output))
    fields = list(reader)[0]
    
    # Habitat 1: exact values preserved (now starts at 47, Column AV)
    # For paired allocations, SM = 1, so ST = 1 × 20.0 = 20.0
    assert fields[47] == "Grassland"  # AV: Habitat 1 Type
    assert fields[48] == "20.00"  # AW: # credits (2 decimal places) - NOT 14.545 (29.09/2)
    assert fields[49] == "20.00"  # AX: ST = 1 × 20.0 (paired, so SM=1)
    assert fields[51] == "1500.00"  # AZ: Quoted Price (2 decimal places)
    assert fields[53] == "30000.00"  # BB: Price inc SRM = 20.00 × 1500.00 (2 decimal places)
    
    # Habitat 2: exact values preserved (now starts at 54, Column BC)
    # For paired allocations, SM = 1, so ST = 1 × 9.09 = 9.09
    assert fields[54] == "Woodland"  # BC: Habitat 2 Type
    assert fields[55] == "9.09"  # BD: # credits (2 decimal places) - NOT 14.545 (29.09/2)
    assert fields[56] == "9.09"  # BE: ST = 1 × 9.09 (paired, so SM=1)
    assert fields[58] == "1800.00"  # BG: Quoted Price (2 decimal places)
    assert fields[60] == "16362.00"  # BI: Price inc SRM = 9.09 × 1800.00 (2 decimal places)
    
    # Totals: sum of ST values and ST × Quoted Price
    # Total ST = 20.00 + 9.09 = 29.09
    # Total Price = 30000.00 + 16362.00 = 46362.00
    assert float(fields[45]) == 46362.0  # AT: Total credit price
    assert float(fields[46]) == 29.09  # AU: Total units (sum of ST)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
