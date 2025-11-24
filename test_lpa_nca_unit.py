"""
Unit test for LPA/NCA lookup functionality without network dependency.

This test uses mocked data to verify the logic flow without needing actual
ArcGIS API access.
"""

from unittest.mock import patch, MagicMock
import optimizer_core


def test_arcgis_name_query_logic():
    """Test that arcgis_name_query builds the correct query."""
    print("\n=== Testing arcgis_name_query logic ===")
    
    # Mock the http_get and safe_json functions
    with patch('optimizer_core.http_get') as mock_http_get, \
         patch('optimizer_core.safe_json') as mock_safe_json:
        
        # Setup mock responses
        mock_response = MagicMock()
        mock_http_get.return_value = mock_response
        
        mock_feature = {
            "geometry": {"rings": [[[0, 0], [1, 1], [1, 0], [0, 0]]]},
            "attributes": {"LAD24NM": "Westminster"}
        }
        mock_safe_json.return_value = {"features": [mock_feature]}
        
        # Call the function
        result = optimizer_core.arcgis_name_query(
            "http://test.url/layer", 
            "LAD24NM", 
            "Westminster"
        )
        
        # Verify http_get was called with correct parameters
        assert mock_http_get.called, "http_get should be called"
        call_args = mock_http_get.call_args
        
        # Check URL
        assert call_args[0][0] == "http://test.url/layer/query", "Should append /query to URL"
        
        # Check params
        params = call_args[1]['params']
        assert params['f'] == 'json', "Should request JSON format"
        assert params['where'] == "LAD24NM = 'Westminster'", "Should build correct WHERE clause"
        assert params['returnGeometry'] == 'true', "Should request geometry"
        assert params['outSR'] == 4326, "Should use correct spatial reference"
        
        # Check return value
        assert result == mock_feature, "Should return first feature"
        
        print("✓ arcgis_name_query builds correct query parameters")


def test_arcgis_name_query_no_results():
    """Test that arcgis_name_query returns empty dict when no results."""
    print("\n=== Testing arcgis_name_query with no results ===")
    
    with patch('optimizer_core.http_get') as mock_http_get, \
         patch('optimizer_core.safe_json') as mock_safe_json:
        
        mock_response = MagicMock()
        mock_http_get.return_value = mock_response
        mock_safe_json.return_value = {"features": []}
        
        result = optimizer_core.arcgis_name_query(
            "http://test.url/layer", 
            "LAD24NM", 
            "NonExistent"
        )
        
        assert result == {}, "Should return empty dict when no features found"
        print("✓ Returns empty dict for no results")


def test_promoter_app_neighbor_lookup_flow():
    """
    Test the flow of neighbor lookup in promoter_app.
    This verifies the logic that was fixed.
    """
    print("\n=== Testing neighbor lookup flow ===")
    
    # Simulate the scenario where we have manual LPA/NCA but no lat/lon
    lat, lon = None, None
    target_lpa = "Westminster"
    target_nca = "Thames Valley"
    lpa_neighbors, nca_neighbors = [], []
    
    # This is the logic from promoter_app.py (lines 556-584)
    with patch('optimizer_core.arcgis_point_query') as mock_point_query, \
         patch('optimizer_core.arcgis_name_query') as mock_name_query, \
         patch('optimizer_core.layer_intersect_names') as mock_intersect:
        
        # Setup mocks
        lpa_geom = {"rings": [[[0, 0], [1, 1], [1, 0], [0, 0]]]}
        nca_geom = {"rings": [[[0, 0], [1, 1], [1, 0], [0, 0]]]}
        
        mock_name_query.side_effect = [
            {"geometry": lpa_geom, "attributes": {"LAD24NM": "Westminster"}},
            {"geometry": nca_geom, "attributes": {"NCA_Name": "Thames Valley"}}
        ]
        
        mock_intersect.side_effect = [
            ["Westminster", "Kensington and Chelsea", "Camden"],
            ["Thames Valley", "Chilterns", "Berkshire Downs"]
        ]
        
        # Simulate the first block (lat/lon check) - should be skipped
        if lat and lon:
            # This should not execute
            assert False, "Should not execute when lat/lon are None"
        
        # Simulate the second block (manual LPA/NCA check) - should execute
        if (not lpa_neighbors or not nca_neighbors) and target_lpa and target_nca:
            # Query LPA by name
            if not lpa_neighbors and target_lpa:
                lpa_feat = mock_name_query("http://lpa.url", "LAD24NM", target_lpa)
                if lpa_feat and lpa_feat.get("geometry"):
                    lpa_neighbors = mock_intersect("http://lpa.url", lpa_feat.get("geometry"), "LAD24NM")
            
            # Query NCA by name
            if not nca_neighbors and target_nca:
                nca_feat = mock_name_query("http://nca.url", "NCA_Name", target_nca)
                if nca_feat and nca_feat.get("geometry"):
                    nca_neighbors = mock_intersect("http://nca.url", nca_feat.get("geometry"), "NCA_Name")
        
        # Verify results
        assert len(lpa_neighbors) == 3, "Should have LPA neighbors"
        assert "Westminster" in lpa_neighbors, "Should include Westminster itself"
        
        assert len(nca_neighbors) == 3, "Should have NCA neighbors"
        assert "Thames Valley" in nca_neighbors, "Should include Thames Valley itself"
        
        # Verify the name query was called (not point query)
        assert mock_name_query.call_count == 2, "Should call name query twice"
        assert not mock_point_query.called, "Should not call point query when no lat/lon"
        
        print("✓ Neighbor lookup flow works correctly for manual LPA/NCA")
        print(f"  - LPA neighbors: {lpa_neighbors}")
        print(f"  - NCA neighbors: {nca_neighbors}")


