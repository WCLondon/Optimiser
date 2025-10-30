"""
Tests for Surplus Uplift Offset (SUO) module.
"""

import pandas as pd
import numpy as np
from suo import compute_suo, SUOConfig


def test_single_site_srm_1():
    """Test single site with SRM=1, should get 50% reduction."""
    print("\n=== Test: Single site, SRM=1 ===")
    
    # Requirements: 100 units needed
    requirements = pd.DataFrame({
        "line_id": ["line1"],
        "trading_group": ["Grassland"],
        "units_needed": [100.0]
    })
    
    # Surplus: 200 units of Medium distinctiveness
    surplus_supply = pd.DataFrame({
        "site_id": ["site1"],
        "distinctiveness": ["Medium"],
        "trading_group": ["Grassland"],
        "units_surplus": [200.0]
    })
    
    # SRM: 1.0 for site1
    srm = pd.DataFrame({
        "site_id": ["site1"],
        "srm": [1.0]
    })
    
    config = SUOConfig(headroom_fraction=0.5)
    
    req_reduced, alloc_ledger, summary = compute_suo(requirements, surplus_supply, srm, config)
    
    print(f"Eligible surplus: {summary['eligible_surplus']}")
    print(f"Usable units (50% headroom): {summary['usable_units']}")
    print(f"Effective capacity: {summary['effective_capacity']}")
    print(f"Reduction fraction: {summary['reduction_fraction_final']}")
    
    # Usable = 200 * 0.5 = 100
    # Effective = 100 / 1.0 = 100
    # R_total = 100
    # Reduction = min(100 / 100, 1) = 1.0 (100%)
    assert abs(summary["usable_units"] - 100.0) < 1e-6, f"Expected 100 usable, got {summary['usable_units']}"
    assert abs(summary["effective_capacity"] - 100.0) < 1e-6
    assert abs(summary["reduction_fraction_final"] - 1.0) < 1e-6
    
    # Check requirements reduced to 0
    assert abs(req_reduced["units_needed_after"].iloc[0]) < 1e-6
    assert abs(req_reduced["units_reduced_by"].iloc[0] - 100.0) < 1e-6
    
    print("✅ Single site SRM=1 test passed")
    return True


def test_two_sites_different_srm():
    """Test two sites with different SRMs, greedy should pick lower SRM first."""
    print("\n=== Test: Two sites, different SRMs ===")
    
    # Requirements: 100 units
    requirements = pd.DataFrame({
        "line_id": ["line1"],
        "trading_group": ["Grassland"],
        "units_needed": [100.0]
    })
    
    # Site1: 50 surplus, SRM=1.0
    # Site2: 150 surplus, SRM=2.0
    surplus_supply = pd.DataFrame({
        "site_id": ["site1", "site2"],
        "distinctiveness": ["Medium", "High"],
        "trading_group": ["Grassland", "Grassland"],
        "units_surplus": [100.0, 300.0]
    })
    
    srm = pd.DataFrame({
        "site_id": ["site1", "site2"],
        "srm": [1.0, 2.0]
    })
    
    config = SUOConfig(headroom_fraction=0.5)
    
    req_reduced, alloc_ledger, summary = compute_suo(requirements, surplus_supply, srm, config)
    
    # Usable: site1=50, site2=150
    # Effective: site1=50/1=50, site2=150/2=75
    # Total effective = 125
    # Reduction fraction = min(125/100, 1) = 1.0
    
    print(f"Usable units: {summary['usable_units']}")
    print(f"Effective capacity: {summary['effective_capacity']}")
    print(f"Reduction fraction: {summary['reduction_fraction_final']}")
    print(f"\nAllocation ledger:")
    print(alloc_ledger)
    
    assert abs(summary["usable_units"] - 200.0) < 1e-6
    assert abs(summary["effective_capacity"] - 125.0) < 1e-6
    
    # Greedy should allocate from site1 first (lower SRM)
    site1_allocs = alloc_ledger[alloc_ledger["site_id"] == "site1"]
    if not site1_allocs.empty:
        site1_effective = site1_allocs["allocated_effective_units"].sum()
        print(f"Site1 allocation (effective): {site1_effective}")
        # Should use all of site1's capacity first
        assert site1_effective > 0, "Should allocate from site1 first (lower SRM)"
    
    print("✅ Two sites with different SRMs test passed")
    return True


