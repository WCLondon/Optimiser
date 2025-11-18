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
    """Test bank name standardization."""
    # Valid combination
    name, note, display = get_standardized_bank_name("WC1P2", "Nunthorpe")
    assert name == "Nunthorpe"
    assert note == ""
    assert display == "WC1P2 - Nunthorpe"
    
    # Test with longer bank_id (takes first 5 chars)
    name, note, display = get_standardized_bank_name("WC1P2-001", "Nunthorpe")
    assert name == "Nunthorpe"
    assert note == ""
    assert display == "WC1P2 - Nunthorpe"
    
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
    
    # Corrected column structure
    assert fields[1] == "Test Client"  # B: Client
    assert fields[3] == "BNG00001"  # D: Ref (no suffix)
    assert fields[17] == ""  # R: blank
    assert fields[18] == ""  # S: Notes (blank for non-paired)
    assert fields[27] == "WC1P2 - Nunthorpe"  # AB: Bank (CORRECTED - was at 28)
    assert fields[28] == "=4/3"  # AC: Spatial Multiplier (RESTORED)
    assert fields[29] == "10.0"  # AD: Total Units (CORRECT)
    assert fields[30] == "10500.0"  # AE: Contract Value (10000 + 500) (CORRECT)
    assert fields[32] == "Test LPA"  # AG: LPA (CORRECTED - moved from 33)
    assert fields[33] == "Test NCA"  # AH: NCA (CORRECTED - moved from 34)
    assert fields[35] == "Test"  # AJ: Introducer (CORRECTED - moved from 36)
    assert fields[36] == "10/11/2025"  # AK: Quote Date (CORRECTED - moved from 37)
    assert fields[37] == "30"  # AL: Quote Period (CORRECTED - moved from 38)
    assert fields[43] == "500.0"  # AR: Admin Fee
    assert fields[44] == "10000.0"  # AS: Total Credit Price (CORRECT)
    assert fields[45] == "10.0"  # AT: Total Units (CORRECT)
    assert fields[47] == "Grassland"  # AV: Habitat Type
    assert fields[48] == "10.0"  # AW: Units
    assert fields[51] == "1000.0"  # AZ: Quoted Price
    assert fields[53] == "10000.0"  # BB: Total Cost


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
    assert rows[0][43] == "500.0"  # Admin fee on first row
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
    
    assert fields[18] == "SRM manual (0.5)"  # S: Notes (CORRECTED from 17)
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
    
    # Habitat 1: exact values preserved
    assert fields[47] == "Grassland"
    assert fields[48] == "20.0"  # NOT 14.545 (29.09/2)
    assert fields[51] == "1500.0"
    assert fields[53] == "30000.0"  # 20 * 1500
    
    # Habitat 2: exact values preserved
    assert fields[54] == "Woodland"
    assert fields[55] == "9.09"  # NOT 14.545 (29.09/2)
    assert fields[58] == "1800.0"
    assert fields[60] == "16362.0"  # 9.09 * 1800
    
    # Totals
    assert float(fields[44]) == 46362.0  # Total credit price
    assert float(fields[45]) == 29.09  # Total units


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
