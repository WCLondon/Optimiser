"""
Test for Felled Woodland trading with Lowland mixed deciduous woodland.

This test verifies that 'Woodland and forest - Felled/Replacement for felled woodland'
can be matched with 'Woodland and forest - Lowland mixed deciduous woodland' supply
when the appropriate trading rule is configured.

Issue: Felled Woodland / Lowland Mixed Deciduous
The optimizer needs to treat 'Felled/Replacement for felled woodland' like 
'Lowland mixed deciduous woodland' when optimizing / finding suitable trades.
"""

import pandas as pd
from optimizer_core import prepare_options, build_dist_levels_map


def test_felled_woodland_trading_with_rule():
    """
    Test that Felled woodland can trade with Lowland mixed deciduous when trading rule exists.
    
    Scenario:
    - Demand: 'Woodland and forest - Felled/Replacement for felled woodland' (High distinctiveness)
    - Supply available: 'Woodland and forest - Lowland mixed deciduous woodland' (High distinctiveness)
    - Trading rule exists: Felled -> Lowland mixed deciduous allowed
    
    Expected: Optimizer should find valid options to match Felled with Lowland mixed deciduous
    """
    
    # Setup demand
    demand_df = pd.DataFrame({
        "habitat_name": ["Woodland and forest - Felled/Replacement for felled woodland"],
        "units_required": [2.5]
    })
    
    # Setup backend data
    backend = {
        "Banks": pd.DataFrame({
            "bank_id": ["BANK001"],
            "bank_name": ["Test Bank"],
            "BANK_KEY": ["Test Bank"],
            "lpa_name": ["Test LPA"],
            "nca_name": ["Test NCA"]
        }),
        
        "HabitatCatalog": pd.DataFrame({
            "habitat_name": [
                "Woodland and forest - Felled/Replacement for felled woodland",
                "Woodland and forest - Lowland mixed deciduous woodland"
            ],
            "broader_type": ["Woodland and forest", "Woodland and forest"],
            "UmbrellaType": ["Area Habitat", "Area Habitat"],
            "distinctiveness_name": ["High", "High"]
        }),
        
        "Stock": pd.DataFrame({
            "stock_id": ["STK001"],
            "bank_id": ["BANK001"],
            "bank_name": ["Test Bank"],
            "habitat_name": ["Woodland and forest - Lowland mixed deciduous woodland"],
            "quantity_available": [10.0],
            "BANK_KEY": ["Test Bank"]
        }),
        
        "Pricing": pd.DataFrame({
            "bank_id": ["BANK001"],
            "BANK_KEY": ["Test Bank"],
            "bank_name": ["Test Bank"],
            "habitat_name": ["Woodland and forest - Lowland mixed deciduous woodland"],
            "contract_size": ["small"],
            "tier": ["local"],
            "price": [15000.0],
            "broader_type": ["Woodland and forest"],
            "distinctiveness_name": ["High"]
        }),
        
        "DistinctivenessLevels": pd.DataFrame({
            "distinctiveness_name": ["Very Low", "Low", "Medium", "High", "Very High"],
            "level_value": [0, 1, 2, 3, 4]
        }),
        
        # CRITICAL: Trading rule that allows Felled to use Lowland mixed deciduous supply
        "TradingRules": pd.DataFrame({
            "demand_habitat": ["Woodland and forest - Felled/Replacement for felled woodland"],
            "allowed_supply_habitat": ["Woodland and forest - Lowland mixed deciduous woodland"],
            "min_distinctiveness_name": [None]  # No minimum required, both are High
        })
    }
    
    # Call prepare_options
    options, stock_caps, stock_bankkey = prepare_options(
        demand_df=demand_df,
        chosen_size="small",
        target_lpa="Test LPA",
        target_nca="Test NCA",
        lpa_neigh=[],
        nca_neigh=[],
        lpa_neigh_norm=[],
        nca_neigh_norm=[],
        backend=backend,
        promoter_discount_type=None,
        promoter_discount_value=None
    )
    
    print("\n" + "="*80)
    print("Test: Felled Woodland Trading WITH Trading Rule")
    print("="*80)
    print(f"\nDemand: {demand_df['habitat_name'].iloc[0]}")
    print(f"Units needed: {demand_df['units_required'].iloc[0]}")
    print(f"\nSupply available: Woodland and forest - Lowland mixed deciduous woodland (10.0 units)")
    print(f"Trading rule configured: ✓ YES")
    print(f"\nOptions found: {len(options)}")
    
    if options:
        for i, opt in enumerate(options):
            print(f"\nOption {i+1}:")
            print(f"  Supply habitat: {opt['supply_habitat']}")
            print(f"  Bank: {opt['BANK_KEY']}")
            print(f"  Tier: {opt['tier']}")
            print(f"  Unit price: £{opt['unit_price']:,.0f}")
    
    # Verify we got valid options
    assert len(options) > 0, "❌ No options found - trading rule not working!"
    assert options[0]["demand_habitat"] == "Woodland and forest - Felled/Replacement for felled woodland"
    assert options[0]["supply_habitat"] == "Woodland and forest - Lowland mixed deciduous woodland"
    
    print("\n✅ TEST PASSED: Felled woodland can trade with Lowland mixed deciduous when rule exists")
    print("="*80)
    return True


