#!/usr/bin/env python3
"""
Test script for backend API validation
Tests that all components can be imported and have correct structure
"""

import sys
import os

def test_backend_imports():
    """Test that backend modules import correctly"""
    print("Testing backend imports...")
    
    try:
        from backend import app
        print("✓ backend.app imported")
    except ImportError as e:
        print(f"✗ Failed to import backend.app: {e}")
        return False
    
    try:
        from backend import tasks
        print("✓ backend.tasks imported")
    except ImportError as e:
        print(f"✗ Failed to import backend.tasks: {e}")
        return False
    
    try:
        from backend import worker
        print("✓ backend.worker imported")
    except ImportError as e:
        print(f"✗ Failed to import backend.worker: {e}")
        return False
    
    return True


def test_backend_structure():
    """Test backend API structure"""
    print("\nTesting backend structure...")
    
    try:
        from backend.app import app as fastapi_app
        
        # Check routes exist
        routes = [route.path for route in fastapi_app.routes]
        expected_routes = ["/health", "/jobs", "/jobs/{job_id}"]
        
        for route in expected_routes:
            if any(route in r for r in routes):
                print(f"✓ Route {route} exists")
            else:
                print(f"✗ Route {route} missing")
                return False
        
        return True
        
    except Exception as e:
        print(f"✗ Error testing structure: {e}")
        return False


def test_backend_client():
    """Test backend client module"""
    print("\nTesting backend client...")
    
    try:
        import backend_client
        
        expected_functions = [
            "submit_optimization_job",
            "check_job_status",
            "check_backend_health",
            "show_backend_status"
        ]
        
        for func in expected_functions:
            if hasattr(backend_client, func):
                print(f"✓ Function {func} exists")
            else:
                print(f"✗ Function {func} missing")
                return False
        
        return True
        
    except Exception as e:
        print(f"✗ Error testing backend client: {e}")
        return False


def test_tasks_structure():
    """Test tasks module structure"""
    print("\nTesting tasks structure...")
    
    try:
        from backend import tasks
        
        if hasattr(tasks, "run_optimization"):
            print("✓ run_optimization function exists")
        else:
            print("✗ run_optimization function missing")
            return False
        
        return True
        
    except Exception as e:
        print(f"✗ Error testing tasks: {e}")
        return False


def main():
    """Run all tests"""
    print("=" * 60)
    print("Backend API Validation Tests")
    print("=" * 60)
    
    tests = [
        ("Import Test", test_backend_imports),
        ("Structure Test", test_backend_structure),
        ("Backend Client Test", test_backend_client),
        ("Tasks Test", test_tasks_structure)
    ]
    
    results = []
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"\n✗ {test_name} crashed: {e}")
            results.append((test_name, False))
    
    print("\n" + "=" * 60)
    print("Test Results")
    print("=" * 60)
    
    for test_name, result in results:
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"{status}: {test_name}")
    
    all_passed = all(result for _, result in results)
    
    if all_passed:
        print("\n✅ All tests passed!")
        return 0
    else:
        print("\n❌ Some tests failed")
        return 1


if __name__ == "__main__":
    sys.exit(main())
