"""
Test that area habitats, hedgerow habitats, and watercourse habitats
remain in separate ledgers and cannot cross-trade.
"""

import pandas as pd
from optimizer_core import (
    prepare_options, prepare_hedgerow_options, prepare_watercourse_options,
    is_hedgerow, is_watercourse, build_dist_levels_map
)


def create_mock_backend():
    """Create a mock backend with area, hedgerow, and watercourse habitats"""
    
    # Create catalog with all three types of habitats
    catalog_data = [
        # Area habitats
        {"habitat_name": "Modified grassland", "broader_type": "Grassland", 
         "distinctiveness_name": "Low", "UmbrellaType": "area"},
        {"habitat_name": "Grassland - Traditional Orchard", "broader_type": "Grassland",
         "distinctiveness_name": "Medium", "UmbrellaType": "area"},
        {"habitat_name": "Mixed scrub", "broader_type": "Heathland and shrub",
         "distinctiveness_name": "Medium", "UmbrellaType": "area"},
        
        # Hedgerow habitats
        {"habitat_name": "Hedgerow - Native species-rich", "broader_type": "Hedgerow",
         "distinctiveness_name": "Medium", "UmbrellaType": "hedgerow"},
        {"habitat_name": "Hedgerow - Native species-poor", "broader_type": "Hedgerow",
         "distinctiveness_name": "Low", "UmbrellaType": "hedgerow"},
        
        # Watercourse habitats  
        {"habitat_name": "Ditch", "broader_type": "Rivers and streams",
         "distinctiveness_name": "Low", "UmbrellaType": "watercourse"},
        {"habitat_name": "River - naturally functioning", "broader_type": "Rivers and streams",
         "distinctiveness_name": "High", "UmbrellaType": "watercourse"},
    ]
    catalog_df = pd.DataFrame(catalog_data)
    
    # Create banks
    banks_data = [
        {"bank_id": "B001", "bank_name": "Test Bank 1", "BANK_KEY": "TEST_BANK_1",
         "lpa_name": "Test LPA", "nca_name": "Test NCA", 
         "lat": 51.5, "lon": -0.1, "postcode": "SW1A 1AA", "address": "Test Address"},
    ]
    banks_df = pd.DataFrame(banks_data)
    
    # Create stock with all three types
    stock_data = [
        # Area habitat stock
        {"stock_id": "S001", "bank_id": "B001", "BANK_KEY": "TEST_BANK_1", 
         "habitat_name": "Modified grassland", "quantity_available": 10.0, 
         "bank_name": "Test Bank 1"},
        {"stock_id": "S002", "bank_id": "B001", "BANK_KEY": "TEST_BANK_1",
         "habitat_name": "Grassland - Traditional Orchard", "quantity_available": 5.0,
         "bank_name": "Test Bank 1"},
        {"stock_id": "S003", "bank_id": "B001", "BANK_KEY": "TEST_BANK_1",
         "habitat_name": "Mixed scrub", "quantity_available": 8.0,
         "bank_name": "Test Bank 1"},
        
        # Hedgerow stock
        {"stock_id": "S004", "bank_id": "B001", "BANK_KEY": "TEST_BANK_1",
         "habitat_name": "Hedgerow - Native species-rich", "quantity_available": 15.0,
         "bank_name": "Test Bank 1"},
        {"stock_id": "S005", "bank_id": "B001", "BANK_KEY": "TEST_BANK_1",
         "habitat_name": "Hedgerow - Native species-poor", "quantity_available": 20.0,
         "bank_name": "Test Bank 1"},
        
        # Watercourse stock
        {"stock_id": "S006", "bank_id": "B001", "BANK_KEY": "TEST_BANK_1",
         "habitat_name": "Ditch", "quantity_available": 12.0,
         "bank_name": "Test Bank 1"},
        {"stock_id": "S007", "bank_id": "B001", "BANK_KEY": "TEST_BANK_1",
         "habitat_name": "River - naturally functioning", "quantity_available": 6.0,
         "bank_name": "Test Bank 1"},
    ]
    stock_df = pd.DataFrame(stock_data)
    
    # Create pricing for all habitats
    pricing_data = []
    for habitat in catalog_data:
        for tier in ["local", "adjacent", "far"]:
            pricing_data.append({
                "habitat_name": habitat["habitat_name"],
                "contract_size": "small",
                "tier": tier,
                "bank_id": "B001",
                "BANK_KEY": "TEST_BANK_1",
                "price": 10000.0,
                "broader_type": habitat["broader_type"],
                "distinctiveness_name": habitat["distinctiveness_name"],
                "bank_name": "Test Bank 1"
            })
    pricing_df = pd.DataFrame(pricing_data)
    
    # Create distinctiveness levels
    dist_levels_data = [
        {"distinctiveness_name": "Low", "level_value": 1},
        {"distinctiveness_name": "Medium", "level_value": 2},
        {"distinctiveness_name": "High", "level_value": 3},
        {"distinctiveness_name": "Very High", "level_value": 4},
    ]
    dist_levels_df = pd.DataFrame(dist_levels_data)
    
    return {
        "HabitatCatalog": catalog_df,
        "Banks": banks_df,
        "Stock": stock_df,
        "Pricing": pricing_df,
        "DistinctivenessLevels": dist_levels_df,
        "TradingRules": pd.DataFrame(),  # Empty trading rules
    }


