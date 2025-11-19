"""
Verification test for the exact issue reported.

This test reproduces the exact scenario from the issue to verify the fix.
"""

import pandas as pd
from datetime import datetime
from sales_quotes_csv import generate_sales_quotes_csv_from_optimizer_output
import csv
import io


def test_issue_verification():
    """
    Reproduce the exact issue scenario:
    - Northants Grassland - Other neutral grassland
    - Local tier
    - 0.20885 units
    - Address: "The Old Rectory, Rectory Lane, Great Rissington, Cheltenham, Gloucestershire GL54 2LL"
    
    Expected fixes:
    1. Spatial multiplier should be "1" (not "=4/3")
    2. Address should not be wrapped in quotes
    """
    
    # Create allocation matching the issue
    alloc_df = pd.DataFrame([{
        'BANK_KEY': 'Northants',
        'bank_name': 'Northants',
        'supply_habitat': 'Grassland - Other neutral grassland',
        'tier': 'local',  # This was the problem - local tier
        'allocation_type': 'normal',
        'units_supplied': 0.20885,
        'effective_units': 0.20885,
        'cost': 4385.85,
        'avg_effective_unit_price': 21000.0
    }])
    
    # Generate CSV
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
    
    # Parse CSV
    reader = csv.reader(io.StringIO(csv_output))
    fields = list(reader)[0]
    
    print("Issue Verification Test")
    print("=" * 60)
    print()
    print("Original Issue:")
    print("  - Tier: local")
    print("  - Expected spatial multiplier: 1")
    print("  - Actual was showing: =4/3 (WRONG)")
    print()
    print("  - Address had commas")
    print("  - Expected: No quotation marks")
    print("  - Actual was: Wrapped in quotes (WRONG)")
    print()
    print("Current Results After Fix:")
    print("-" * 60)
    
    # Verify spatial multiplier
    spatial_multiplier = fields[29]  # Column AD
    print(f"  Spatial Multiplier: {spatial_multiplier}")
    assert spatial_multiplier == "1", f"Expected '1', got {repr(spatial_multiplier)}"
    print("  ✓ Correct! (was =4/3 before)")
    print()
    
    # Verify address is not quoted
    address = fields[2]  # Column C
    expected_address = 'The Old Rectory; Rectory Lane; Great Rissington; Cheltenham; Gloucestershire GL54 2LL'
    print(f"  Address: {address}")
    assert address == expected_address, f"Expected {repr(expected_address)}, got {repr(address)}"
    print("  ✓ Correct! (commas replaced with semicolons, no quotes)")
    print()
    
    # Verify raw CSV doesn't have quotes around address
    assert f'"{expected_address}"' not in csv_output, "Address should not be wrapped in quotes in raw CSV"
    print("  Raw CSV verification:")
    print("  ✓ No quotation marks around address field")
    print()
    
    print("=" * 60)
    print("✅ ISSUE RESOLVED - Both problems fixed!")
    print("=" * 60)


if __name__ == "__main__":
    test_issue_verification()
