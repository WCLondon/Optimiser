"""
Test script to validate total row formatting (3 decimals max, remove trailing zeros).
"""

def format_units_total(value):
    """
    Format total row units with up to 3 decimal places.
    - Maximum 3 decimal places
    - Remove trailing zeros (but keep at least 2 decimal places)
    """
    if value == 0:
        return "0.00"
    
    # Format with 3 decimals
    formatted = f"{value:.3f}"
    parts = formatted.split('.')
    if len(parts) == 2:
        integer_part = parts[0]
        decimal_part = parts[1].rstrip('0')
        # Ensure at least 2 decimal places
        if len(decimal_part) < 2:
            decimal_part = decimal_part.ljust(2, '0')
        return f"{integer_part}.{decimal_part}"
    return formatted


def test_format_units_total():
    """Test the total row formatting function"""
    print("Testing format_units_total...")
    
    test_cases = [
        # (input, expected_output, description)
        (0.349, "0.349", "3 significant digits, no trailing zero"),
        (0.350, "0.35", "trailing zero removed"),
        (0.35, "0.35", "already 2 decimals"),
        (0.228, "0.228", "3 decimals"),
        (0.121, "0.121", "3 decimals"),
        (0.12, "0.12", "2 decimals"),
        (1.5, "1.50", "minimum 2 decimals"),
        (2.0, "2.00", "minimum 2 decimals"),
        (0.080, "0.08", "trailing zero removed"),
        (0.083, "0.083", "3 decimals, no trailing zero"),
        (0.0, "0.00", "zero case"),
        (0.3456, "0.346", "rounds to 3 decimals"),
        (10.123, "10.123", "integer > 1 with 3 decimals"),
        (10.120, "10.12", "integer > 1 with trailing zero"),
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
    
    # The user's example shows "0.35" in the total row, which suggests rounding
    # But the comment says "keep the total rows as 3 decimal places (unless there are trailing zeros)"
    # So 0.349 should display as "0.349" (3 decimals, no trailing zero)
    # But 0.350 should display as "0.35" (trailing zero removed)
    
    expected = "0.349"  # 3 decimals, no trailing zero
    if formatted_total == expected:
        print(f"  ✓ Correct: {formatted_total} matches expected {expected}")
        return True
    else:
        print(f"  ✗ Got {formatted_total}, expected {expected}")
        return False


def main():
    print("=" * 60)
    print("Total Row Formatting Tests")
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
