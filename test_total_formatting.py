"""
Test script to validate total row formatting (2 decimals).
"""

def format_units_total(value):
    """
    Format total row units with 2 decimal places.
    - Exactly 2 decimal places
    - All calculations rounded to 2 decimals
    """
    if value == 0:
        return "0.00"
    
    # Format with 2 decimals
    formatted = f"{value:.2f}"
    return formatted


def test_format_units_total():
    """Test the total row formatting function"""
    print("Testing format_units_total...")
    
    test_cases = [
        # (input, expected_output, description)
        (0.349, "0.35", "rounds to 2 decimals"),
        (0.350, "0.35", "2 decimals"),
        (0.35, "0.35", "already 2 decimals"),
        (0.228, "0.23", "rounds to 2 decimals"),
        (0.121, "0.12", "rounds to 2 decimals"),
        (0.12, "0.12", "2 decimals"),
        (1.5, "1.50", "2 decimals"),
        (2.0, "2.00", "2 decimals"),
        (0.080, "0.08", "2 decimals"),
        (0.083, "0.08", "rounds to 2 decimals"),
        (0.0, "0.00", "zero case"),
        (0.3456, "0.35", "rounds to 2 decimals"),
        (10.123, "10.12", "rounds to 2 decimals"),
        (10.126, "10.13", "rounds up to 2 decimals"),
    ]
    
    all_passed = True
    for value, expected, description in test_cases:
        result = format_units_total(value)
        status = "✓" if result == expected else "✗"
        if result != expected:
            all_passed = False
            print(f"  {status} format_units_total({value}) = {result} (expected: {expected}) - {description}")
        else:
            print(f"  {status} format_units_total({value}) = {result} - {description}")
    
    return all_passed


def test_user_example():
    """Test the specific example from the user's comment"""
    print("\nTesting user's example...")
    print("  0.228 + 0.121 = 0.349")
    
    total = 0.228 + 0.121
    formatted_total = format_units_total(total)
    
    print(f"  Formatted total: {formatted_total}")
    
    # With 2 decimal places, 0.349 should round to 0.35
    expected = "0.35"  # 2 decimals
    if formatted_total == expected:
        print(f"  ✓ Correct: {formatted_total} matches expected {expected}")
        return True
    else:
        print(f"  ✗ Got {formatted_total}, expected {expected}")
        return False


def main():
    print("=" * 60)
    print("Total Row Formatting Tests (2 decimals)")
    print("=" * 60)
    
    test1_passed = test_format_units_total()
    test2_passed = test_user_example()
    
    print("\n" + "=" * 60)
    if test1_passed and test2_passed:
        print("✓ All tests PASSED")
        return 0
    else:
        print("✗ Some tests FAILED")
        return 1


if __name__ == "__main__":
    import sys
    sys.exit(main())
