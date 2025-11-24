"""
Test for LPA/NCA lookup by name functionality.

This test verifies that we can query ArcGIS by LPA/NCA name to get geometry
and then find neighbors, which is needed when users select manual LPA/NCA
without providing an address or postcode.
"""

import optimizer_core

# URLs from optimizer_core
LPA_URL = ("https://services1.arcgis.com/ESMARspQHYMw9BZ9/arcgis/rest/services/"
           "Local_Authority_Districts_December_2024_Boundaries_UK_BFC/FeatureServer/0")
NCA_URL = ("https://services.arcgis.com/JJzESW51TqeY9uat/arcgis/rest/services/"
           "National_Character_Areas_England/FeatureServer/0")


def test_arcgis_name_query_lpa():
    """Test querying LPA by name to get geometry."""
    print("\n=== Testing LPA query by name ===")
    
    # Test with a well-known LPA
    lpa_name = "Westminster"
    print(f"Querying LPA: {lpa_name}")
    
    lpa_feat = optimizer_core.arcgis_name_query(LPA_URL, "LAD24NM", lpa_name)
    
    assert lpa_feat, f"Should find feature for LPA '{lpa_name}'"
    assert "geometry" in lpa_feat, "Feature should have geometry"
    assert "attributes" in lpa_feat, "Feature should have attributes"
    
    # Check that the name matches
    attrs = lpa_feat.get("attributes", {})
    returned_name = attrs.get("LAD24NM", "")
    print(f"Found LPA: {returned_name}")
    assert returned_name == lpa_name, f"Expected '{lpa_name}', got '{returned_name}'"
    
    print("✓ LPA query by name successful")
    return lpa_feat


def test_arcgis_name_query_nca():
    """Test querying NCA by name to get geometry."""
    print("\n=== Testing NCA query by name ===")
    
    # Test with a well-known NCA
    nca_name = "Thames Valley"
    print(f"Querying NCA: {nca_name}")
    
    nca_feat = optimizer_core.arcgis_name_query(NCA_URL, "NCA_Name", nca_name)
    
    assert nca_feat, f"Should find feature for NCA '{nca_name}'"
    assert "geometry" in nca_feat, "Feature should have geometry"
    assert "attributes" in nca_feat, "Feature should have attributes"
    
    # Check that the name matches
    attrs = nca_feat.get("attributes", {})
    returned_name = attrs.get("NCA_Name", "")
    print(f"Found NCA: {returned_name}")
    assert returned_name == nca_name, f"Expected '{nca_name}', got '{returned_name}'"
    
    print("✓ NCA query by name successful")
    return nca_feat


def test_find_lpa_neighbors_from_name():
    """Test finding LPA neighbors using name query."""
    print("\n=== Testing LPA neighbor lookup from name ===")
    
    # Query Westminster LPA
    lpa_name = "Westminster"
    print(f"Finding neighbors for LPA: {lpa_name}")
    
    lpa_feat = optimizer_core.arcgis_name_query(LPA_URL, "LAD24NM", lpa_name)
    assert lpa_feat and lpa_feat.get("geometry"), "Should get LPA geometry"
    
    # Get neighbors using the geometry
    lpa_neighbors = optimizer_core.layer_intersect_names(
        LPA_URL, lpa_feat.get("geometry"), "LAD24NM"
    )
    
    print(f"Found {len(lpa_neighbors)} LPA neighbors:")
    for neighbor in lpa_neighbors[:5]:  # Show first 5
        print(f"  - {neighbor}")
    
    assert isinstance(lpa_neighbors, list), "Should return a list"
    assert len(lpa_neighbors) > 0, "Should find at least one neighbor (itself)"
    assert lpa_name in lpa_neighbors, f"Should include '{lpa_name}' itself"
    
    print(f"✓ Found {len(lpa_neighbors)} LPA neighbors")
    return lpa_neighbors


def test_find_nca_neighbors_from_name():
    """Test finding NCA neighbors using name query."""
    print("\n=== Testing NCA neighbor lookup from name ===")
    
    # Query Thames Valley NCA
    nca_name = "Thames Valley"
    print(f"Finding neighbors for NCA: {nca_name}")
    
    nca_feat = optimizer_core.arcgis_name_query(NCA_URL, "NCA_Name", nca_name)
    assert nca_feat and nca_feat.get("geometry"), "Should get NCA geometry"
    
    # Get neighbors using the geometry
    nca_neighbors = optimizer_core.layer_intersect_names(
        NCA_URL, nca_feat.get("geometry"), "NCA_Name"
    )
    
    print(f"Found {len(nca_neighbors)} NCA neighbors:")
    for neighbor in nca_neighbors[:5]:  # Show first 5
        print(f"  - {neighbor}")
    
    assert isinstance(nca_neighbors, list), "Should return a list"
    assert len(nca_neighbors) > 0, "Should find at least one neighbor (itself)"
    assert nca_name in nca_neighbors, f"Should include '{nca_name}' itself"
    
    print(f"✓ Found {len(nca_neighbors)} NCA neighbors")
    return nca_neighbors


def test_nonexistent_lpa():
    """Test querying for a non-existent LPA."""
    print("\n=== Testing non-existent LPA ===")
    
    fake_lpa = "NonExistentCity12345"
    print(f"Querying fake LPA: {fake_lpa}")
    
    lpa_feat = optimizer_core.arcgis_name_query(LPA_URL, "LAD24NM", fake_lpa)
    
    # Should return empty dict if not found
    assert lpa_feat == {}, f"Should return empty dict for non-existent LPA"
    
    print("✓ Correctly returns empty dict for non-existent LPA")


if __name__ == "__main__":
    print("=" * 60)
    print("Testing LPA/NCA Lookup by Name Functionality")
    print("=" * 60)
    
    try:
        # Run all tests
        test_arcgis_name_query_lpa()
        test_arcgis_name_query_nca()
        test_find_lpa_neighbors_from_name()
        test_find_nca_neighbors_from_name()
        test_nonexistent_lpa()
        
        print("\n" + "=" * 60)
        print("✅ All tests passed!")
        print("=" * 60)
        
    except AssertionError as e:
        print(f"\n❌ Test failed: {e}")
        raise
    except Exception as e:
        print(f"\n❌ Error during test: {e}")
        import traceback
        traceback.print_exc()
        raise
