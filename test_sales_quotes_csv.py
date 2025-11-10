"""
Tests for sales_quotes_csv module.

Tests the CSV generation for Sales & Quotes Excel workbook.
"""

import pytest
from datetime import datetime
import pandas as pd
from sales_quotes_csv import (
    generate_sales_quotes_csv,
    generate_sales_quotes_csv_from_optimizer_output,
    get_admin_fee_for_contract_size
)


def test_admin_fee_fractional():
    """Test admin fee for fractional contract size."""
    assert get_admin_fee_for_contract_size("fractional") == 300.0
    assert get_admin_fee_for_contract_size("Fractional") == 300.0
    assert get_admin_fee_for_contract_size("FRACTIONAL") == 300.0


def test_admin_fee_standard():
    """Test admin fee for standard contract sizes."""
    assert get_admin_fee_for_contract_size("small") == 500.0
    assert get_admin_fee_for_contract_size("medium") == 500.0
    assert get_admin_fee_for_contract_size("large") == 500.0


def test_single_allocation_basic():
    """Test CSV generation for single allocation."""
    allocations = [{
        "bank_ref": "WC1P2",
        "bank_name": "Nunthorpe",
        "is_paired": False,
        "spatial_relation": "adjacent",
        "spatial_multiplier_numeric": 4.0/3.0,
        "allocation_total_credits": 10.5,
        "contract_value_gbp": 15000.0,
        "habitats": [{
            "type": "Grassland - Other neutral grassland",
            "units_supplied": 10.0,
            "effective_units": 13.33,
            "avg_effective_unit_price": 1125.0
        }]
    }]
    
    csv_output = generate_sales_quotes_csv(
        quote_number="1923",
        client_name="David Evans",
        development_address="123 Test Street, London",
        base_ref="BNG01640",
        introducer="John Smith",
        today_date=datetime(2025, 11, 10),
        local_planning_authority="Westminster",
        national_character_area="Thames Valley",
        allocations=allocations,
        contract_size="small"
    )
    
    # Parse CSV
    lines = csv_output.strip().split('\n')
    assert len(lines) == 1  # One allocation = one line
    
    # For proper CSV parsing, we should handle quoted fields
    # Simple split won't work for fields with commas
    # Let's check the raw output contains the expected data
    assert "David Evans" in csv_output  # Client
    assert "123 Test Street, London" in csv_output  # Address (will be quoted)
    assert "BNG01640," in csv_output  # Ref (no suffix for single allocation)
    assert "WC1P2 - Nunthorpe" in csv_output  # Bank
    assert "=4/3" in csv_output  # Spatial Multiplier (formula for adjacent)
    assert "Westminster" in csv_output  # LPA
    assert "Thames Valley" in csv_output  # NCA
    assert "John Smith" in csv_output  # Introducer
    assert "10/11/2025" in csv_output  # Quote Date
    assert "500.0" in csv_output  # Admin Fee
    assert "Grassland - Other neutral grassland" in csv_output  # Habitat Type
    
    # For more precise checking, use proper CSV parsing
    import csv
    import io
    reader = csv.reader(io.StringIO(csv_output))
    fields = next(reader)
    
    assert fields[1] == "David Evans"  # Column B: Client
    assert fields[2] == "123 Test Street, London"  # Column C: Address
    assert fields[3] == "BNG01640"  # Column D: Ref (no suffix for single allocation)
    assert fields[19] == ""  # Column T: Notes (blank for non-paired)
    assert fields[28] == "WC1P2 - Nunthorpe"  # Column AC: Bank
    assert fields[29] == "=4/3"  # Column AD: Spatial Multiplier (formula for adjacent)
    assert fields[33] == "Westminster"  # Column AH: LPA
    assert fields[34] == "Thames Valley"  # Column AI: NCA
    assert fields[36] == "John Smith"  # Column AK: Introducer
    assert fields[37] == "10/11/2025"  # Column AL: Quote Date
    assert fields[43] == "500.0"  # Column AR: Admin Fee
    assert fields[47] == "Grassland - Other neutral grassland"  # Column AV: Habitat 1 Type
    assert fields[48] == "10.0"  # Column AW: Habitat 1 # credits (uses units_supplied for non-paired)
    assert fields[49] == ""  # Column AX: Habitat 1 ST (blank)
    assert fields[50] == ""  # Column AY: Habitat 1 Standard Price (blank)
    assert fields[51] == "1125.0"  # Column AZ: Habitat 1 Quoted Price
    assert fields[52] == ""  # Column BA: Habitat 1 Minimum (blank)
    assert fields[53] == ""  # Column BB: Habitat 1 Price inc SM (blank)


