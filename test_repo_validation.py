"""
Test script to validate repo module syntax and imports.
This does NOT test actual database operations (requires PostgreSQL).
"""

import sys

def test_imports():
    """Test that repo module can be imported."""
    print("Testing imports...")
    
    try:
        import repo
        print("✓ repo module imported successfully")
    except ImportError as e:
        print(f"✗ Failed to import repo: {e}")
        return False
    
    return True

def test_function_structure():
    """Test that repo module has expected functions."""
    print("\nTesting function structure...")
    
    try:
        import repo
        
        # Check that repo has all expected functions
        expected_functions = [
            'get_db_engine',
            'fetch_banks',
            'fetch_pricing',
            'fetch_habitat_catalog',
            'fetch_stock',
            'fetch_distinctiveness_levels',
            'fetch_srm',
            'fetch_trading_rules',
            'fetch_all_reference_tables',
            'check_required_tables_not_empty',
            'validate_reference_tables'
        ]
        
        for func_name in expected_functions:
            if not hasattr(repo, func_name):
                print(f"✗ Missing function: {func_name}")
                return False
            print(f"✓ Function exists: {func_name}")
        
        return True
    except Exception as e:
        print(f"✗ Error testing function structure: {e}")
        return False

def test_function_signatures():
    """Test that function signatures are correct."""
    print("\nTesting function signatures...")
    
    try:
        import repo
        import inspect
        
        # Check fetch_all_reference_tables returns dict
        sig = inspect.signature(repo.fetch_all_reference_tables)
        print(f"✓ fetch_all_reference_tables signature: {sig}")
        
        # Check validate_reference_tables returns tuple
        sig = inspect.signature(repo.validate_reference_tables)
        print(f"✓ validate_reference_tables signature: {sig}")
        
        return True
    except Exception as e:
        print(f"✗ Error testing function signatures: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Run all tests."""
    print("=" * 60)
    print("Repository Module Validation Test")
    print("=" * 60)
    
    tests = [
        ("Import Test", test_imports),
        ("Function Structure Test", test_function_structure),
        ("Function Signature Test", test_function_signatures)
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
        print("1. A running PostgreSQL/Supabase instance")
        print("2. Populated reference tables (Banks, Pricing, etc.)")
        print("3. Database credentials in .streamlit/secrets.toml")
        print("4. Run the application: streamlit run app.py")
        return 0
    else:
        print("✗ Some tests failed!")
        print("=" * 60)
        return 1

if __name__ == "__main__":
    sys.exit(main())
