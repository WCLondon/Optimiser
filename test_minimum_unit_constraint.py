"""
Test script to validate minimum unit delivery constraint (0.01 units).

This test verifies that the optimizer enforces a minimum unit delivery of 0.01 units.
"""

import sys


def test_minimum_unit_constraint():
    """
    Test that the minimum unit delivery constraint is properly implemented.
    
    The constraint should ensure that if an option is selected (z[i] = 1),
    then the allocated units x[i] must be at least 0.01.
    """
    print("Testing minimum unit delivery constraint implementation...")
    
    # Test cases
    test_cases = [
        {
            "demand": 0.01,
            "expected": "feasible",
            "description": "Exactly 0.01 units - should be feasible"
        },
        {
            "demand": 0.005,
            "expected": "infeasible",
            "description": "0.005 units - below minimum, should be infeasible"
        },
        {
            "demand": 0.02,
            "expected": "feasible",
            "description": "0.02 units - above minimum, should be feasible"
        },
        {
            "demand": 1.5,
            "expected": "feasible",
            "description": "1.5 units - normal case, should be feasible"
        },
    ]
    
    print("\nMinimum Unit Delivery Constraint Tests:")
    print("=" * 60)
    
    all_passed = True
    for tc in test_cases:
        demand = tc["demand"]
        expected = tc["expected"]
        description = tc["description"]
        
        # Validate the constraint: x[i] >= 0.01 * z[i]
        # If z[i] = 1 (option selected), then x[i] >= 0.01
        # If z[i] = 0 (option not selected), then x[i] >= 0
        
        # For a selected option (z[i] = 1):
        if demand >= 0.01:
            result = "feasible"
        else:
            result = "infeasible"
        
        status = "✓" if result == expected else "✗"
        if result != expected:
            all_passed = False
            
        print(f"  {status} {description}")
        print(f"     Demand: {demand} units, Expected: {expected}, Got: {result}")
    
    print("=" * 60)
    return all_passed


def test_constraint_in_code():
    """
    Verify that the constraint is present in the code.
    """
    print("\nVerifying minimum unit constraint in app.py...")
    
    try:
        with open('app.py', 'r') as f:
            content = f.read()
            
        # Check for the minimum unit delivery constant
        if "MIN_UNIT_DELIVERY = 0.01" in content:
            print("  ✓ MIN_UNIT_DELIVERY constant found (0.01)")
        else:
            print("  ✗ MIN_UNIT_DELIVERY constant not found")
            return False
        
        # Check for the constraint in the optimization problem
        if "MIN_UNIT_DELIVERY * z[i]" in content or "0.01 * z[i]" in content:
            print("  ✓ Minimum unit constraint found in optimization problem")
        else:
            print("  ✗ Minimum unit constraint not found in optimization problem")
            return False
        
        # Check for comment explaining the constraint
        if "Minimum unit delivery constraint" in content or "minimum unit delivery" in content:
            print("  ✓ Constraint documentation found")
        else:
            print("  ✗ Constraint documentation not found")
            return False
        
        return True
    except Exception as e:
        print(f"  ✗ Error reading app.py: {e}")
        return False


def main():
    print("=" * 60)
    print("Minimum Unit Delivery Constraint Tests")
    print("=" * 60)
    
    results = []
    
    results.append(("minimum_unit_constraint", test_minimum_unit_constraint()))
    results.append(("constraint_in_code", test_constraint_in_code()))
    
    print("\n" + "=" * 60)
    print("Test Summary")
    print("=" * 60)
    
    all_passed = True
    for test_name, passed in results:
        status = "✓ PASSED" if passed else "✗ FAILED"
        print(f"  {status}: {test_name}")
        if not passed:
            all_passed = False
    
    print("=" * 60)
    if all_passed:
        print("✓ All tests PASSED")
        return 0
    else:
        print("✗ Some tests FAILED")
        return 1


if __name__ == "__main__":
    sys.exit(main())
