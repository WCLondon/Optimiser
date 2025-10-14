"""
Test script to validate database module syntax and imports.
This does NOT test actual database operations (requires PostgreSQL).
"""

import sys
import importlib

def test_imports():
    """Test that all modules can be imported."""
    print("Testing imports...")
    
    try:
        import db
        print("✓ db module imported successfully")
    except ImportError as e:
        print(f"✗ Failed to import db: {e}")
        return False
    
    try:
        import database
        print("✓ database module imported successfully")
    except ImportError as e:
        print(f"✗ Failed to import database: {e}")
        return False
    
    return True

def test_class_structure():
    """Test that classes have expected methods."""
    print("\nTesting class structure...")
    
    try:
        from database import SubmissionsDB
        
        # Check that SubmissionsDB has all expected methods
        expected_methods = [
            '__init__',
            '_get_connection',
            '_init_database',
            'close',
            'store_submission',
            'get_all_submissions',
            'get_submission_by_id',
            'get_allocations_for_submission',
            'filter_submissions',
            'export_to_csv',
            'get_summary_stats',
            'add_introducer',
            'get_all_introducers',
            'get_introducer_by_name',
            'update_introducer',
            'delete_introducer',
            'db_healthcheck'
        ]
        
        for method in expected_methods:
            if not hasattr(SubmissionsDB, method):
                print(f"✗ Missing method: {method}")
                return False
            print(f"✓ Method exists: {method}")
        
        return True
    except Exception as e:
        print(f"✗ Error testing class structure: {e}")
        return False

def test_db_connection_class():
    """Test DatabaseConnection class structure."""
    print("\nTesting DatabaseConnection class...")
    
    try:
        from db import DatabaseConnection
        
        expected_methods = [
            'get_engine',
            'close',
            'execute_with_retry',
            'db_healthcheck'
        ]
        
        for method in expected_methods:
            if not hasattr(DatabaseConnection, method):
                print(f"✗ Missing method: {method}")
                return False
            print(f"✓ Method exists: {method}")
        
        return True
    except Exception as e:
        print(f"✗ Error testing DatabaseConnection: {e}")
        return False

def test_method_signatures():
    """Test that method signatures are compatible."""
    print("\nTesting method signatures...")
    
    try:
        from database import SubmissionsDB
        import inspect
        
        # Check store_submission signature
        sig = inspect.signature(SubmissionsDB.store_submission)
        params = list(sig.parameters.keys())
        
        expected_params = [
            'self', 'client_name', 'reference_number', 'site_location',
            'target_lpa', 'target_nca', 'target_lat', 'target_lon',
            'lpa_neighbors', 'nca_neighbors', 'demand_df', 'allocation_df',
            'contract_size', 'total_cost', 'admin_fee',
            'manual_hedgerow_rows', 'manual_watercourse_rows',
            'username', 'promoter_name', 'promoter_discount_type', 'promoter_discount_value'
        ]
        
        for param in expected_params:
            if param not in params:
                print(f"✗ Missing parameter in store_submission: {param}")
                return False
        
        print("✓ store_submission signature is compatible")
        
        # Check filter_submissions signature
        sig = inspect.signature(SubmissionsDB.filter_submissions)
        params = list(sig.parameters.keys())
        
        expected_params = [
            'self', 'start_date', 'end_date', 'client_name',
            'lpa', 'nca', 'reference_number'
        ]
        
        for param in expected_params:
            if param not in params:
                print(f"✗ Missing parameter in filter_submissions: {param}")
                return False
        
        print("✓ filter_submissions signature is compatible")
        
        return True
    except Exception as e:
        print(f"✗ Error testing method signatures: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Run all tests."""
    print("=" * 60)
    print("Database Module Validation Test")
    print("=" * 60)
    
    tests = [
        ("Import Test", test_imports),
        ("Class Structure Test", test_class_structure),
        ("DatabaseConnection Test", test_db_connection_class),
        ("Method Signature Test", test_method_signatures)
    ]
    
    results = []
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"\n✗ {test_name} failed with exception: {e}")
            import traceback
            traceback.print_exc()
            results.append((test_name, False))
    
    print("\n" + "=" * 60)
    print("Test Summary")
    print("=" * 60)
    
    for test_name, result in results:
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"{status}: {test_name}")
    
    all_passed = all(result for _, result in results)
    
    print("\n" + "=" * 60)
    if all_passed:
        print("✓ All tests passed!")
        print("=" * 60)
        print("\nNote: These tests only validate code structure and imports.")
        print("To test actual database operations, you need:")
        print("1. A running PostgreSQL instance")
        print("2. Database credentials in .streamlit/secrets.toml")
        print("3. Run the application: streamlit run app.py")
        return 0
    else:
        print("✗ Some tests failed!")
        print("=" * 60)
        return 1

if __name__ == "__main__":
    sys.exit(main())
