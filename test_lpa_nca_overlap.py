"""
Test for get_lpa_nca_overlap_point function.

This test verifies that when manual LPA/NCA are selected (without postcode),
the function can find a representative point and neighbors for tier calculation.
"""

import json
from unittest.mock import patch, MagicMock
import optimizer_core


def test_get_lpa_nca_overlap_point_success():
    """Test successful case where both LPA and NCA geometries are found."""
    print("\n=== Testing get_lpa_nca_overlap_point with valid LPA/NCA ===")
    
    # Mock LPA geometry (simplified polygon)
    mock_lpa_geometry = {
        "rings": [
            [
                [-0.15, 51.50],  # Westminster area coordinates
                [-0.10, 51.50],
                [-0.10, 51.52],
                [-0.15, 51.52],
                [-0.15, 51.50]
            ]
        ]
    }
    
    # Mock NCA geometry (simplified polygon)
    mock_nca_geometry = {
        "rings": [
            [
                [-0.20, 51.48],  # Thames Valley area
                [-0.05, 51.48],
                [-0.05, 51.54],
                [-0.20, 51.54],
                [-0.20, 51.48]
            ]
        ]
    }
    
    # Mock LPA feature
    mock_lpa_feat = {
        "geometry": mock_lpa_geometry,
        "attributes": {"LAD24NM": "Westminster"}
    }
    
    # Mock NCA feature
    mock_nca_feat = {
        "geometry": mock_nca_geometry,
        "attributes": {"NCA_Name": "Thames Valley"}
    }
    
    # Mock LPA neighbors
    mock_lpa_neighbors = ["Westminster", "Camden", "Kensington and Chelsea"]
    
    # Mock NCA neighbors
    mock_nca_neighbors = ["Thames Valley", "Chilterns"]
    
    with patch.object(optimizer_core, 'arcgis_name_query') as mock_name_query, \
         patch.object(optimizer_core, 'layer_intersect_names') as mock_intersect:
        
        # Setup mock returns
        def name_query_side_effect(url, field, name):
            if "Local_Authority" in url:
                return mock_lpa_feat
            else:  # NCA
                return mock_nca_feat
        
        def intersect_side_effect(url, geom, field):
            if "Local_Authority" in url:
                return mock_lpa_neighbors
            else:  # NCA
                return mock_nca_neighbors
        
        mock_name_query.side_effect = name_query_side_effect
        mock_intersect.side_effect = intersect_side_effect
        
        # Call the function
        lat, lon, lpa_neighbors, nca_neighbors = optimizer_core.get_lpa_nca_overlap_point(
            "Westminster", "Thames Valley"
        )
        
        # Verify results
        assert lat is not None, "Latitude should not be None"
        assert lon is not None, "Longitude should not be None"
        assert isinstance(lat, float), "Latitude should be a float"
        assert isinstance(lon, float), "Longitude should be a float"
        
        # Check that centroid is approximately in the Westminster area
        # The centroid of our mock polygon should be around (-0.125, 51.51)
        assert 51.48 < lat < 51.54, f"Latitude {lat} should be in Westminster range"
        assert -0.20 < lon < -0.05, f"Longitude {lon} should be in Westminster range"
        
        # Verify neighbors are populated
        assert len(lpa_neighbors) > 0, "LPA neighbors should not be empty"
        assert len(nca_neighbors) > 0, "NCA neighbors should not be empty"
        assert "Westminster" in lpa_neighbors, "LPA neighbors should include Westminster"
        assert "Thames Valley" in nca_neighbors, "NCA neighbors should include Thames Valley"
        
        print(f"✓ Found centroid: ({lat:.4f}, {lon:.4f})")
        print(f"✓ LPA neighbors: {lpa_neighbors}")
        print(f"✓ NCA neighbors: {nca_neighbors}")


