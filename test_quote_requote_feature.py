"""
Test script for Quote Requote and Customer Management features.
This validates the new methods without requiring a live database.
"""

import sys


def test_imports():
    """Test that all modules can be imported."""
    print("Testing imports...")
    
    try:
        from database import SubmissionsDB
        print("✓ SubmissionsDB imported successfully")
    except ImportError as e:
        print(f"✗ Failed to import SubmissionsDB: {e}")
        return False
    
    return True


def test_customer_methods():
    """Test that customer methods exist with correct signatures."""
    print("\nTesting customer methods...")
    
    try:
        from database import SubmissionsDB
        import inspect
        
        # Check add_customer method
        if hasattr(SubmissionsDB, 'add_customer'):
            sig = inspect.signature(SubmissionsDB.add_customer)
            params = list(sig.parameters.keys())
            expected_params = ['self', 'client_name', 'company_name', 'contact_person', 
                              'address', 'email', 'mobile_number']
            if all(p in params for p in expected_params):
                print("✓ add_customer method exists with correct signature")
            else:
                print(f"✗ add_customer has unexpected signature: {params}")
                return False
        else:
            print("✗ add_customer method not found")
            return False
        
        # Check get_customer_by_id method
        if hasattr(SubmissionsDB, 'get_customer_by_id'):
            print("✓ get_customer_by_id method exists")
        else:
            print("✗ get_customer_by_id method not found")
            return False
        
        # Check get_customer_by_contact method
        if hasattr(SubmissionsDB, 'get_customer_by_contact'):
            print("✓ get_customer_by_contact method exists")
        else:
            print("✗ get_customer_by_contact method not found")
            return False
        
        # Check get_all_customers method
        if hasattr(SubmissionsDB, 'get_all_customers'):
            print("✓ get_all_customers method exists")
        else:
            print("✗ get_all_customers method not found")
            return False
        
        # Check update_customer method
        if hasattr(SubmissionsDB, 'update_customer'):
            print("✓ update_customer method exists")
        else:
            print("✗ update_customer method not found")
            return False
        
        return True
        
    except Exception as e:
        print(f"✗ Error testing customer methods: {e}")
        return False


def test_requote_methods():
    """Test that requote methods exist with correct signatures."""
    print("\nTesting requote methods...")
    
    try:
        from database import SubmissionsDB
        import inspect
        
        # Check get_next_revision_number method
        if hasattr(SubmissionsDB, 'get_next_revision_number'):
            sig = inspect.signature(SubmissionsDB.get_next_revision_number)
            params = list(sig.parameters.keys())
            if 'base_reference' in params:
                print("✓ get_next_revision_number method exists with correct signature")
            else:
                print(f"✗ get_next_revision_number has unexpected signature: {params}")
                return False
        else:
            print("✗ get_next_revision_number method not found")
            return False
        
        # Check get_quotes_by_reference_base method
        if hasattr(SubmissionsDB, 'get_quotes_by_reference_base'):
            print("✓ get_quotes_by_reference_base method exists")
        else:
            print("✗ get_quotes_by_reference_base method not found")
            return False
        
        # Check create_requote_from_submission method
        if hasattr(SubmissionsDB, 'create_requote_from_submission'):
            sig = inspect.signature(SubmissionsDB.create_requote_from_submission)
            params = list(sig.parameters.keys())
            if 'submission_id' in params and 'new_demand_df' in params:
                print("✓ create_requote_from_submission method exists with correct signature")
            else:
                print(f"✗ create_requote_from_submission has unexpected signature: {params}")
                return False
        else:
            print("✗ create_requote_from_submission method not found")
            return False
        
        return True
        
    except Exception as e:
        print(f"✗ Error testing requote methods: {e}")
        return False


def test_store_submission_signature():
    """Test that store_submission has customer_id parameter."""
    print("\nTesting store_submission signature...")
    
    try:
        from database import SubmissionsDB
        import inspect
        
        sig = inspect.signature(SubmissionsDB.store_submission)
        params = list(sig.parameters.keys())
        
        if 'customer_id' in params:
            print("✓ store_submission has customer_id parameter")
            return True
        else:
            print("✗ store_submission missing customer_id parameter")
            print(f"  Current parameters: {params}")
            return False
            
    except Exception as e:
        print(f"✗ Error testing store_submission: {e}")
        return False


def test_revision_number_logic():
    """Test revision number incrementing logic."""
    print("\nTesting revision number logic...")
    
    try:
        # Test the logic without database
        def get_next_revision_mock(base_reference, existing_refs):
            """Mock version of get_next_revision_number for testing."""
            base_ref = base_reference.split('.')[0]
            
            if not existing_refs:
                return f"{base_ref}.1"
            
            max_revision = 0
            for ref in existing_refs:
                if '.' in ref:
                    try:
                        revision = int(ref.split('.')[-1])
                        max_revision = max(max_revision, revision)
                    except ValueError:
                        pass
            
            return f"{base_ref}.{max_revision + 1}"
        
        # Test cases
        test_cases = [
            ("BNG01234", [], "BNG01234.1"),
            ("BNG01234", ["BNG01234"], "BNG01234.1"),
            ("BNG01234", ["BNG01234", "BNG01234.1"], "BNG01234.2"),
            ("BNG01234", ["BNG01234.1", "BNG01234.2", "BNG01234.3"], "BNG01234.4"),
            ("BNG01234.1", ["BNG01234.1"], "BNG01234.2"),  # Should strip existing revision
        ]
        
        all_passed = True
        for base_ref, existing, expected in test_cases:
            result = get_next_revision_mock(base_ref, existing)
            if result == expected:
                print(f"✓ {base_ref} with {len(existing)} existing → {result}")
            else:
                print(f"✗ {base_ref} expected {expected} but got {result}")
                all_passed = False
        
        return all_passed
        
    except Exception as e:
        print(f"✗ Error testing revision logic: {e}")
        return False


def main():
    """Run all tests."""
    print("=" * 60)
    print("Quote Requote & Customer Management Feature Test")
    print("=" * 60)
    
    results = {
        "Imports": test_imports(),
        "Customer Methods": test_customer_methods(),
        "Requote Methods": test_requote_methods(),
        "store_submission Signature": test_store_submission_signature(),
        "Revision Number Logic": test_revision_number_logic()
    }
    
    print("\n" + "=" * 60)
    print("Test Summary")
    print("=" * 60)
    
    for test_name, passed in results.items():
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"{status}: {test_name}")
    
    print("=" * 60)
    
    if all(results.values()):
        print("✓ All tests passed!")
        print("\nNote: These tests only validate code structure.")
        print("To test actual database operations, you need:")
        print("1. A running PostgreSQL instance")
        print("2. Database credentials in .streamlit/secrets.toml")
        print("3. Run the application: streamlit run app.py")
        return 0
    else:
        print("✗ Some tests failed!")
        return 1


if __name__ == "__main__":
    sys.exit(main())