def test_multi_allocation_ref_suffixing():
    """Test that multi-bank allocations get ref suffixes (a, b, c)."""
    allocations = [
        {
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
                "avg_effective_unit_price": 750.0
            }]
        },
        {
            "bank_ref": "WC2P3",
            "bank_name": "Oakwood",
            "is_paired": False,
            "spatial_relation": "far",
            "spatial_multiplier_numeric": 2.0,
            "allocation_total_credits": 5.0,
            "contract_value_gbp": 5000.0,
            "habitats": [{
                "type": "Woodland",
                "units_supplied": 5.0,
                "effective_units": 10.0,
                "avg_effective_unit_price": 500.0
            }]
        }
    ]
    
    csv_output = generate_sales_quotes_csv(
        quote_number="1924",
        client_name="Jane Doe",
        development_address="456 Another St",
        base_ref="BNG01641",
        introducer=None,  # Test "Direct"
        today_date=datetime(2025, 11, 10),
        local_planning_authority="Camden",
        national_character_area="London Basin",
        allocations=allocations,
        contract_size="medium"
    )
    
    lines = csv_output.strip().split('\n')
    assert len(lines) == 2  # Two allocations = two lines
    
    # First allocation should have 'a' suffix
    fields1 = lines[0].split(',')
    assert fields1[3] == "BNG01641a"  # Column D: Ref with 'a' suffix
    assert fields1[36] == "Direct"  # Column AK: Introducer (default to Direct)
    
    # Second allocation should have 'b' suffix
    fields2 = lines[1].split(',')
    assert fields2[3] == "BNG01641b"  # Column D: Ref with 'b' suffix


def test_paired_allocation_srm_notes():
    """Test SRM notes for paired allocations."""
    # Test paired + far
    allocations_far = [{
        "bank_ref": "WC1P2",
        "bank_name": "Nunthorpe",
        "is_paired": True,
        "spatial_relation": "far",
        "spatial_multiplier_numeric": 1.0,
        "allocation_total_credits": 10.0,
        "contract_value_gbp": 10000.0,
        "habitats": [{
            "type": "Grassland",
            "units_supplied": 10.0,
            "effective_units": 10.0,
            "avg_effective_unit_price": 1000.0
        }]
    }]
    
    csv_far = generate_sales_quotes_csv(
        quote_number="1925",
        client_name="Test Client",
        development_address="Test Address",
        base_ref="BNG01642",
        introducer="Test Introducer",
        today_date=datetime(2025, 11, 10),
        local_planning_authority="Test LPA",
        national_character_area="Test NCA",
        allocations=allocations_far,
        contract_size="small"
    )
    
    fields_far = csv_far.split(',')
    assert fields_far[19] == "SRM manual (0.5)"  # Column T: Notes for paired + far
    assert fields_far[29] == "1"  # Column AD: Spatial Multiplier (numeric 1 for paired)
    
    # Test paired + adjacent
    allocations_adj = [{
        "bank_ref": "WC1P2",
        "bank_name": "Nunthorpe",
        "is_paired": True,
        "spatial_relation": "adjacent",
        "spatial_multiplier_numeric": 1.0,
        "allocation_total_credits": 10.0,
        "contract_value_gbp": 10000.0,
        "habitats": [{
            "type": "Grassland",
            "units_supplied": 10.0,
            "effective_units": 10.0,
            "avg_effective_unit_price": 1000.0
        }]
    }]
    
    csv_adj = generate_sales_quotes_csv(
        quote_number="1926",
        client_name="Test Client",
        development_address="Test Address",
        base_ref="BNG01643",
        introducer="Test Introducer",
        today_date=datetime(2025, 11, 10),
        local_planning_authority="Test LPA",
        national_character_area="Test NCA",
        allocations=allocations_adj,
        contract_size="small"
    )
    
    fields_adj = csv_adj.split(',')
    assert fields_adj[19] == "SRM manual (0.75)"  # Column T: Notes for paired + adjacent
    assert fields_adj[29] == "1"  # Column AD: Spatial Multiplier (numeric 1 for paired)