def test_felled_woodland_trading_without_rule():
    """
    Test that Felled woodland CANNOT trade with Lowland mixed deciduous WITHOUT trading rule.
    
    This demonstrates why the trading rule is necessary:
    - Both habitats are High distinctiveness
    - High distinctiveness requires exact habitat match by default
    - Without explicit trading rule, they cannot trade
    
    Expected: No valid options (or only exact match if Felled supply existed)
    """
    
    # Setup demand
    demand_df = pd.DataFrame({
        "habitat_name": ["Woodland and forest - Felled/Replacement for felled woodland"],
        "units_required": [2.5]
    })
    
    # Setup backend data - SAME as above but NO TradingRules
    backend = {
        "Banks": pd.DataFrame({
            "bank_id": ["BANK001"],
            "bank_name": ["Test Bank"],
            "BANK_KEY": ["Test Bank"],
            "lpa_name": ["Test LPA"],
            "nca_name": ["Test NCA"]
        }),
        
        "HabitatCatalog": pd.DataFrame({
            "habitat_name": [
                "Woodland and forest - Felled/Replacement for felled woodland",
                "Woodland and forest - Lowland mixed deciduous woodland"
            ],
            "broader_type": ["Woodland and forest", "Woodland and forest"],
            "UmbrellaType": ["Area Habitat", "Area Habitat"],
            "distinctiveness_name": ["High", "High"]
        }),
        
        "Stock": pd.DataFrame({
            "stock_id": ["STK001"],
            "bank_id": ["BANK001"],
            "bank_name": ["Test Bank"],
            "habitat_name": ["Woodland and forest - Lowland mixed deciduous woodland"],
            "quantity_available": [10.0],
            "BANK_KEY": ["Test Bank"]
        }),
        
        "Pricing": pd.DataFrame({
            "bank_id": ["BANK001"],
            "BANK_KEY": ["Test Bank"],
            "bank_name": ["Test Bank"],
            "habitat_name": ["Woodland and forest - Lowland mixed deciduous woodland"],
            "contract_size": ["small"],
            "tier": ["local"],
            "price": [15000.0],
            "broader_type": ["Woodland and forest"],
            "distinctiveness_name": ["High"]
        }),
        
        "DistinctivenessLevels": pd.DataFrame({
            "distinctiveness_name": ["Very Low", "Low", "Medium", "High", "Very High"],
            "level_value": [0, 1, 2, 3, 4]
        }),
        
        # NO TradingRules - this is the key difference
        "TradingRules": pd.DataFrame()
    }
    
    # Call prepare_options
    options, stock_caps, stock_bankkey = prepare_options(
        demand_df=demand_df,
        chosen_size="small",
        target_lpa="Test LPA",
        target_nca="Test NCA",
        lpa_neigh=[],
        nca_neigh=[],
        lpa_neigh_norm=[],
        nca_neigh_norm=[],
        backend=backend,
        promoter_discount_type=None,
        promoter_discount_value=None
    )
    
    print("\n" + "="*80)
    print("Test: Felled Woodland Trading WITHOUT Trading Rule")
    print("="*80)
    print(f"\nDemand: {demand_df['habitat_name'].iloc[0]}")
    print(f"Units needed: {demand_df['units_required'].iloc[0]}")
    print(f"\nSupply available: Woodland and forest - Lowland mixed deciduous woodland (10.0 units)")
    print(f"Trading rule configured: ✗ NO")
    print(f"\nOptions found: {len(options)}")
    
    # Without trading rule, High distinctiveness requires exact match
    # So we should get NO options (since only Lowland mixed deciduous supply exists, not Felled supply)
    assert len(options) == 0, "❌ Options found without trading rule - this shouldn't happen for High distinctiveness!"
    
    print("\n✅ TEST PASSED: Without trading rule, Felled woodland cannot use Lowland mixed deciduous supply")
    print("   (This demonstrates why the trading rule is necessary)")
    print("="*80)
    return True


if __name__ == "__main__":
    print("\n" + "="*80)
    print("Testing Felled Woodland / Lowland Mixed Deciduous Trading")
    print("="*80)
    
    # Test 1: Verify trading rule enables the match
    success1 = test_felled_woodland_trading_with_rule()
    
    # Test 2: Verify that without trading rule, they cannot match
    success2 = test_felled_woodland_trading_without_rule()
    
    print("\n" + "="*80)
    if success1 and success2:
        print("✅ ALL TESTS PASSED!")
        print("\nConclusion:")
        print("  The TradingRules table entry is REQUIRED for Felled woodland to trade")
        print("  with Lowland mixed deciduous woodland, because both are High distinctiveness")
        print("  and High distinctiveness requires exact matching by default.")
    else:
        print("❌ SOME TESTS FAILED")
    print("="*80)
    
    exit(0 if (success1 and success2) else 1)
