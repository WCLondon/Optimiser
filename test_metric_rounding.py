"""
Test script to validate rounding up to nearest 0.01 in metric_reader.
"""

import sys
sys.path.insert(0, '/home/runner/work/Optimiser/Optimiser')

from metric_reader import round_up_to_nearest_hundredth


def test_round_up_to_nearest_hundredth():
    """Test the round_up_to_nearest_hundredth function"""
    print("Testing round_up_to_nearest_hundredth...")
    
    test_cases = [
        # (input, expected_output, description)
        (0.001, 0.01, "0.001 rounds up to 0.01"),
        (0.005, 0.01, "0.005 rounds up to 0.01"),
        (0.009, 0.01, "0.009 rounds up to 0.01"),
        (0.01, 0.01, "0.01 stays at 0.01"),
        (0.011, 0.02, "0.011 rounds up to 0.02"),
        (0.019, 0.02, "0.019 rounds up to 0.02"),
        (0.02, 0.02, "0.02 stays at 0.02"),
        (0.228, 0.23, "0.228 rounds up to 0.23"),
        (0.121, 0.13, "0.121 rounds up to 0.13"),
        (0.349, 0.35, "0.349 rounds up to 0.35"),
        (1.501, 1.51, "1.501 rounds up to 1.51"),
        (1.5, 1.5, "1.5 stays at 1.5"),
        (0.0, 0.0, "0.0 stays at 0.0"),
        (0.1234, 0.13, "0.1234 rounds up to 0.13"),
    ]
    
    all_passed = True
    for value, expected, description in test_cases:
        result = round_up_to_nearest_hundredth(value)
        status = "✓" if result == expected else "✗"
        if result != expected:
            all_passed = False
            print(f"  {status} {description} - Got {result}, expected {expected}")
        else:
            print(f"  {status} {description}")
    
    return all_passed


def test_minimum_unit_enforcement():
    """Test that all values below 0.01 become 0.01"""
    print("\nTesting minimum unit enforcement...")
    
    small_values = [0.001, 0.002, 0.005, 0.008, 0.009, 0.00001]
    
    all_passed = True
    for val in small_values:
        result = round_up_to_nearest_hundredth(val)
        if result != 0.01:
            print(f"  ✗ {val} should round up to 0.01, got {result}")
            all_passed = False
        else:
            print(f"  ✓ {val} rounds up to 0.01")
    
    return all_passed


def main():
    print("=" * 60)
    print("Round Up to Nearest 0.01 Tests")
    print("=" * 60)
    
    results = []
    
    results.append(("round_up_to_nearest_hundredth", test_round_up_to_nearest_hundredth()))
    results.append(("minimum_unit_enforcement", test_minimum_unit_enforcement()))
    
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
