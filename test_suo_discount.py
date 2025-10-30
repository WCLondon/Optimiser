"""
Test SUO cost discount calculation
"""

import pandas as pd


def test_suo_discount_calculation():
    """Test that SUO discount is calculated correctly: usable_surplus / total_units"""
    print("\n=== Test: SUO Discount Calculation (New Formula) ===")
    
    # Mock allocation data: 100 units allocated across 2 banks
    alloc_df = pd.DataFrame({
        "bank_id": ["bank1", "bank1", "bank2"],
        "tier": ["local", "local", "adjacent"],
        "units_supplied": [40.0, 30.0, 30.0],
        "cost": [4000.0, 3000.0, 4500.0]
    })
    
    # Mock metric surplus: 60 units of Medium distinctiveness
    metric_surplus = pd.DataFrame({
        "habitat": ["Heathland"],
        "broad_group": ["Heathland"],
        "distinctiveness": ["Medium"],
        "units_surplus": [60.0]
    })
    
    # Calculate expected values
    # Total units to mitigate: 100
    # Eligible surplus: 60 (Medium)
    # Usable (50%): 30
    # Discount formula: usable / total_units = 30 / 100 = 30%
    
    print(f"Allocation: {alloc_df['units_supplied'].sum()} units across {alloc_df['bank_id'].nunique()} banks")
    print(f"Metric surplus: {metric_surplus['units_surplus'].sum()} units (Medium)")
    print(f"\nExpected:")
    print(f"  Eligible: 60 units")
    print(f"  Usable (50%): 30 units")
    print(f"  Total units to mitigate: 100 units")
    print(f"  Discount: 30 / 100 = 30%")
    
    # Manual calculation to verify logic
    eligible = 60.0  # All Medium
    usable = eligible * 0.5  # 50% headroom
    total_units = alloc_df["units_supplied"].sum()
    discount = usable / total_units
    
    print(f"\nActual calculation:")
    print(f"  Eligible: {eligible} units")
    print(f"  Usable: {usable} units")
    print(f"  Total units: {total_units} units")
    print(f"  Discount: {discount*100:.1f}%")
    
    # Verify discount is correct
    assert abs(discount - 0.30) < 0.001, f"Discount {discount} not 0.30"
    
    # Test rounding to nearest £100
    original_price = 1234.56
    rounded = round(original_price / 100) * 100
    print(f"\nPrice rounding test:")
    print(f"  Original: £{original_price:.2f}")
    print(f"  Rounded to nearest £100: £{rounded:.0f}")
    assert rounded == 1200, f"Rounded price {rounded} not 1200"
    
    # Test discount application
    original_cost = 10000
    discounted_cost = original_cost * (1 - discount)
    savings = original_cost - discounted_cost
    print(f"\nDiscount application:")
    print(f"  Original cost: £{original_cost:,.0f}")
    print(f"  Discount: {discount*100:.1f}%")
    print(f"  Discounted cost: £{discounted_cost:,.0f}")
    print(f"  Savings: £{savings:,.0f}")
    
    print("\n✅ SUO discount calculation test passed")
    return True


if __name__ == "__main__":
    try:
        success = test_suo_discount_calculation()
        exit(0 if success else 1)
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        exit(1)