def test_area_ledger_excludes_hedgerows_and_watercourses():
    """Test that prepare_options (area) excludes hedgerows and watercourses"""
    print("\n" + "="*80)
    print("Test: Area ledger excludes hedgerows and watercourses")
    print("="*80)
    
    backend = create_mock_backend()
    
    # Create demand for area habitat
    demand_df = pd.DataFrame([
        {"habitat_name": "Modified grassland", "units_required": 2.0}
    ])
    
    options, caps, bk = prepare_options(
        demand_df=demand_df,
        chosen_size="small",
        target_lpa="Test LPA",
        target_nca="Test NCA",
        lpa_neigh=[],
        nca_neigh=[],
        lpa_neigh_norm=[],
        nca_neigh_norm=[],
        backend=backend
    )
    
    # Check that no options use hedgerow or watercourse supply
    hedgerow_options = [opt for opt in options if is_hedgerow(opt["supply_habitat"])]
    watercourse_options = [opt for opt in options if is_watercourse(opt["supply_habitat"])]
    
    if hedgerow_options:
        print(f"\n❌ FAIL: Found {len(hedgerow_options)} hedgerow options in area ledger:")
        for opt in hedgerow_options:
            print(f"  - {opt['supply_habitat']}")
        return False
    
    if watercourse_options:
        print(f"\n❌ FAIL: Found {len(watercourse_options)} watercourse options in area ledger:")
        for opt in watercourse_options:
            print(f"  - {opt['supply_habitat']}")
        return False
    
    print(f"\n✅ PASS: Area ledger has {len(options)} options, none are hedgerows or watercourses")
    for opt in options[:3]:  # Show first 3
        print(f"  - {opt['supply_habitat']}")
    
    return True


