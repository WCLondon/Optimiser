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
        
        # Check that client_name is set to NULL in the trigger
        # Look for the pattern: DATE(NEW.submission_date), followed by NULL, followed by NEW.reference_number
        trigger_check = re.search(
            r'DATE\(NEW\.submission_date\),\s*NULL,\s*NEW\.reference_number',
            content,
            re.DOTALL
        )
        
        if trigger_check:
            print("✓ client_name is correctly set to NULL in trigger function")
        else:
            print("✗ client_name is not NULL in trigger function")
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
        
        # Check backfill query also uses NULL
        # Look for the pattern: DATE(submission_date), followed by NULL, followed by reference_number
        backfill_check = re.search(
            r'DATE\(submission_date\),\s*NULL,\s*reference_number',
            content,
            re.DOTALL
        )
        
        if backfill_check:
            print("✓ client_name is correctly set to NULL in backfill query")
        else:
            print("✗ client_name is not NULL in backfill query")
            return False
        
        print("\n✓ All Attio compatibility checks passed!")
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
        print("- client_name is NULL (Attio can map this to a customer record)")
        print("- site_location has all required location fields")
    else:
        print("✗ FAIL: Attio compatibility test")
        exit(1)
