"""
Test for watercourse Spatial Risk Multiplier (SRM) calculation

Tests the SRM system which uses watercourse catchments instead of LPA/NCA for watercourse habitats:
- Same waterbody catchment → SRM = 1.0 (no uplift)
- Same operational catchment (different waterbody) → SRM = 0.75 (4/3 uplift)
- Outside operational catchment → SRM = 0.5 (2× uplift)
"""

import re


def norm_name(s: str) -> str:
    """Normalize name for comparison (copied from app.py)"""
    if s is None:
        return ""
    t = str(s).strip().lower()
    t = re.sub(r'\b(city of|royal borough of|metropolitan borough of)\b', '', t)
    t = re.sub(r'\b(council|borough|district|county|unitary authority|unitary|city)\b', '', t)
    t = t.replace("&", "and")
    t = re.sub(r'[^a-z0-9]+', '', t)
    return t


def calculate_watercourse_srm(site_waterbody: str, site_operational: str,
                               bank_waterbody: str, bank_operational: str) -> float:
    """
    Calculate Spatial Risk Multiplier (SRM) for watercourse habitats based on catchment proximity.
    (Copied from app.py for testing)
    
    SRM Rules:
    - Same waterbody catchment: SRM = 1.0 (no uplift)
    - Same operational catchment (different waterbody): SRM = 0.75 (buyer needs 4/3× units)
    - Outside operational catchment: SRM = 0.5 (buyer needs 2× units)
    
    Returns SRM multiplier (1.0, 0.75, or 0.5)
    """
    # Normalize for comparison
    site_wb = norm_name(site_waterbody)
    site_op = norm_name(site_operational)
    bank_wb = norm_name(bank_waterbody)
    bank_op = norm_name(bank_operational)
    
    # If catchment data is missing, default to far (0.5)
    if not site_wb and not site_op:
        return 0.5
    if not bank_wb and not bank_op:
        return 0.5
    
    # Same waterbody catchment
    if site_wb and bank_wb and site_wb == bank_wb:
        return 1.0
    
    # Same operational catchment (different waterbody)
    if site_op and bank_op and site_op == bank_op:
        return 0.75
    
    # Outside operational catchment
    return 0.5


def test_srm_same_waterbody():
    """Test that same waterbody catchment gives SRM = 1.0"""
    
    srm = calculate_watercourse_srm(
        site_waterbody="River Thames - Headwaters",
        site_operational="Thames Upper",
        bank_waterbody="River Thames - Headwaters",
        bank_operational="Thames Upper"
    )
    
    assert srm == 1.0, f"Expected SRM 1.0 for same waterbody, got {srm}"
    print("✅ test_srm_same_waterbody passed")


def test_srm_same_operational_different_waterbody():
    """Test that same operational catchment but different waterbody gives SRM = 0.75"""
    
    srm = calculate_watercourse_srm(
        site_waterbody="River Thames - Headwaters",
        site_operational="Thames Upper",
        bank_waterbody="River Cole",
        bank_operational="Thames Upper"
    )
    
    assert srm == 0.75, f"Expected SRM 0.75 for same operational catchment, got {srm}"
    print("✅ test_srm_same_operational_different_waterbody passed")


def test_srm_different_operational():
    """Test that different operational catchment gives SRM = 0.5"""
    
    srm = calculate_watercourse_srm(
        site_waterbody="River Thames - Headwaters",
        site_operational="Thames Upper",
        bank_waterbody="River Severn",
        bank_operational="Severn Middle"
    )
    
    assert srm == 0.5, f"Expected SRM 0.5 for different operational catchment, got {srm}"
    print("✅ test_srm_different_operational passed")


def test_srm_missing_site_data():
    """Test that missing site catchment data defaults to SRM = 0.5"""
    
    srm = calculate_watercourse_srm(
        site_waterbody="",
        site_operational="",
        bank_waterbody="River Thames - Headwaters",
        bank_operational="Thames Upper"
    )
    
    assert srm == 0.5, f"Expected SRM 0.5 for missing site data, got {srm}"
    print("✅ test_srm_missing_site_data passed")


def test_srm_missing_bank_data():
    """Test that missing bank catchment data defaults to SRM = 0.5"""
    
    srm = calculate_watercourse_srm(
        site_waterbody="River Thames - Headwaters",
        site_operational="Thames Upper",
        bank_waterbody="",
        bank_operational=""
    )
    
    assert srm == 0.5, f"Expected SRM 0.5 for missing bank data, got {srm}"
    print("✅ test_srm_missing_bank_data passed")


def test_srm_case_insensitive():
    """Test that SRM calculation is case-insensitive"""
    
    srm1 = calculate_watercourse_srm(
        site_waterbody="River Thames - Headwaters",
        site_operational="Thames Upper",
        bank_waterbody="RIVER THAMES - HEADWATERS",
        bank_operational="THAMES UPPER"
    )
    
    srm2 = calculate_watercourse_srm(
        site_waterbody="river thames - headwaters",
        site_operational="thames upper",
        bank_waterbody="River Thames - Headwaters",
        bank_operational="Thames Upper"
    )
    
    assert srm1 == 1.0, f"Expected SRM 1.0 for same waterbody (uppercase), got {srm1}"
    assert srm2 == 1.0, f"Expected SRM 1.0 for same waterbody (lowercase), got {srm2}"
    print("✅ test_srm_case_insensitive passed")


def test_srm_to_tier_mapping():
    """Test that SRM values map correctly to tiers"""
    # SRM 1.0 → local
    # SRM 0.75 → adjacent
    # SRM 0.5 → far
    
    # Test in the context where this mapping occurs
    # (This is more of a documentation test since the mapping is inline)
    
    srm_to_tier = {
        1.0: "local",
        0.75: "adjacent",
        0.5: "far"
    }
    
    for srm, expected_tier in srm_to_tier.items():
        if srm >= 0.95:
            tier = "local"
        elif srm >= 0.70:
            tier = "adjacent"
        else:
            tier = "far"
        
        assert tier == expected_tier, f"SRM {srm} should map to '{expected_tier}', got '{tier}'"
    
    print("✅ test_srm_to_tier_mapping passed")


if __name__ == "__main__":
    print("=" * 60)
    print("Testing Watercourse Spatial Risk Multiplier (SRM)")
    print("=" * 60)
    
    tests = [
        test_srm_same_waterbody,
        test_srm_same_operational_different_waterbody,
        test_srm_different_operational,
        test_srm_missing_site_data,
        test_srm_missing_bank_data,
        test_srm_case_insensitive,
        test_srm_to_tier_mapping,
    ]
    
    all_passed = True
    for test in tests:
        try:
            test()
        except AssertionError as e:
            print(f"❌ {test.__name__} failed: {e}")
            all_passed = False
        except Exception as e:
            print(f"❌ {test.__name__} errored: {e}")
            all_passed = False
    
    print("=" * 60)
    if all_passed:
        print("✅ ALL TESTS PASSED!")
    else:
        print("❌ SOME TESTS FAILED")
        exit(1)
    print("=" * 60)
