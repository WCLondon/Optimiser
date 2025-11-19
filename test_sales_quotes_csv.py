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
    # S (18): Notes - may have bank name if not in database, or blank if non-paired and bank found
    # assert fields[18] == ""  # S: Notes (depends on database)
    assert fields[27].endswith("Nunthorpe") or fields[27].endswith("Other")  # AB: Bank (database lookup)
    assert fields[28] == "=4/3"  # AC: Spatial Multiplier (RESTORED)
    
    # New ST calculation: SM × # credits = 4/3 × 10.0 = 13.333... ≈ 13.33
    assert fields[29] == "13.33"  # AD: Total Units (sum of ST values)
    # New total: ST × Quoted Price + admin = 13.333... × 1000.0 + 500 = 13833.33
    assert fields[30] == "13833.33"  # AE: Contract Value (CORRECT)
    
    assert fields[32] == "Test LPA"  # AG: LPA (CORRECTED - moved from 33)
    assert fields[33] == "Test NCA"  # AH: NCA (CORRECTED - moved from 34)
    assert fields[35] == "Test"  # AJ: Introducer (CORRECTED - moved from 36)
    assert fields[36] == "10/11/2025"  # AK: Quote Date (CORRECTED - moved from 37)
    assert fields[37] == "30"  # AL: Quote Period (CORRECTED - moved from 38)
    assert fields[38].startswith("=AK")  # AM: Quote Expiry (formula)
    assert fields[42] == "500.00"  # AQ: Admin Fee (2 decimal places)
    assert fields[44] == "13333.33"  # AS: Total Credit Price (ST × Quoted Price)
    assert fields[45] == "13.33"  # AT: Total Units (sum of ST values)
    assert fields[46] == "Grassland"  # AU: Habitat Type (MOVED LEFT from 47)
    assert fields[47] == "10.00"  # AV: # credits (2 decimal places)
    assert fields[48] == "13.33"  # AW: ST = 4/3 × 10.0 (NEW!)
    assert fields[50] == "1000.00"  # AY: Quoted Price (2 decimal places)
    assert fields[52] == "13333.33"  # BA: Price inc SRM = ST × Quoted Price (NEW CALC!)


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
    assert rows[0][42] == "500.00"  # Admin fee on first row (2 decimal places)
    assert rows[1][42] == ""  # No admin fee on second row


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
    
    # S (18): Notes - if bank not in DB, shows bank name; otherwise SRM for paired
    # Bank fallback takes priority over SRM notes
    assert fields[18] in ["SRM manual (0.5)", "Nunthorpe"]  # S: Notes
    assert fields[28] == "1"  # AC: Spatial Multiplier = 1 for paired


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
    
    # Habitat 1: exact values preserved (MOVED LEFT - now starts at 46)
    # For paired allocations, SM = 1, so ST = 1 × 20.0 = 20.0
    assert fields[46] == "Grassland"  # AU: Habitat 1 Type (MOVED from 47)
    assert fields[47] == "20.00"  # AV: # credits (2 decimal places) - NOT 14.545 (29.09/2)
    assert fields[48] == "20.00"  # AW: ST = 1 × 20.0 (paired, so SM=1)
    assert fields[50] == "1500.00"  # AY: Quoted Price (2 decimal places)
    assert fields[52] == "30000.00"  # BA: Price inc SRM = 20.00 × 1500.00 (2 decimal places)
    
    # Habitat 2: exact values preserved (MOVED LEFT - now starts at 53)
    # For paired allocations, SM = 1, so ST = 1 × 9.09 = 9.09
    assert fields[53] == "Woodland"  # BB: Habitat 2 Type (MOVED from 54)
    assert fields[54] == "9.09"  # BC: # credits (2 decimal places) - NOT 14.545 (29.09/2)
    assert fields[55] == "9.09"  # BD: ST = 1 × 9.09 (paired, so SM=1)
    assert fields[57] == "1800.00"  # BF: Quoted Price (2 decimal places)
    assert fields[59] == "16362.00"  # BH: Price inc SRM = 9.09 × 1800.00 (2 decimal places)
    
    # Totals: sum of ST values and ST × Quoted Price
    # Total ST = 20.00 + 9.09 = 29.09
    # Total Price = 30000.00 + 16362.00 = 46362.00
    assert float(fields[44]) == 46362.0  # Total credit price
    assert float(fields[45]) == 29.09  # Total units (sum of ST)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
