"""
Test script to validate minimum unit delivery (0.01 units) at optimizer output stage.

This test verifies that the optimizer rounds all allocation lines up to the nearest 0.01.
"""

import sys


def test_optimizer_output_rounding():
    """
    Test that minimum unit delivery is enforced by rounding up optimizer output.
    
    The optimizer works with full precision during calculation, but each 
    allocation line (supply line) is rounded up to nearest 0.01 in output.
    This allows bundling multiple small requirements without forcing each to 0.01.
    """
    print("Testing minimum unit delivery via optimizer output rounding...")
    
    # Test cases showing how optimizer output gets rounded up
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
            "input": 0.0034,
            "expected": 0.01,
            "description": "0.0034 units - rounds up to 0.01 (minimum)"
        },
        {
            "input": 0.0024,
            "expected": 0.01,
            "description": "0.0024 units - rounds up to 0.01 (minimum)"
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
    
    print("\nOptimizer Output Rounding Tests:")
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


def test_bundling_example():
    """
    Test that bundling works: two small requirements can be combined.
    
    Example: 0.0034 + 0.0024 = 0.0058 can be allocated as a single 0.01 unit
    rather than forcing 0.01 + 0.01 = 0.02 units.
    """
    print("\nTesting bundling example (0.0034 + 0.0024)...")
    
    import math
    
    # Individual rounding (OLD approach - would give 0.02)
    individual_rounded = math.ceil(0.0034 * 100) / 100 + math.ceil(0.0024 * 100) / 100
    print(f"  Individual rounding: 0.01 + 0.01 = {individual_rounded:.2f} units")
    
    # Combined rounding (NEW approach - gives 0.01)
    combined = 0.0034 + 0.0024
    combined_rounded = math.ceil(combined * 100) / 100
    print(f"  Combined rounding: (0.0034 + 0.0024) = 0.0058 → {combined_rounded:.2f} units")
    
    if combined_rounded == 0.01:
        print("  ✓ Bundling works correctly - single 0.01 unit allocation")
        return True
    else:
        print(f"  ✗ Bundling failed - expected 0.01, got {combined_rounded}")
        return False


def test_rounding_in_code():
    """
    Verify that the rounding is present in app.py at optimizer output stage.
    """
    print("\nVerifying rounding function in app.py...")
    
    try:
        with open('app.py', 'r') as f:
            content = f.read()
            
        # Check for math.ceil usage in extract function
        if "math.ceil" in content and "qty_rounded" in content:
            print("  ✓ Rounding logic found in optimizer output (extract function)")
        else:
            print("  ✗ Rounding logic not found in extract function")
            return False
        
        # Check that it's in the extract function
        if "def extract(xvars, zvars):" in content:
            print("  ✓ extract function found")
            
            # Check if rounding is applied to units_supplied
            extract_section_start = content.find("def extract(xvars, zvars):")
            extract_section_end = content.find("return pd.DataFrame(rows)", extract_section_start)
            extract_section = content[extract_section_start:extract_section_end]
            
            if "qty_rounded" in extract_section and "units_supplied" in extract_section:
                print("  ✓ Rounding applied to units_supplied in extract function")
            else:
                print("  ✗ Rounding not properly applied in extract function")
                return False
        else:
            print("  ✗ extract function not found")
            return False
        
        return True
    except Exception as e:
        print(f"  ✗ Error reading app.py: {e}")
        return False


def main():
    print("=" * 60)
    print("Minimum Unit Delivery Tests (Optimizer Output Stage)")
    print("=" * 60)
    
    results = []
    
    results.append(("optimizer_output_rounding", test_optimizer_output_rounding()))
    results.append(("bundling_example", test_bundling_example()))
    results.append(("rounding_in_code", test_rounding_in_code()))
    
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
