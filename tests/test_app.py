import pytest
import json
import io
from app import app

@pytest.fixture
def client():
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client

def test_pnov_bridge_no_file_uploaded(client):
    """Test response when no file is uploaded to PNOV bridge endpoint"""
    response = client.post('/pnov-bridge')
    assert response.status_code == 400
    data = json.loads(response.data)
    assert "error" in data
    assert data["error"] == "No file uploaded"

def test_split_day_of_ops_no_file_uploaded(client):
    """Test response when no file is uploaded to split-day-of-ops endpoint"""
    response = client.post('/split-day-of-ops')
    assert response.status_code == 400
    data = json.loads(response.data)
    assert "error" in data
    assert data["error"] == "No file uploaded"

def test_options_endpoint(client):
    """Test the OPTIONS endpoint for CORS preflight requests"""
    response = client.options('/pnov-bridge')
    assert response.status_code == 200
    data = json.loads(response.data)
    assert data["status"] == "success"
    
    # Check CORS headers
    assert response.headers.get('Access-Control-Allow-Origin') == '*'
    assert response.headers.get('Access-Control-Allow-Headers') == 'Content-Type'
    assert response.headers.get('Access-Control-Allow-Methods') == 'GET, POST, OPTIONS'

def test_split_day_of_ops_options_endpoint(client):
    """Test the OPTIONS endpoint for split-day-of-ops CORS preflight requests"""
    response = client.options('/split-day-of-ops')
    assert response.status_code == 200
    data = json.loads(response.data)
    assert data["status"] == "success"
    
    # Check CORS headers
    assert response.headers.get('Access-Control-Allow-Origin') == '*'
    assert response.headers.get('Access-Control-Allow-Headers') == 'Content-Type'
    assert response.headers.get('Access-Control-Allow-Methods') == 'GET, POST, OPTIONS'