def test_get_lpa_nca_overlap_point_missing_lpa():
    """Test case where LPA geometry is not found."""
    print("\n=== Testing get_lpa_nca_overlap_point with missing LPA ===")
    
    with patch.object(optimizer_core, 'arcgis_name_query') as mock_name_query:
        # LPA not found
        mock_name_query.return_value = {}
        
        lat, lon, lpa_neighbors, nca_neighbors = optimizer_core.get_lpa_nca_overlap_point(
            "NonExistentLPA", "Thames Valley"
        )
        
        # Should return None values when LPA is not found
        assert lat is None, "Latitude should be None when LPA not found"
        assert lon is None, "Longitude should be None when LPA not found"
        assert lpa_neighbors == [], "LPA neighbors should be empty"
        assert nca_neighbors == [], "NCA neighbors should be empty"
        
        print("✓ Correctly returns None when LPA not found")


def test_get_lpa_nca_overlap_point_missing_nca():
    """Test case where NCA geometry is not found."""
    print("\n=== Testing get_lpa_nca_overlap_point with missing NCA ===")
    
    mock_lpa_feat = {
        "geometry": {"rings": [[[-0.15, 51.50], [-0.10, 51.50], [-0.10, 51.52], [-0.15, 51.50]]]},
        "attributes": {"LAD24NM": "Westminster"}
    }
    
    with patch.object(optimizer_core, 'arcgis_name_query') as mock_name_query:
        def name_query_side_effect(url, field, name):
            if "Local_Authority" in url:
                return mock_lpa_feat
            else:  # NCA - not found
                return {}
        
        mock_name_query.side_effect = name_query_side_effect
        
        lat, lon, lpa_neighbors, nca_neighbors = optimizer_core.get_lpa_nca_overlap_point(
            "Westminster", "NonExistentNCA"
        )
        
        # Should return None values when NCA is not found
        assert lat is None, "Latitude should be None when NCA not found"
        assert lon is None, "Longitude should be None when NCA not found"
        assert lpa_neighbors == [], "LPA neighbors should be empty"
        assert nca_neighbors == [], "NCA neighbors should be empty"
        
        print("✓ Correctly returns None when NCA not found")


def test_get_lpa_nca_overlap_point_empty_geometry():
    """Test case where geometry has no rings."""
    print("\n=== Testing get_lpa_nca_overlap_point with empty geometry ===")
    
    mock_lpa_feat = {
        "geometry": {"rings": []},  # Empty rings
        "attributes": {"LAD24NM": "Westminster"}
    }
    
    mock_nca_feat = {
        "geometry": {"rings": [[[-0.20, 51.48], [-0.05, 51.48], [-0.05, 51.54], [-0.20, 51.48]]]},
        "attributes": {"NCA_Name": "Thames Valley"}
    }
    
    with patch.object(optimizer_core, 'arcgis_name_query') as mock_name_query, \
         patch.object(optimizer_core, 'layer_intersect_names') as mock_intersect:
        
        def name_query_side_effect(url, field, name):
            if "Local_Authority" in url:
                return mock_lpa_feat
            else:  # NCA
                return mock_nca_feat
        
        mock_name_query.side_effect = name_query_side_effect
        mock_intersect.return_value = ["test"]
        
        lat, lon, lpa_neighbors, nca_neighbors = optimizer_core.get_lpa_nca_overlap_point(
            "Westminster", "Thames Valley"
        )
        
        # Should return None lat/lon when geometry is empty
        assert lat is None, "Latitude should be None when geometry is empty"
        assert lon is None, "Longitude should be None when geometry is empty"
        # But neighbors might still be populated
        
        print("✓ Correctly handles empty geometry")


if __name__ == "__main__":
    print("=" * 60)
    print("Testing get_lpa_nca_overlap_point Functionality")
    print("=" * 60)
    
    try:
        # Run all tests
        test_get_lpa_nca_overlap_point_success()
        test_get_lpa_nca_overlap_point_missing_lpa()
        test_get_lpa_nca_overlap_point_missing_nca()
        test_get_lpa_nca_overlap_point_empty_geometry()
        
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