def test_non_paired_spatial_multiplier_formulas():
    """Test spatial multiplier formulas for non-paired allocations."""
    # Test adjacent (should be =4/3)
    allocations_adj = [{
        "bank_ref": "WC1P2",
        "bank_name": "Nunthorpe",
        "is_paired": False,
        "spatial_relation": "adjacent",
        "spatial_multiplier_numeric": 4.0/3.0,
        "allocation_total_credits": 10.0,
        "contract_value_gbp": 10000.0,
        "habitats": []
    }]
    
    csv_adj = generate_sales_quotes_csv(
        quote_number="1927",
        client_name="Test",
        development_address="Test",
        base_ref="BNG01644",
        introducer=None,
        today_date=datetime(2025, 11, 10),
        local_planning_authority="Test",
        national_character_area="Test",
        allocations=allocations_adj,
        contract_size="small"
    )
    
    fields_adj = csv_adj.split(',')
    assert fields_adj[29] == "=4/3"  # Column AD: Formula for adjacent
    
    # Test far (should be =2/1)
    allocations_far = [{
        "bank_ref": "WC1P2",
        "bank_name": "Nunthorpe",
        "is_paired": False,
        "spatial_relation": "far",
        "spatial_multiplier_numeric": 2.0,
        "allocation_total_credits": 10.0,
        "contract_value_gbp": 10000.0,
        "habitats": []
    }]
    
    csv_far = generate_sales_quotes_csv(
        quote_number="1928",
        client_name="Test",
        development_address="Test",
        base_ref="BNG01645",
        introducer=None,
        today_date=datetime(2025, 11, 10),
        local_planning_authority="Test",
        national_character_area="Test",
        allocations=allocations_far,
        contract_size="small"
    )
    
    fields_far = csv_far.split(',')
    assert fields_far[29] == "=2/1"  # Column AD: Formula for far


def test_habitat_units_paired_vs_non_paired():
    """Test that habitat units use effective_units for paired, units_supplied for non-paired."""
    # Paired: should use effective_units
    allocations_paired = [{
        "bank_ref": "WC1P2",
        "bank_name": "Nunthorpe",
        "is_paired": True,
        "spatial_relation": "far",
        "spatial_multiplier_numeric": 1.0,
        "allocation_total_credits": 10.0,
        "contract_value_gbp": 10000.0,
        "habitats": [{
            "type": "Grassland",
            "units_supplied": 8.0,
            "effective_units": 10.0,
            "avg_effective_unit_price": 1000.0
        }]
    }]
    
    csv_paired = generate_sales_quotes_csv(
        quote_number="1929",
        client_name="Test",
        development_address="Test",
        base_ref="BNG01646",
        introducer=None,
        today_date=datetime(2025, 11, 10),
        local_planning_authority="Test",
        national_character_area="Test",
        allocations=allocations_paired,
        contract_size="small"
    )
    
    fields_paired = csv_paired.split(',')
    assert fields_paired[48] == "10.0"  # Column AW: Uses effective_units for paired
    
    # Non-paired: should use units_supplied
    allocations_non_paired = [{
        "bank_ref": "WC1P2",
        "bank_name": "Nunthorpe",
        "is_paired": False,
        "spatial_relation": "far",
        "spatial_multiplier_numeric": 2.0,
        "allocation_total_credits": 10.0,
        "contract_value_gbp": 10000.0,
        "habitats": [{
            "type": "Grassland",
            "units_supplied": 8.0,
            "effective_units": 16.0,
            "avg_effective_unit_price": 625.0
        }]
    }]
    
    csv_non_paired = generate_sales_quotes_csv(
        quote_number="1930",
        client_name="Test",
        development_address="Test",
        base_ref="BNG01647",
        introducer=None,
        today_date=datetime(2025, 11, 10),
        local_planning_authority="Test",
        national_character_area="Test",
        allocations=allocations_non_paired,
        contract_size="small"
    )
    
    fields_non_paired = csv_non_paired.split(',')
    assert fields_non_paired[48] == "8.0"  # Column AW: Uses units_supplied for non-paired


