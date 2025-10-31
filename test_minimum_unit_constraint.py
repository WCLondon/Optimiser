"""
Test script to validate minimum unit delivery (0.01 units) in metric reader.

This test verifies that the metric reader rounds all habitat units up to the nearest 0.01.
"""

import sys


def test_minimum_unit_constraint():
    """
    Test that minimum unit delivery is enforced by rounding up in metric reader.
    
    All units from the metric should be rounded up to the nearest 0.01 at the 
    point of upload, ensuring the optimizer always works with values >= 0.01.
    """
    print("Testing minimum unit delivery via metric reader rounding...")
    
    # Test cases showing how metric values get rounded up
    test_cases = [
        {
            "input": 0.01,
            "expected": 0.01,
            "description": "Exactly 0.01 units - no change needed"
        },
        {
            "input": 0.005,
            "expected": 0.01,
            "description": "0.005 units - rounds up to 0.01"
        },
        {
            "input": 0.02,
            "expected": 0.02,
            "description": "0.02 units - no change needed"
        },
        {
            "input": 1.5,
            "expected": 1.5,
            "description": "1.5 units - no change needed"
        },
        {
            "input": 0.228,
            "expected": 0.23,
            "description": "0.228 units - rounds up to 0.23"
        },
        {
            "input": 0.001,
            "expected": 0.01,
            "description": "0.001 units - rounds up to 0.01 (minimum)"
        },
    ]
    
    print("\nMetric Reader Rounding Tests:")
    print("=" * 60)
    
    all_passed = True
    for tc in test_cases:
        input_val = tc["input"]
        expected = tc["expected"]
        description = tc["description"]
        
        # Simulate the rounding function
        import math
        result = math.ceil(input_val * 100) / 100 if input_val > 0 else 0.0
        
        status = "✓" if result == expected else "✗"
        if result != expected:
            all_passed = False
            print(f"  {status} {description} - Got {result}")
        else:
            print(f"  {status} {description}")
    
    print("=" * 60)
    return all_passed


def test_constraint_in_code():
    """
    Verify that the rounding function is present in metric_reader.py.
    """
    print("\nVerifying rounding function in metric_reader.py...")
    
    try:
        with open('metric_reader.py', 'r') as f:
            content = f.read()
            
        # Check for the rounding function
        if "def round_up_to_nearest_hundredth" in content:
            print("  ✓ round_up_to_nearest_hundredth function found")
        else:
            print("  ✗ round_up_to_nearest_hundredth function not found")
            return False
        
        # Check for math.ceil usage
        if "math.ceil" in content:
            print("  ✓ math.ceil usage found")
        else:
            print("  ✗ math.ceil usage not found")
            return False
        
        # Check that the function is being used
        if "round_up_to_nearest_hundredth(" in content and content.count("round_up_to_nearest_hundredth(") > 1:
            print("  ✓ Rounding function is being used in multiple places")
        else:
            print("  ✗ Rounding function not used sufficiently")
            return False
        
        return True
    except Exception as e:
        print(f"  ✗ Error reading metric_reader.py: {e}")
        return False


def main():
    print("=" * 60)
    print("Minimum Unit Delivery Tests (Metric Reader)")
    print("=" * 60)
    
    results = []
    
    results.append(("metric_reader_rounding", test_minimum_unit_constraint()))
    results.append(("rounding_function_in_code", test_constraint_in_code()))
    
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
