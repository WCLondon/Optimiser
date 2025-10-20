"""
Basic tests for the FastAPI backend.
"""

import pytest
from fastapi.testclient import TestClient
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from main import app


@pytest.fixture
def client():
    """Create a test client."""
    return TestClient(app)


def test_root_endpoint(client):
    """Test the root endpoint."""
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["service"] == "BNG Optimiser API"
    assert data["status"] == "running"


def test_health_check(client):
    """Test the health check endpoint."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "timestamp" in data


def test_run_endpoint_missing_demand(client):
    """Test run endpoint with missing demand."""
    response = client.post("/run", json={
        "demand": [],
        "location": {}
    })
    # Should accept the request but may fail during processing
    assert response.status_code in [200, 422]


def test_status_endpoint_not_found(client):
    """Test status endpoint with non-existent job."""
    response = client.get("/status/nonexistent-job-id")
    assert response.status_code == 404


def test_list_jobs(client):
    """Test listing jobs."""
    response = client.get("/jobs")
    assert response.status_code == 200
    data = response.json()
    assert "jobs" in data
    assert isinstance(data["jobs"], list)