def test_hedgerow_ledger_excludes_area_and_watercourses():
    """Test that prepare_hedgerow_options excludes area and watercourse habitats"""
    print("\n" + "="*80)
    print("Test: Hedgerow ledger excludes area and watercourse habitats")
    print("="*80)
    
    backend = create_mock_backend()
    
    # Create demand for hedgerow habitat
    demand_df = pd.DataFrame([
        {"habitat_name": "Hedgerow - Native species-rich", "units_required": 3.0}
    ])
    
    options, caps, bk = prepare_hedgerow_options(
        demand_df=demand_df,
        chosen_size="small",
        target_lpa="Test LPA",
        target_nca="Test NCA",
        lpa_neigh=[],
        nca_neigh=[],
        lpa_neigh_norm=[],
        nca_neigh_norm=[],
        backend=backend
    )
    
    # Check that no options use area or watercourse supply
    area_options = [opt for opt in options 
                   if not is_hedgerow(opt["supply_habitat"]) 
                   and not is_watercourse(opt["supply_habitat"])]
    watercourse_options = [opt for opt in options if is_watercourse(opt["supply_habitat"])]
    
    if area_options:
        print(f"\n❌ FAIL: Found {len(area_options)} area habitat options in hedgerow ledger:")
        for opt in area_options:
            print(f"  - {opt['supply_habitat']}")
        return False
    
    if watercourse_options:
        print(f"\n❌ FAIL: Found {len(watercourse_options)} watercourse options in hedgerow ledger:")
        for opt in watercourse_options:
            print(f"  - {opt['supply_habitat']}")
        return False
    
    print(f"\n✅ PASS: Hedgerow ledger has {len(options)} options, all are hedgerows")
    for opt in options[:3]:  # Show first 3
        print(f"  - {opt['supply_habitat']}")
    
    return True


def test_watercourse_ledger_excludes_area_and_hedgerows():
    """Test that prepare_watercourse_options excludes area and hedgerow habitats"""
    print("\n" + "="*80)
    print("Test: Watercourse ledger excludes area and hedgerow habitats")
    print("="*80)
    
    backend = create_mock_backend()
    
    # Create demand for watercourse habitat
    demand_df = pd.DataFrame([
        {"habitat_name": "Ditch", "units_required": 1.5}
    ])
    
    options, caps, bk = prepare_watercourse_options(
        demand_df=demand_df,
        chosen_size="small",
        target_lpa="Test LPA",
        target_nca="Test NCA",
        lpa_neigh=[],
        nca_neigh=[],
        lpa_neigh_norm=[],
        nca_neigh_norm=[],
        backend=backend
    )
    
    # Check that no options use area or hedgerow supply
    area_options = [opt for opt in options 
                   if not is_hedgerow(opt["supply_habitat"]) 
                   and not is_watercourse(opt["supply_habitat"])]
    hedgerow_options = [opt for opt in options if is_hedgerow(opt["supply_habitat"])]
    
    if area_options:
        print(f"\n❌ FAIL: Found {len(area_options)} area habitat options in watercourse ledger:")
        for opt in area_options:
            print(f"  - {opt['supply_habitat']}")
        return False
    
    if hedgerow_options:
        print(f"\n❌ FAIL: Found {len(hedgerow_options)} hedgerow options in watercourse ledger:")
        for opt in hedgerow_options:
            print(f"  - {opt['supply_habitat']}")
        return False
    
    print(f"\n✅ PASS: Watercourse ledger has {len(options)} options, all are watercourses")
    for opt in options[:3]:  # Show first 3
        print(f"  - {opt['supply_habitat']}")
    
    return True