def test_csv_escaping():
    """Test that CSV fields with commas/quotes are properly escaped."""
    allocations = [{
        "bank_ref": "WC1P2",
        "bank_name": "Test, Bank",  # Contains comma
        "is_paired": False,
        "spatial_relation": "far",
        "spatial_multiplier_numeric": 2.0,
        "allocation_total_credits": 10.0,
        "contract_value_gbp": 10000.0,
        "habitats": [{
            "type": "Grassland \"Special\"",  # Contains quotes
            "units_supplied": 10.0,
            "effective_units": 20.0,
            "avg_effective_unit_price": 500.0
        }]
    }]
    
    csv_output = generate_sales_quotes_csv(
        quote_number="1931",
        client_name="Test, Client",  # Contains comma
        development_address="Test Address",
        base_ref="BNG01648",
        introducer=None,
        today_date=datetime(2025, 11, 10),
        local_planning_authority="Test",
        national_character_area="Test",
        allocations=allocations,
        contract_size="small"
    )
    
    # Check that fields with commas are quoted
    assert '"Test, Client"' in csv_output
    assert '"WC1P2 - Test, Bank"' in csv_output
    assert 'Grassland ""Special""' in csv_output  # Quotes escaped


def test_generate_from_dataframe():
    """Test generating CSV from optimizer DataFrame output."""
    # Create a sample allocation DataFrame
    alloc_df = pd.DataFrame([
        {
            "BANK_KEY": "WC1P2",
            "bank_name": "Nunthorpe",
            "allocation_type": "normal",
            "tier": "adjacent",
            "supply_habitat": "Grassland - Other neutral grassland",
            "units_supplied": 10.0,
            "unit_price": 1000.0,
            "cost": 10000.0
        }
    ])
    
    csv_output = generate_sales_quotes_csv_from_optimizer_output(
        quote_number="1932",
        client_name="Test Client",
        development_address="Test Address",
        base_ref="BNG01649",
        introducer="Test Introducer",
        today_date=datetime(2025, 11, 10),
        local_planning_authority="Test LPA",
        national_character_area="Test NCA",
        alloc_df=alloc_df,
        contract_size="small"
    )
    
    # Should produce one line
    lines = csv_output.strip().split('\n')
    assert len(lines) == 1
    
    fields = lines[0].split(',')
    assert fields[1] == "Test Client"
    assert fields[28] == "WC1P2 - Nunthorpe"
    assert fields[29] == "=4/3"  # Adjacent tier


def test_empty_dataframe():
    """Test that empty DataFrame returns empty CSV."""
    alloc_df = pd.DataFrame()
    
    csv_output = generate_sales_quotes_csv_from_optimizer_output(
        quote_number="1933",
        client_name="Test",
        development_address="Test",
        base_ref="BNG01650",
        introducer=None,
        today_date=datetime(2025, 11, 10),
        local_planning_authority="Test",
        national_character_area="Test",
        alloc_df=alloc_df,
        contract_size="small"
    )
    
    assert csv_output == ""


def test_date_formatting():
    """Test that dates are formatted as DD/MM/YYYY."""
    allocations = [{
        "bank_ref": "WC1P2",
        "bank_name": "Nunthorpe",
        "is_paired": False,
        "spatial_relation": "far",
        "spatial_multiplier_numeric": 2.0,
        "allocation_total_credits": 10.0,
        "contract_value_gbp": 10000.0,
        "habitats": []
    }]
    
    # Test various dates
    test_dates = [
        (datetime(2025, 1, 5), "05/01/2025"),
        (datetime(2025, 12, 25), "25/12/2025"),
        (datetime(2025, 11, 10), "10/11/2025"),
    ]
    
    for date_obj, expected_str in test_dates:
        csv_output = generate_sales_quotes_csv(
            quote_number="1934",
            client_name="Test",
            development_address="Test",
            base_ref="BNG01651",
            introducer=None,
            today_date=date_obj,
            local_planning_authority="Test",
            national_character_area="Test",
            allocations=allocations,
            contract_size="small"
        )
        
        fields = csv_output.split(',')
        assert fields[37] == expected_str  # Column AL: Quote Date