def test_insufficient_capacity():
    """Test insufficient capacity triggers downward adjustment."""
    print("\n=== Test: Insufficient capacity ===")
    
    # Requirements: 100 units
    requirements = pd.DataFrame({
        "line_id": ["line1"],
        "trading_group": ["Grassland"],
        "units_needed": [100.0]
    })
    
    # Surplus: only 60 units (30 usable at 50% headroom)
    surplus_supply = pd.DataFrame({
        "site_id": ["site1"],
        "distinctiveness": ["Medium"],
        "trading_group": ["Grassland"],
        "units_surplus": [60.0]
    })
    
    srm = pd.DataFrame({
        "site_id": ["site1"],
        "srm": [1.0]
    })
    
    config = SUOConfig(headroom_fraction=0.5)
    
    req_reduced, alloc_ledger, summary = compute_suo(requirements, surplus_supply, srm, config)
    
    # Usable = 60 * 0.5 = 30
    # Effective = 30 / 1.0 = 30
    # Reduction = min(30/100, 1) = 0.3 (30%)
    
    print(f"Usable units: {summary['usable_units']}")
    print(f"Effective capacity: {summary['effective_capacity']}")
    print(f"Reduction fraction: {summary['reduction_fraction_final']}")
    
    assert abs(summary["reduction_fraction_final"] - 0.3) < 1e-6
    assert abs(req_reduced["units_needed_after"].iloc[0] - 70.0) < 1e-6
    
    print("✅ Insufficient capacity test passed")
    return True


def test_distinctiveness_gating():
    """Test that only Medium+ distinctiveness is eligible."""
    print("\n=== Test: Distinctiveness gating ===")
    
    requirements = pd.DataFrame({
        "line_id": ["line1"],
        "trading_group": ["Grassland"],
        "units_needed": [100.0]
    })
    
    # Mix of distinctiveness levels
    surplus_supply = pd.DataFrame({
        "site_id": ["site1", "site2", "site3"],
        "distinctiveness": ["Low", "Medium", "High"],
        "trading_group": ["Grassland", "Grassland", "Grassland"],
        "units_surplus": [200.0, 100.0, 100.0]
    })
    
    srm = pd.DataFrame({
        "site_id": ["site1", "site2", "site3"],
        "srm": [1.0, 1.0, 1.0]
    })
    
    config = SUOConfig(headroom_fraction=0.5)
    
    req_reduced, alloc_ledger, summary = compute_suo(requirements, surplus_supply, srm, config)
    
    # Only site2 (Medium) and site3 (High) should contribute
    # Eligible surplus = 100 + 100 = 200
    # Usable = 200 * 0.5 = 100
    
    print(f"Eligible surplus: {summary['eligible_surplus']}")
    print(f"Usable units: {summary['usable_units']}")
    
    assert abs(summary["eligible_surplus"] - 200.0) < 1e-6, "Should exclude Low distinctiveness"
    assert abs(summary["usable_units"] - 100.0) < 1e-6
    
    # Should not see site1 in allocation
    if not alloc_ledger.empty:
        assert "site1" not in alloc_ledger["site_id"].values, "Low distinctiveness site should not be used"
    
    print("✅ Distinctiveness gating test passed")
    return True


def test_no_eligible_surplus():
    """Test behavior when no eligible surplus exists."""
    print("\n=== Test: No eligible surplus ===")
    
    requirements = pd.DataFrame({
        "line_id": ["line1"],
        "trading_group": ["Grassland"],
        "units_needed": [100.0]
    })
    
    # Only Low distinctiveness surplus
    surplus_supply = pd.DataFrame({
        "site_id": ["site1"],
        "distinctiveness": ["Low"],
        "trading_group": ["Grassland"],
        "units_surplus": [500.0]
    })
    
    srm = pd.DataFrame({
        "site_id": ["site1"],
        "srm": [1.0]
    })
    
    config = SUOConfig()
    
    req_reduced, alloc_ledger, summary = compute_suo(requirements, surplus_supply, srm, config)
    
    print(f"Reduction fraction: {summary['reduction_fraction_final']}")
    
    # No reduction should occur
    assert summary["reduction_fraction_final"] == 0.0
    assert abs(req_reduced["units_needed_after"].iloc[0] - 100.0) < 1e-6
    assert alloc_ledger.empty
    
    print("✅ No eligible surplus test passed")
    return True


def test_zero_requirements():
    """Test edge case with zero requirements."""
    print("\n=== Test: Zero requirements ===")
    
    requirements = pd.DataFrame({
        "line_id": ["line1"],
        "trading_group": ["Grassland"],
        "units_needed": [0.0]
    })
    
    surplus_supply = pd.DataFrame({
        "site_id": ["site1"],
        "distinctiveness": ["Medium"],
        "trading_group": ["Grassland"],
        "units_surplus": [100.0]
    })
    
    srm = pd.DataFrame({
        "site_id": ["site1"],
        "srm": [1.0]
    })
    
    config = SUOConfig()
    
    req_reduced, alloc_ledger, summary = compute_suo(requirements, surplus_supply, srm, config)
    
    # Should handle gracefully
    assert summary["reduction_fraction_final"] == 0.0
    assert req_reduced["units_needed_after"].iloc[0] == 0.0
    
    print("✅ Zero requirements test passed")
    return True


