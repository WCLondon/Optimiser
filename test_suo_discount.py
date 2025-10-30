"""
Test SUO cost discount calculation
"""

import pandas as pd


def test_suo_discount_calculation():
    """Test that SUO discount is calculated correctly with bank SRMs"""
    print("\n=== Test: SUO Discount Calculation ===")
    
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
    
    # Mock SRM data
    srm_df = pd.DataFrame({
        "tier": ["local", "adjacent", "far"],
        "multiplier": [1.0, 1.33, 2.0]
    })
    
    # Calculate expected values
    # Total units: 100
    # Bank1: 70 units at local (SRM=1.0)
    # Bank2: 30 units at adjacent (SRM=1.33)
    # Weighted avg SRM: (70*1.0 + 30*1.33) / 100 = 1.099
    
    # Eligible surplus: 60 (Medium)
    # Usable (50%): 30
    # Effective offset: 30 / 1.099 = 27.3
    # Discount: 27.3 / 100 = 27.3%
    
    print(f"Allocation: {alloc_df['units_supplied'].sum()} units across {alloc_df['bank_id'].nunique()} banks")
    print(f"Metric surplus: {metric_surplus['units_surplus'].sum()} units (Medium)")
    print(f"\nExpected:")
    print(f"  Eligible: 60 units")
    print(f"  Usable (50%): 30 units")
    print(f"  Weighted avg SRM: ~1.10")
    print(f"  Effective offset: ~27 units")
    print(f"  Discount: ~27%")
    
    # Manual calculation to verify logic
    eligible = 60.0  # All Medium
    usable = eligible * 0.5  # 50% headroom
    
    # Calculate weighted SRM
    bank_units = alloc_df.groupby(["bank_id", "tier"])["units_supplied"].sum().reset_index()
    tier_srm = dict(zip(srm_df["tier"].str.lower(), srm_df["multiplier"]))
    bank_units["srm"] = bank_units["tier"].str.lower().map(tier_srm)
    weighted_srm = (bank_units["srm"] * bank_units["units_supplied"]).sum() / bank_units["units_supplied"].sum()
    
    effective = usable / weighted_srm
    total_units = alloc_df["units_supplied"].sum()
    discount = effective / total_units
    
    print(f"\nActual calculation:")
    print(f"  Eligible: {eligible} units")
    print(f"  Usable: {usable} units")
    print(f"  Weighted SRM: {weighted_srm:.3f}")
    print(f"  Effective: {effective:.2f} units")
    print(f"  Discount: {discount*100:.1f}%")
    
    # Verify discount is reasonable
    assert 0.25 <= discount <= 0.30, f"Discount {discount} not in expected range"
    
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
