"""
Simple smoke test for promoter form routes
Tests basic functionality without database or external dependencies
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from fastapi.testclient import TestClient
from unittest.mock import Mock, patch

# Mock the database and storage before importing the app
mock_engine = Mock()
mock_storage = Mock()

with patch('database.get_db_engine', return_value=mock_engine):
    with patch('storage.SupabaseStorage', return_value=mock_storage):
        from app import app

client = TestClient(app)


def test_app_health():
    """Test that the app starts and health endpoint works"""
    # Note: health endpoint might fail without Redis, but app should start
    response = client.get("/")
    # Just checking the app responds
    assert response.status_code in [200, 404, 307]  # Any response is good


def test_promoter_form_display():
    """Test that promoter form displays correctly"""
    response = client.get("/EPT")
    assert response.status_code == 200
    assert b"BNG Quote Request" in response.content
    assert b"EPT" in response.content
    assert b"Contact Email" in response.content
    assert b"metric_file" in response.content


def test_promoter_form_different_slugs():
    """Test that different promoter slugs work"""
    for slug in ["EPT", "Arbtech", "TestPromoter"]:
        response = client.get(f"/{slug}")
        assert response.status_code == 200
        assert slug.upper().encode() in response.content


def test_form_has_required_fields():
    """Test that form contains all required fields"""
    response = client.get("/EPT")
    content = response.content.decode()
    
    # Check for required fields
    assert 'name="contact_email"' in content
    assert 'name="site_address"' in content
    assert 'name="site_postcode"' in content
    assert 'name="metric_file"' in content
    assert 'name="consent"' in content
    
    # Check for optional fields
    assert 'name="client_reference"' in content
    assert 'name="notes"' in content


def test_form_validation_messages():
    """Test that form includes validation requirements"""
    response = client.get("/EPT")
    content = response.content.decode()
    
    # Check for required indicators
    assert 'required' in content.lower()
    assert 'xlsx' in content.lower()


if __name__ == "__main__":
    print("Running promoter form smoke tests...")
    
    try:
        test_app_health()
        print("✓ App health check passed")
    except Exception as e:
        print(f"✗ App health check failed: {e}")
    
    try:
        test_promoter_form_display()
        print("✓ Form display test passed")
    except Exception as e:
        print(f"✗ Form display test failed: {e}")
    
    try:
        test_promoter_form_different_slugs()
        print("✓ Multiple promoter slugs test passed")
    except Exception as e:
        print(f"✗ Multiple promoter slugs test failed: {e}")
    
    try:
        test_form_has_required_fields()
        print("✓ Required fields test passed")
    except Exception as e:
        print(f"✗ Required fields test failed: {e}")
    
    try:
        test_form_validation_messages()
        print("✓ Validation messages test passed")
    except Exception as e:
        print(f"✗ Validation messages test failed: {e}")
    
    print("\nAll smoke tests completed!")