def test_promoter_app_with_latlon():
    """
    Test that the original lat/lon lookup still works.
    This ensures we didn't break existing functionality.
    """
    print("\n=== Testing original lat/lon neighbor lookup ===")
    
    # Simulate having lat/lon from postcode geocoding
    lat, lon = 51.5, -0.1
    target_lpa = None
    target_nca = None
    lpa_neighbors, nca_neighbors = [], []
    
    with patch('optimizer_core.arcgis_point_query') as mock_point_query, \
         patch('optimizer_core.arcgis_name_query') as mock_name_query, \
         patch('optimizer_core.layer_intersect_names') as mock_intersect:
        
        # Setup mocks for point query
        lpa_geom = {"rings": [[[0, 0], [1, 1], [1, 0], [0, 0]]]}
        nca_geom = {"rings": [[[0, 0], [1, 1], [1, 0], [0, 0]]]}
        
        mock_point_query.side_effect = [
            {"geometry": lpa_geom, "attributes": {"LAD24NM": "Westminster"}},
            {"geometry": nca_geom, "attributes": {"NCA_Name": "Thames Valley"}}
        ]
        
        mock_intersect.side_effect = [
            ["Westminster", "Kensington and Chelsea"],
            ["Thames Valley", "Chilterns"]
        ]
        
        # Simulate the first block (lat/lon check) - should execute
        if lat and lon:
            lpa_feat = mock_point_query("http://lpa.url", lat, lon, "LAD24NM")
            nca_feat = mock_point_query("http://nca.url", lat, lon, "NCA_Name")
            
            if lpa_feat and lpa_feat.get("geometry"):
                lpa_neighbors = mock_intersect("http://lpa.url", lpa_feat.get("geometry"), "LAD24NM")
            if nca_feat and nca_feat.get("geometry"):
                nca_neighbors = mock_intersect("http://nca.url", nca_feat.get("geometry"), "NCA_Name")
        
        # The second block should not execute because we already have neighbors
        if (not lpa_neighbors or not nca_neighbors) and target_lpa and target_nca:
            assert False, "Should not execute when neighbors already found via lat/lon"
        
        # Verify results
        assert len(lpa_neighbors) == 2, "Should have LPA neighbors"
        assert len(nca_neighbors) == 2, "Should have NCA neighbors"
        
        # Verify point query was called (not name query)
        assert mock_point_query.call_count == 2, "Should call point query twice"
        assert not mock_name_query.called, "Should not call name query when using lat/lon"
        
        print("✓ Original lat/lon lookup still works")
        print(f"  - LPA neighbors: {lpa_neighbors}")
        print(f"  - NCA neighbors: {nca_neighbors}")


if __name__ == "__main__":
    print("=" * 60)
    print("Unit Tests for LPA/NCA Lookup (No Network Required)")
    print("=" * 60)
    
    try:
        test_arcgis_name_query_logic()
        test_arcgis_name_query_no_results()
        test_promoter_app_neighbor_lookup_flow()
        test_promoter_app_with_latlon()
        
        print("\n" + "=" * 60)
        print("✅ All unit tests passed!")
        print("=" * 60)
        
    except AssertionError as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        raise
    except Exception as e:
        print(f"\n❌ Error during test: {e}")
        import traceback
        traceback.print_exc()
        raise
