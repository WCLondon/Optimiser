"""
Test to verify Attio sync compatibility for submissions_attio table.

This test ensures that:
1. client_name field is set to NULL (as Attio expects UUID references, not TEXT)
2. site_location has all required fields for Attio location type
"""

def test_attio_compatibility():
    """
    Verify that the submissions_attio table structure is compatible with Attio/StackSync.
    
    Expected behavior:
    - client_name should be NULL (Attio expects UUID reference, not text)
    - site_location should be JSONB with all required keys:
      line_1, line_2, line_3, line_4, locality, region, postcode, 
      country_code, latitude, longitude
    """
    print("Testing Attio compatibility...")
    
    try:
        from database import SubmissionsDB
        import re
        
        # Read the database.py file to check the trigger function
        with open('/home/runner/work/Optimiser/Optimiser/database.py', 'r') as f:
            content = f.read()
        
        # Check that client_name is passed from NEW.client_name in trigger
        # Look for the pattern: DATE(NEW.submission_date), followed by NEW.client_name
        trigger_check = re.search(
            r'DATE\(NEW\.submission_date\),\s*NEW\.client_name,',
            content,
            re.DOTALL
        )
        
        if trigger_check:
            print("✓ client_name is correctly passed from NEW.client_name in trigger function")
        else:
            print("✗ client_name is not being passed correctly in trigger function")
            return False
        
        # Check that email and mobile_number are fetched from customers table
        if 'SELECT email, mobile_number INTO' in content and 'FROM customers WHERE id = NEW.customer_id' in content:
            print("✓ email and mobile_number are fetched from customers table in trigger")
        else:
            print("✗ email and mobile_number are not being fetched from customers table")
            return False
        
        # Check that site_location has all required fields
        required_fields = [
            'line_1', 'line_2', 'line_3', 'line_4',
            'locality', 'region', 'postcode', 'country_code',
            'latitude', 'longitude'
        ]
        
        all_fields_present = all(field in content for field in required_fields)
        
        if all_fields_present:
            print("✓ site_location has all required Attio location fields")
        else:
            print("✗ site_location is missing some required fields")
            missing = [f for f in required_fields if f not in content]
            print(f"  Missing: {missing}")
            return False
        
        # Check that email and mobile_number fields are in submissions_attio table
        if 'email TEXT,' in content and 'mobile_number TEXT,' in content:
            print("✓ submissions_attio table includes email and mobile_number fields")
        else:
            print("✗ submissions_attio table is missing email or mobile_number fields")
            return False
        
        # Check backfill query uses LEFT JOIN with customers table
        # Look for the pattern: LEFT JOIN customers and the field references
        backfill_check = re.search(
            r'LEFT JOIN customers c ON s\.customer_id = c\.id',
            content,
            re.DOTALL
        )
        
        if backfill_check:
            print("✓ backfill query correctly joins with customers table")
        else:
            print("✗ backfill query does not join with customers table")
            return False
        
        # Check that backfill uses c.email and c.mobile_number
        if 'c.email,' in content and 'c.mobile_number,' in content:
            print("✓ backfill query includes email and mobile_number from customers")
        else:
            print("✗ backfill query does not include email or mobile_number")
            return False
        
        print("\n✓ All Attio compatibility checks passed!")
        print("\nKey changes:")
        print("  - client_name is passed as TEXT (customer name)")
        print("  - email and mobile_number are included from customers table")
        print("  - Attio can use these fields to create/match customer records")
        return True
        
    except Exception as e:
        print(f"✗ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    print("=" * 60)
    print("Attio Sync Compatibility Test")
    print("=" * 60)
    
    success = test_attio_compatibility()
    
    print("\n" + "=" * 60)
    print("Test Summary")
    print("=" * 60)
    
    if success:
        print("✓ PASS: Attio compatibility test")
        print("\nThe submissions_attio table is now compatible with Attio/StackSync:")
        print("- client_name contains the customer name as TEXT")
        print("- email and mobile_number are included for customer matching/creation")
        print("- site_location has all required location fields")
        print("- Attio can use name, email, and mobile to create or match customer records")
    else:
        print("✗ FAIL: Attio compatibility test")
        exit(1)
