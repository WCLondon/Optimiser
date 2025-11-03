"""
Test minimum delivery padding logic
"""
import pandas as pd

def test_enforce_minimum_delivery():
    """Test that minimum delivery of 0.01 is enforced by padding cheapest habitat"""
    
    # Mock enforce_minimum_delivery function
    def enforce_minimum_delivery(alloc_df):
        """
        Ensure total units_supplied >= 0.01 by padding the cheapest habitat.
        If total < 0.01, add extra units to the cheapest habitat to reach 0.01 minimum.
        """
        if alloc_df.empty:
            return alloc_df, 0.0
        
        total_units = alloc_df["units_supplied"].sum()
        
        if total_units < 0.01:
            # Find the cheapest habitat (lowest unit_price)
            cheapest_idx = alloc_df["unit_price"].idxmin()
            shortage = 0.01 - total_units
            
            # Add shortage to the cheapest habitat
            alloc_df.loc[cheapest_idx, "units_supplied"] += shortage
            alloc_df.loc[cheapest_idx, "cost"] = alloc_df.loc[cheapest_idx, "units_supplied"] * alloc_df.loc[cheapest_idx, "unit_price"]
        
        # Recalculate total cost
        total_cost = float(alloc_df["cost"].sum())
        return alloc_df, total_cost
    
    # Test case 1: Example from user comment (0.0064 Scrub + 0.0012 Net Gain)
    alloc_df = pd.DataFrame({
        "demand_habitat": ["Scrub", "Net Gain"],
        "units_supplied": [0.0064, 0.0012],
        "unit_price": [22000, 22000],
        "cost": [0.0064 * 22000, 0.0012 * 22000]
    })
    
    result_df, total_cost = enforce_minimum_delivery(alloc_df)
    
    # Total should be 0.01
    assert abs(result_df["units_supplied"].sum() - 0.01) < 1e-9, f"Total should be 0.01, got {result_df['units_supplied'].sum()}"
    
    # The cheapest habitat (both have same price, so first one) should have added units
    # Expected: Scrub gets 0.0064 + (0.01 - 0.0076) = 0.0064 + 0.0024 = 0.0088
    # Wait, both have same price, so it picks the first one
    print("Test case 1 (same prices):")
    print(f"Scrub: {result_df.iloc[0]['units_supplied']:.4f}")
    print(f"Net Gain: {result_df.iloc[1]['units_supplied']:.4f}")
    print(f"Total: {result_df['units_supplied'].sum():.4f}")
    
    # Test case 2: Different prices (Net Gain cheaper)
    alloc_df2 = pd.DataFrame({
        "demand_habitat": ["Scrub", "Net Gain"],
        "units_supplied": [0.0064, 0.0012],
        "unit_price": [25000, 20000],  # Net Gain is cheaper
        "cost": [0.0064 * 25000, 0.0012 * 20000]
    })
    
    result_df2, total_cost2 = enforce_minimum_delivery(alloc_df2)
    
    print("\nTest case 2 (Net Gain cheaper):")
    print(f"Scrub: {result_df2.iloc[0]['units_supplied']:.4f}")
    print(f"Net Gain: {result_df2.iloc[1]['units_supplied']:.4f}")
    print(f"Total: {result_df2['units_supplied'].sum():.4f}")
    
    # Net Gain should have added units since it's cheaper
    # Expected: Net Gain gets 0.0012 + 0.0024 = 0.0036
    expected_net_gain = 0.0012 + (0.01 - 0.0076)
    assert abs(result_df2.iloc[1]["units_supplied"] - expected_net_gain) < 1e-9, \
        f"Net Gain should be {expected_net_gain:.4f}, got {result_df2.iloc[1]['units_supplied']:.4f}"
    
    # Test case 3: Already above 0.01
    alloc_df3 = pd.DataFrame({
        "demand_habitat": ["Scrub"],
        "units_supplied": [0.05],
        "unit_price": [22000],
        "cost": [0.05 * 22000]
    })
    
    result_df3, total_cost3 = enforce_minimum_delivery(alloc_df3)
    
    print("\nTest case 3 (already above 0.01):")
    print(f"Scrub: {result_df3.iloc[0]['units_supplied']:.4f}")
    print(f"Total: {result_df3['units_supplied'].sum():.4f}")
    
    # Should remain unchanged
    assert abs(result_df3.iloc[0]["units_supplied"] - 0.05) < 1e-9, "Should remain unchanged"
    
    print("\nAll tests passed!")

if __name__ == "__main__":
    test_enforce_minimum_delivery()
