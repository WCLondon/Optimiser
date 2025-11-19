"""
Test to verify tier and address fixes in CSV generation.
"""

import pandas as pd
from datetime import datetime
from sales_quotes_csv import generate_sales_quotes_csv_from_optimizer_output
import csv
import io


def test_local_tier_spatial_multiplier():
    """Test that 'local' tier produces spatial multiplier of '1' in CSV."""
    alloc_df = pd.DataFrame([{
        'BANK_KEY': 'TestBank',
        'bank_name': 'TestBank',
        'supply_habitat': 'Grassland',
        'tier': 'local',
        'allocation_type': 'normal',
        'units_supplied': 10.0,
        'effective_units': 10.0,
        'cost': 5000.0,
        'avg_effective_unit_price': 500.0
    }])
    
    csv_output = generate_sales_quotes_csv_from_optimizer_output(
        quote_number='TEST001',
        client_name='Test Client',
        development_address='Test Address',
        base_ref='TEST001',
        introducer='Direct',
        today_date=datetime(2025, 11, 19),
        local_planning_authority='Test LPA',
        national_character_area='Test NCA',
        alloc_df=alloc_df,
        contract_size='small'
    )
    
    reader = csv.reader(io.StringIO(csv_output))
    fields = list(reader)[0]
    
    # Field 29 is the spatial multiplier (Column AD)
    assert fields[29] == '1', f"Expected '1' for local tier, got {repr(fields[29])}"
    print("✓ Local tier produces spatial multiplier '1'")


def test_adjacent_tier_spatial_multiplier():
    """Test that 'adjacent' tier produces spatial multiplier of '=4/3' in CSV."""
    alloc_df = pd.DataFrame([{
        'BANK_KEY': 'TestBank',
        'bank_name': 'TestBank',
        'supply_habitat': 'Grassland',
        'tier': 'adjacent',
        'allocation_type': 'normal',
        'units_supplied': 10.0,
        'effective_units': 13.33,
        'cost': 6665.0,
        'avg_effective_unit_price': 500.0
    }])
    
    csv_output = generate_sales_quotes_csv_from_optimizer_output(
        quote_number='TEST002',
        client_name='Test Client',
        development_address='Test Address',
        base_ref='TEST002',
        introducer='Direct',
        today_date=datetime(2025, 11, 19),
        local_planning_authority='Test LPA',
        national_character_area='Test NCA',
        alloc_df=alloc_df,
        contract_size='small'
    )
    
    reader = csv.reader(io.StringIO(csv_output))
    fields = list(reader)[0]
    
    assert fields[29] == '=4/3', f"Expected '=4/3' for adjacent tier, got {repr(fields[29])}"
    print("✓ Adjacent tier produces spatial multiplier '=4/3'")


def test_far_tier_spatial_multiplier():
    """Test that 'far' tier produces spatial multiplier of '=2/1' in CSV."""
    alloc_df = pd.DataFrame([{
        'BANK_KEY': 'TestBank',
        'bank_name': 'TestBank',
        'supply_habitat': 'Grassland',
        'tier': 'far',
        'allocation_type': 'normal',
        'units_supplied': 10.0,
        'effective_units': 20.0,
        'cost': 10000.0,
        'avg_effective_unit_price': 500.0
    }])
    
    csv_output = generate_sales_quotes_csv_from_optimizer_output(
        quote_number='TEST003',
        client_name='Test Client',
        development_address='Test Address',
        base_ref='TEST003',
        introducer='Direct',
        today_date=datetime(2025, 11, 19),
        local_planning_authority='Test LPA',
        national_character_area='Test NCA',
        alloc_df=alloc_df,
        contract_size='small'
    )
    
    reader = csv.reader(io.StringIO(csv_output))
    fields = list(reader)[0]
    
    assert fields[29] == '=2/1', f"Expected '=2/1' for far tier, got {repr(fields[29])}"
    print("✓ Far tier produces spatial multiplier '=2/1'")


def test_address_without_quotes():
    """Test that address with commas doesn't get wrapped in quotes."""
    alloc_df = pd.DataFrame([{
        'BANK_KEY': 'TestBank',
        'bank_name': 'TestBank',
        'supply_habitat': 'Grassland',
        'tier': 'local',
        'allocation_type': 'normal',
        'units_supplied': 10.0,
        'effective_units': 10.0,
        'cost': 5000.0,
        'avg_effective_unit_price': 500.0
    }])
    
    test_address = 'The Old Rectory, Rectory Lane, Great Rissington, Cheltenham, Gloucestershire GL54 2LL'
    
    csv_output = generate_sales_quotes_csv_from_optimizer_output(
        quote_number='TEST004',
        client_name='Test Client',
        development_address=test_address,
        base_ref='TEST004',
        introducer='Direct',
        today_date=datetime(2025, 11, 19),
        local_planning_authority='Test LPA',
        national_character_area='Test NCA',
        alloc_df=alloc_df,
        contract_size='small'
    )
    
    # Check raw CSV doesn't have quotes around address
    # The address should have commas replaced with semicolons
    expected_address = test_address.replace(',', ';')
    assert f'"{expected_address}"' not in csv_output, "Address should not be wrapped in quotes"
    assert expected_address in csv_output, f"Address should be in CSV: {expected_address}"
    
    # Also verify via CSV reader
    reader = csv.reader(io.StringIO(csv_output))
    fields = list(reader)[0]
    
    # Field 2 is the address (Column C)
    assert fields[2] == expected_address, f"Expected {repr(expected_address)}, got {repr(fields[2])}"
    print("✓ Address field does not contain quotes")


def test_real_world_example():
    """Test with the actual example from the issue."""
    alloc_df = pd.DataFrame([{
        'BANK_KEY': 'Northants',
        'bank_name': 'Northants',
        'supply_habitat': 'Grassland - Other neutral grassland',
        'tier': 'local',
        'allocation_type': 'normal',
        'units_supplied': 0.20885,
        'effective_units': 0.20885,
        'cost': 4385.85,
        'avg_effective_unit_price': 21000.0
    }])
    
    csv_output = generate_sales_quotes_csv_from_optimizer_output(
        quote_number='BNG-A-02033',
        client_name='Rob Freeman',
        development_address='The Old Rectory, Rectory Lane, Great Rissington, Cheltenham, Gloucestershire GL54 2LL',
        base_ref='BNG-A-02033',
        introducer='Arbtech',
        today_date=datetime(2025, 11, 19),
        local_planning_authority='Cotswold',
        national_character_area='Cotswolds',
        alloc_df=alloc_df,
        contract_size='small'
    )
    
    reader = csv.reader(io.StringIO(csv_output))
    fields = list(reader)[0]
    
    # Verify spatial multiplier is '1' for local tier
    assert fields[29] == '1', f"Expected '1' for local tier, got {repr(fields[29])}"
    
    # Verify address doesn't have quotes
    expected_address = 'The Old Rectory; Rectory Lane; Great Rissington; Cheltenham; Gloucestershire GL54 2LL'
    assert fields[2] == expected_address, f"Expected {repr(expected_address)}, got {repr(fields[2])}"
    
    print("✓ Real-world example from issue works correctly")


if __name__ == "__main__":
    print("Running CSV tier and address fix tests...\n")
    
    test_local_tier_spatial_multiplier()
    test_adjacent_tier_spatial_multiplier()
    test_far_tier_spatial_multiplier()
    test_address_without_quotes()
    test_real_world_example()
    
    print("\n✅ All tests passed!")
