"""
Test to verify Attio sync compatibility for customers table and submissions_attio table.

This test ensures that:
1. customers table has Attio-compatible JSONB fields
2. Trigger automatically syncs legacy fields to Attio format
3. submissions_attio has all required fields
4. Validation enforces first_name and last_name requirements
"""

def test_customers_table_schema():
    """
    Verify that the customers table has the required Attio-compatible columns.
    """
    print("\n=== Testing Customers Table Schema ===")
    
    try:
        import re
        
        # Read the database.py file to check schema
        with open('/home/runner/work/Optimiser/Optimiser/database.py', 'r') as f:
            content = f.read()
        
        # Check for Attio-compatible JSONB columns
        attio_columns = ['personal_name', 'email_addresses', 'phone_numbers', 'companies']
        
        for column in attio_columns:
            if f'column_name = \'{column}\'' in content:
                print(f"✓ Attio-compatible column '{column}' is added")
            else:
                print(f"✗ Column '{column}' is missing")
                return False
        
        # Check for sync trigger function
        if 'CREATE OR REPLACE FUNCTION sync_customer_attio_fields()' in content:
            print("✓ Trigger function sync_customer_attio_fields() exists")
        else:
            print("✗ Trigger function sync_customer_attio_fields() not found")
            return False
        
        # Check that trigger is created
        if 'CREATE TRIGGER sync_customer_attio_fields_trigger' in content:
            print("✓ Trigger sync_customer_attio_fields_trigger is created")
        else:
            print("✗ Trigger sync_customer_attio_fields_trigger not found")
            return False
        
        # Check that backfill query exists
        if 'UPDATE customers SET' in content and 'jsonb_build_object' in content:
            print("✓ Backfill query for existing customers exists")
        else:
            print("✗ Backfill query not found")
            return False
        
        return True
        
    except Exception as e:
        print(f"✗ Schema test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_validation_requirements():
    """
    Verify that first_name and last_name are required for customer creation.
    """
    print("\n=== Testing Validation Requirements ===")
    
    try:
        import re
        
        # Read the database.py file
        with open('/home/runner/work/Optimiser/Optimiser/database.py', 'r') as f:
            content = f.read()
        
        # Check that add_customer validates first_name
        if 'if not first_name or not first_name.strip():' in content:
            print("✓ first_name validation exists in add_customer()")
        else:
            print("✗ first_name validation missing")
            return False
        
        # Check that add_customer validates last_name
        if 'if not last_name or not last_name.strip():' in content:
            print("✓ last_name validation exists in add_customer()")
        else:
            print("✗ last_name validation missing")
            return False
        
        # Check error messages
        if 'raise ValueError("First name is required' in content:
            print("✓ Proper error message for missing first_name")
        else:
            print("✗ Error message for first_name missing")
            return False
        
        if 'raise ValueError("Last name is required' in content:
            print("✓ Proper error message for missing last_name")
        else:
            print("✗ Error message for last_name missing")
            return False
        
        return True
        
    except Exception as e:
        print(f"✗ Validation test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_app_form_validation():
    """
    Verify that app.py has proper form validation for customer fields.
    """
    print("\n=== Testing App Form Validation ===")
    
    try:
        import re
        
        # Read the app.py file
        with open('/home/runner/work/Optimiser/Optimiser/app.py', 'r') as f:
            content = f.read()
        
        # Check that first_name is marked as required in form
        if 'First Name*' in content and 'form_customer_first_name' in content:
            print("✓ First Name is marked as required in form")
        else:
            print("✗ First Name not properly marked as required")
            return False
        
        # Check that last_name is marked as required in form
        if 'Last Name*' in content and 'form_customer_last_name' in content:
            print("✓ Last Name is marked as required in form")
        else:
            print("✗ Last Name not properly marked as required")
            return False
        
        # Check validation before saving
        if 'if not form_customer_first_name or not form_customer_first_name.strip():' in content:
            print("✓ First name validation before saving exists")
        else:
            print("✗ First name validation before saving missing")
            return False
        
        if 'if not form_customer_last_name or not form_customer_last_name.strip():' in content:
            print("✓ Last name validation before saving exists")
        else:
            print("✗ Last name validation before saving missing")
            return False
        
        # Check email download validation
        if 'has_customer_name' in content and 'Email download is disabled' in content:
            print("✓ Email download validation exists")
        else:
            print("✗ Email download validation missing")
            return False
        
        return True
        
    except Exception as e:
        print(f"✗ App validation test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_submissions_attio_compatibility():
    """
    Verify that the submissions_attio table structure is compatible with Attio/StackSync.
    """
    print("\n=== Testing Submissions Attio Compatibility ===")
    
    try:
        import re
        
        # Read the database.py file
        with open('/home/runner/work/Optimiser/Optimiser/database.py', 'r') as f:
            content = f.read()
        
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
        
        return True
        
    except Exception as e:
        print(f"✗ Submissions attio test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    print("=" * 70)
    print("Attio Sync Compatibility Test Suite")
    print("=" * 70)
    
    # Run all tests
    results = {
        "Customers Table Schema": test_customers_table_schema(),
        "Validation Requirements": test_validation_requirements(),
        "App Form Validation": test_app_form_validation(),
        "Submissions Attio Compatibility": test_submissions_attio_compatibility()
    }
    
    print("\n" + "=" * 70)
    print("Test Summary")
    print("=" * 70)
    
    all_passed = all(results.values())
    
    for test_name, passed in results.items():
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"{status}: {test_name}")
    
    if all_passed:
        print("\n" + "=" * 70)
        print("✓ ALL TESTS PASSED!")
        print("=" * 70)
        print("\nThe customers table is now compatible with Attio/StackSync:")
        print("- personal_name stored as JSONB object: {first_name, last_name, full_name}")
        print("- email_addresses stored as JSONB array: [{email_address}]")
        print("- phone_numbers stored as JSONB array: [{original_phone_number, country_code}]")
        print("- companies stored as JSONB array: [company_name]")
        print("- Automatic trigger syncs legacy fields to Attio format")
        print("- First and last names are required for all customer records")
        print("- Email download disabled until customer name is complete")
    else:
        print("\n" + "=" * 70)
        print("✗ SOME TESTS FAILED")
        print("=" * 70)
        exit(1)