def test_cross_ledger_demand():
    """Test that cross-ledger demands are properly filtered"""
    print("\n" + "="*80)
    print("Test: Cross-ledger demands are properly filtered")
    print("="*80)
    
    backend = create_mock_backend()
    
    # Create mixed demand (all three types)
    demand_df = pd.DataFrame([
        {"habitat_name": "Modified grassland", "units_required": 2.0},
        {"habitat_name": "Hedgerow - Native species-rich", "units_required": 3.0},
        {"habitat_name": "Ditch", "units_required": 1.5}
    ])
    
    # Test area options - should only process grassland demand (index 0)
    area_options, _, _ = prepare_options(
        demand_df=demand_df, chosen_size="small",
        target_lpa="Test LPA", target_nca="Test NCA",
        lpa_neigh=[], nca_neigh=[], lpa_neigh_norm=[], nca_neigh_norm=[],
        backend=backend
    )
    
    # Check that area options don't include hedgerow or watercourse supply
    area_hedgerow_supply = [opt for opt in area_options if is_hedgerow(opt["supply_habitat"])]
    area_watercourse_supply = [opt for opt in area_options if is_watercourse(opt["supply_habitat"])]
    
    if area_hedgerow_supply:
        print(f"\n❌ FAIL: Area ledger has hedgerow supply options")
        return False
    if area_watercourse_supply:
        print(f"\n❌ FAIL: Area ledger has watercourse supply options")
        return False
    
    # Test hedgerow options - should only process hedgerow demand (index 1)
    hedge_options, _, _ = prepare_hedgerow_options(
        demand_df=demand_df, chosen_size="small",
        target_lpa="Test LPA", target_nca="Test NCA",
        lpa_neigh=[], nca_neigh=[], lpa_neigh_norm=[], nca_neigh_norm=[],
        backend=backend
    )
    
    # Check that hedgerow options don't include area or watercourse supply
    hedge_area_supply = [opt for opt in hedge_options 
                        if not is_hedgerow(opt["supply_habitat"]) 
                        and not is_watercourse(opt["supply_habitat"])]
    hedge_watercourse_supply = [opt for opt in hedge_options if is_watercourse(opt["supply_habitat"])]
    
    if hedge_area_supply:
        print(f"\n❌ FAIL: Hedgerow ledger has area habitat supply options")
        return False
    if hedge_watercourse_supply:
        print(f"\n❌ FAIL: Hedgerow ledger has watercourse supply options")
        return False
    
    # Test watercourse options - should only process watercourse demand (index 2)
    water_options, _, _ = prepare_watercourse_options(
        demand_df=demand_df, chosen_size="small",
        target_lpa="Test LPA", target_nca="Test NCA",
        lpa_neigh=[], nca_neigh=[], lpa_neigh_norm=[], nca_neigh_norm=[],
        backend=backend
    )
    
    # Check that watercourse options don't include area or hedgerow supply
    water_area_supply = [opt for opt in water_options 
                        if not is_hedgerow(opt["supply_habitat"]) 
                        and not is_watercourse(opt["supply_habitat"])]
    water_hedgerow_supply = [opt for opt in water_options if is_hedgerow(opt["supply_habitat"])]
    
    if water_area_supply:
        print(f"\n❌ FAIL: Watercourse ledger has area habitat supply options")
        return False
    if water_hedgerow_supply:
        print(f"\n❌ FAIL: Watercourse ledger has hedgerow supply options")
        return False
    
    print("\n✅ PASS: All ledgers correctly filtered supplies (no cross-ledger trading)")
    print(f"  - Area options: {len(area_options)} (no hedgerow or watercourse supply)")
    print(f"  - Hedgerow options: {len(hedge_options)} (no area or watercourse supply)")
    print(f"  - Watercourse options: {len(water_options)} (no area or hedgerow supply)")
    
    return True


if __name__ == "__main__":
    print("\n" + "="*80)
    print("LEDGER SEPARATION TESTS")
    print("="*80)
    
    tests = [
        ("Area excludes hedgerows/watercourses", test_area_ledger_excludes_hedgerows_and_watercourses),
        ("Hedgerow excludes area/watercourses", test_hedgerow_ledger_excludes_area_and_watercourses),
        ("Watercourse excludes area/hedgerows", test_watercourse_ledger_excludes_area_and_hedgerows),
        ("Cross-ledger demand filtering", test_cross_ledger_demand),
    ]
    
    results = []
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"\n❌ EXCEPTION in {test_name}: {e}")
            import traceback
            traceback.print_exc()
            results.append((test_name, False))
    
    print("\n" + "="*80)
    print("SUMMARY")
    print("="*80)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status}: {test_name}")
    
    print(f"\nTotal: {passed}/{total} tests passed")
    print("="*80)
    
    exit(0 if passed == total else 1)
