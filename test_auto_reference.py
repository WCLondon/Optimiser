"""
Test auto-generated BNG reference numbers
"""

import sys
from unittest.mock import MagicMock, patch

# Mock streamlit
sys.modules['streamlit'] = MagicMock()

def test_reference_number_generation():
    """Test that reference numbers are generated correctly"""
    from database import SubmissionsDB
    
    # Mock the database connection and query results
    with patch('database.DatabaseConnection.get_engine') as mock_engine:
        mock_conn = MagicMock()
        mock_result = MagicMock()
        
        # Test case 1: No existing references - should start at BNG-A-02025
        mock_result.fetchone.return_value = None
        mock_conn.execute.return_value = mock_result
        mock_conn.__enter__ = MagicMock(return_value=mock_conn)
        mock_conn.__exit__ = MagicMock(return_value=False)
        mock_engine.return_value.connect.return_value = mock_conn
        
        db = SubmissionsDB()
        next_ref = db.get_next_bng_reference("BNG-A-")
        
        assert next_ref == "BNG-A-02025", f"Expected BNG-A-02025, got {next_ref}"
        print("✓ Test passed: No existing references returns BNG-A-02025")
        
        # Test case 2: Latest reference is BNG-A-02025 - should return BNG-A-02026
        mock_result.fetchone.return_value = ("BNG-A-02025",)
        
        next_ref = db.get_next_bng_reference("BNG-A-")
        
        assert next_ref == "BNG-A-02026", f"Expected BNG-A-02026, got {next_ref}"
        print("✓ Test passed: BNG-A-02025 increments to BNG-A-02026")
        
        # Test case 3: Latest reference is BNG-A-02999 - should return BNG-A-03000
        mock_result.fetchone.return_value = ("BNG-A-02999",)
        
        next_ref = db.get_next_bng_reference("BNG-A-")
        
        assert next_ref == "BNG-A-03000", f"Expected BNG-A-03000, got {next_ref}"
        print("✓ Test passed: BNG-A-02999 increments to BNG-A-03000")
        
        # Test case 4: Reference with revision suffix - should ignore .1 and increment base
        mock_result.fetchone.return_value = ("BNG-A-02050.1",)
        
        next_ref = db.get_next_bng_reference("BNG-A-")
        
        assert next_ref == "BNG-A-02051", f"Expected BNG-A-02051, got {next_ref}"
        print("✓ Test passed: BNG-A-02050.1 increments to BNG-A-02051 (ignoring revision)")


def test_excel_formula_row_numbers():
    """Test that Excel formulas use correct row numbers"""
    from sales_quotes_csv import generate_sales_quotes_csv
    from datetime import datetime
    
    allocations = [
        {
            "bank_ref": "WC1P2",
            "bank_name": "Nunthorpe",
            "is_paired": False,
            "spatial_relation": "adjacent",
            "spatial_multiplier_numeric": 4.0/3.0,
            "allocation_total_credits": 10.0,
            "contract_value_gbp": 10000.0,
            "habitats": [{"type": "Grassland", "units_supplied": 10.0, "effective_units": 13.33, "avg_effective_unit_price": 1000.0}]
        },
        {
            "bank_ref": "WC1P5",
            "bank_name": "Bedford",
            "is_paired": False,
            "spatial_relation": "far",
            "spatial_multiplier_numeric": 2.0,
            "allocation_total_credits": 5.0,
            "contract_value_gbp": 5000.0,
            "habitats": [{"type": "Woodland", "units_supplied": 5.0, "effective_units": 10.0, "avg_effective_unit_price": 500.0}]
        }
    ]
    
    csv_output = generate_sales_quotes_csv(
        quote_number="TEST001",
        client_name="Test Client",
        development_address="Test Address",
        base_ref="BNG-A-02025",
        introducer="Test",
        today_date=datetime(2025, 11, 19),
        local_planning_authority="Test LPA",
        national_character_area="Test NCA",
        allocations=allocations,
        contract_size="small"
    )
    
    # Split CSV into lines
    lines = csv_output.split('\n')
    
    # Parse first row
    import csv
    import io
    reader = csv.reader(io.StringIO(lines[0]))
    row1_fields = list(reader)[0]
    
    # Column 39 (index 39) should have formula =AL1+AM1 for first row
    assert row1_fields[39] == "=AL1+AM1", f"Expected =AL1+AM1 in row 1, got {row1_fields[39]}"
    print("✓ Test passed: Row 1 formula is =AL1+AM1")
    
    # Parse second row
    reader = csv.reader(io.StringIO(lines[1]))
    row2_fields = list(reader)[0]
    
    # Column 39 should have formula =AL2+AM2 for second row
    assert row2_fields[39] == "=AL2+AM2", f"Expected =AL2+AM2 in row 2, got {row2_fields[39]}"
    print("✓ Test passed: Row 2 formula is =AL2+AM2")


if __name__ == '__main__':
    print("Running auto-reference number tests...")
    print()
    
    test_reference_number_generation()
    print()
    test_excel_formula_row_numbers()
    
    print()
    print("=" * 60)
    print("All tests passed! ✓")
    print("=" * 60)