def test_multiple_habitats():
    """Test CSV generation with multiple habitats (up to 8)."""
    # Create 8 different habitats
    habitats = [
        {"type": f"Habitat Type {i+1}", "units_supplied": 0.5 + i*0.1, 
         "effective_units": 1.0 + i*0.2, "avg_effective_unit_price": 1000 + i*100}
        for i in range(8)
    ]
    
    allocations = [{
        "bank_ref": "WC1P2",
        "bank_name": "Nunthorpe",
        "is_paired": False,
        "spatial_relation": "far",
        "spatial_multiplier_numeric": 2.0,
        "allocation_total_credits": 10.0,
        "contract_value_gbp": 10000.0,
        "habitats": habitats
    }]
    
    csv_output = generate_sales_quotes_csv(
        quote_number="1935",
        client_name="Test Client",
        development_address="Test Address",
        base_ref="BNG01652",
        introducer=None,
        today_date=datetime(2025, 11, 10),
        local_planning_authority="Test LPA",
        national_character_area="Test NCA",
        allocations=allocations,
        contract_size="small"
    )
    
    fields = csv_output.split(',')
    
    # Check that all 8 habitats are present
    # Habitat 1: columns 47-53 (AV-BB)
    # Habitat 2: columns 54-60 (BC-BI)
    # Habitat 3: columns 61-67 (BJ-BP)
    # Habitat 4: columns 68-74 (BQ-BW)
    # Habitat 5: columns 75-81 (BX-CD)
    # Habitat 6: columns 82-88 (CE-CK)
    # Habitat 7: columns 89-95 (CL-CR)
    # Habitat 8: columns 96-102 (CS-CY)
    
    for hab_idx in range(8):
        base_idx = 47 + (hab_idx * 7)
        # Check Type (column 0)
        assert fields[base_idx] == f"Habitat Type {hab_idx + 1}"
        # Check # credits (column 1, uses units_supplied for non-paired)
        expected_units = 0.5 + hab_idx * 0.1
        assert fields[base_idx + 1] == str(expected_units)
        # Check ST (column 2) - should be blank
        assert fields[base_idx + 2] == ""
        # Check Standard Price (column 3) - should be blank
        assert fields[base_idx + 3] == ""
        # Check Quoted Price (column 4)
        expected_price = 1000 + hab_idx * 100
        assert fields[base_idx + 4] == str(expected_price)
        # Check Minimum (column 5) - should be blank
        assert fields[base_idx + 5] == ""
        # Check Price inc SM (column 6) - should be blank
        assert fields[base_idx + 6] == ""


def test_habitat_limit_8():
    """Test that only first 8 habitats are included even if more are provided."""
    # Create 10 habitats
    habitats = [
        {"type": f"Habitat {i+1}", "units_supplied": 1.0, 
         "effective_units": 2.0, "avg_effective_unit_price": 1000}
        for i in range(10)
    ]
    
    allocations = [{
        "bank_ref": "WC1P2",
        "bank_name": "Nunthorpe",
        "is_paired": False,
        "spatial_relation": "far",
        "spatial_multiplier_numeric": 2.0,
        "allocation_total_credits": 10.0,
        "contract_value_gbp": 10000.0,
        "habitats": habitats
    }]
    
    csv_output = generate_sales_quotes_csv(
        quote_number="1936",
        client_name="Test",
        development_address="Test",
        base_ref="BNG01653",
        introducer=None,
        today_date=datetime(2025, 11, 10),
        local_planning_authority="Test",
        national_character_area="Test",
        allocations=allocations,
        contract_size="small"
    )
    
    fields = csv_output.split(',')
    
    # Check that habitat 8 is present
    assert fields[96] == "Habitat 8"
    
    # Check that habitat 9 and 10 are not included (we only go to column 102)
    # All fields after column 102 should not exist
    assert len(fields) == 103  # Exactly 103 columns (A to CY)


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v"])