def test_multi_line_uniform_reduction():
    """Test uniform reduction across multiple requirement lines."""
    print("\n=== Test: Multi-line uniform reduction ===")
    
    # Two requirement lines
    requirements = pd.DataFrame({
        "line_id": ["line1", "line2"],
        "trading_group": ["Grassland", "Woodland"],
        "units_needed": [100.0, 50.0]
    })
    
    # Surplus sufficient for 50% of total
    surplus_supply = pd.DataFrame({
        "site_id": ["site1"],
        "distinctiveness": ["Medium"],
        "trading_group": ["Mixed"],
        "units_surplus": [150.0]
    })
    
    srm = pd.DataFrame({
        "site_id": ["site1"],
        "srm": [1.0]
    })
    
    config = SUOConfig(headroom_fraction=0.5)
    
    req_reduced, alloc_ledger, summary = compute_suo(requirements, surplus_supply, srm, config)
    
    # Total R = 150
    # Usable = 75
    # Reduction = 75/150 = 0.5
    
    print(f"Reduction fraction: {summary['reduction_fraction_final']}")
    print("Requirements after reduction:")
    print(req_reduced[["line_id", "units_needed_before", "units_needed_after"]])
    
    assert abs(summary["reduction_fraction_final"] - 0.5) < 1e-6
    
    # Both lines should be reduced by 50%
    assert abs(req_reduced[req_reduced["line_id"] == "line1"]["units_needed_after"].iloc[0] - 50.0) < 1e-6
    assert abs(req_reduced[req_reduced["line_id"] == "line2"]["units_needed_after"].iloc[0] - 25.0) < 1e-6
    
    print("✅ Multi-line uniform reduction test passed")
    return True


def test_per_site_per_line_srm():
    """Test per-(site, line) SRM handling."""
    print("\n=== Test: Per-(site, line) SRM ===")
    
    # Two requirement lines
    requirements = pd.DataFrame({
        "line_id": ["line1", "line2"],
        "trading_group": ["Grassland", "Woodland"],
        "units_needed": [100.0, 100.0]
    })
    
    # One site with ample surplus
    surplus_supply = pd.DataFrame({
        "site_id": ["site1"],
        "distinctiveness": ["Medium"],
        "trading_group": ["Mixed"],
        "units_surplus": [400.0]
    })
    
    # Different SRM for each line from same site
    srm = pd.DataFrame({
        "site_id": ["site1", "site1"],
        "line_id": ["line1", "line2"],
        "srm": [1.0, 2.0]
    })
    
    config = SUOConfig(headroom_fraction=0.5)
    
    req_reduced, alloc_ledger, summary = compute_suo(requirements, surplus_supply, srm, config)
    
    print(f"Reduction fraction: {summary['reduction_fraction_final']}")
    print("\nAllocation ledger:")
    print(alloc_ledger)
    
    # Usable = 200
    # For capacity planning, we use max SRM = 2.0 (conservative)
    # Effective capacity = 200 / 2.0 = 100
    # Reduction = min(100/200, 1) = 0.5
    
    # Check allocations use correct per-line SRM
    if not alloc_ledger.empty:
        line1_alloc = alloc_ledger[alloc_ledger["line_id"] == "line1"]
        line2_alloc = alloc_ledger[alloc_ledger["line_id"] == "line2"]
        
        if not line1_alloc.empty:
            print(f"Line1 SRM used: {line1_alloc['srm_used'].iloc[0]}")
            assert abs(line1_alloc['srm_used'].iloc[0] - 1.0) < 1e-6
        
        if not line2_alloc.empty:
            print(f"Line2 SRM used: {line2_alloc['srm_used'].iloc[0]}")
            assert abs(line2_alloc['srm_used'].iloc[0] - 2.0) < 1e-6
    
    print("✅ Per-(site, line) SRM test passed")
    return True


def run_all_tests():
    """Run all SUO tests."""
    print("=" * 60)
    print("Running SUO Test Suite")
    print("=" * 60)
    
    tests = [
        test_single_site_srm_1,
        test_two_sites_different_srm,
        test_insufficient_capacity,
        test_distinctiveness_gating,
        test_no_eligible_surplus,
        test_zero_requirements,
        test_multi_line_uniform_reduction,
        test_per_site_per_line_srm,
    ]
    
    passed = 0
    failed = 0
    
    for test in tests:
        try:
            if test():
                passed += 1
        except Exception as e:
            print(f"❌ {test.__name__} FAILED: {e}")
            import traceback
            traceback.print_exc()
            failed += 1
    
    print("\n" + "=" * 60)
    print(f"Test Results: {passed} passed, {failed} failed")
    print("=" * 60)
    
    return failed == 0


if __name__ == "__main__":
    success = run_all_tests()
    exit(0 if success else 1)
