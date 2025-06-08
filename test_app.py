import pytest
import pandas as pd
import io
import json
from app import app

@pytest.fixture
def client():
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client

def test_no_file_uploaded(client):
    """Test response when no file is uploaded"""
    response = client.post('/pnov-bridge')
    assert response.status_code == 400
    data = json.loads(response.data)
    assert "error" in data
    assert data["error"] == "No file uploaded"

def test_empty_dsp_name_handling(client):
    """Test that empty DSP Name values are converted to 'FLEX'"""
    # Create test CSV data with empty DSP Name
    csv_data = """Tracking ID,DSP Name,DA Name,Route,Cost
    ABC123,,John Doe,R1,25.00
    DEF456,DSP1,Jane Smith,R2,30.00
    GHI789,,Bob Johnson,R1,60.00"""
    
    data = {'file': (io.BytesIO(csv_data.encode('utf-8')), 'test.csv')}
    response = client.post('/pnov-bridge', data=data, content_type='multipart/form-data')
    
    assert response.status_code == 200
    response_data = json.loads(response.data)
    report = response_data["report"]
    
    # Check if FLEX appears in the report
    assert "FLEX" in report

def test_high_value_mm(client):
    """Test high value missing missorts section - should exclude FLEX drivers and sort by cost"""
    # Create test CSV data with high value items in random cost order
    csv_data = """Tracking ID,DSP Name,DA Name,Route,Cost
    ABC123,DSP1,John Doe,R1,85.00
    DEF456,DSP2,Jane Smith,R2,75.00
    GHI789,FLEX,Bob Johnson,R3,100.00
    JKL012,DSP3,Sarah Wilson,R4,150.00
    MNO345,DSP4,Tom Davis,R5,60.00"""
    
    data = {'file': (io.BytesIO(csv_data.encode('utf-8')), 'test.csv')}
    response = client.post('/pnov-bridge', data=data, content_type='multipart/form-data')
    
    assert response.status_code == 200
    response_data = json.loads(response.data)
    report = response_data["report"]
    
    # Split the report into lines
    report_lines = report.split('\n')
    
    # Get the high value section lines (after the header)
    high_value_index = report_lines.index("High Value MM still missing DAs")
    high_value_lines = report_lines[high_value_index+1:]
    
    # Check if high value section includes DSP items but not FLEX
    assert "DSP3" in report
    assert "DSP1" in report
    assert "DSP2" in report
    assert "DSP4" in report
    
    # Verify FLEX item is excluded
    assert "FLEX" not in "".join(high_value_lines)
    
    # Verify sorting: the items should appear in descending order by cost
    # First item should be DSP3 with cost 150.00
    assert "150.00" in high_value_lines[0]
    assert "DSP3" in high_value_lines[0]
    
    # Second item should be DSP1 with cost 85.00
    assert "85.00" in high_value_lines[1]
    assert "DSP1" in high_value_lines[1]
    
    # Last item should be DSP4 with cost 60.00
    assert "60.00" in high_value_lines[-1]
    assert "DSP4" in high_value_lines[-1]

def test_multiple_mm_by_da(client):
    """Test multiple missing missorts by DA section"""
    # Create test CSV data with a DA having multiple missing missorts
    csv_data = """Tracking ID,DSP Name,DA Name,Route,Cost
    ABC123,DSP1,John Doe,R1,25.00
    DEF456,DSP1,John Doe,R1,30.00
    GHI789,DSP1,John Doe,R1,20.00"""
    
    data = {'file': (io.BytesIO(csv_data.encode('utf-8')), 'test.csv')}
    response = client.post('/pnov-bridge', data=data, content_type='multipart/form-data')
    
    assert response.status_code == 200
    response_data = json.loads(response.data)
    report = response_data["report"]
    
    # Check if multiple MM section appears correctly
    assert "DAs with Over 1 MM still missing:" in report
    assert "R1 / John Doe / 3" in report

def test_total_by_dsp(client):
    """Test total PNOV by DSP section"""
    # Create test CSV data with multiple DSPs
    csv_data = """Tracking ID,DSP Name,DA Name,Route,Cost
    ABC123,DSP1,John Doe,R1,25.00
    DEF456,DSP2,Jane Smith,R2,30.00
    GHI789,,Bob Johnson,R3,20.00
    JKL012,DSP1,Alice Brown,R4,15.00"""
    
    data = {'file': (io.BytesIO(csv_data.encode('utf-8')), 'test.csv')}
    response = client.post('/pnov-bridge', data=data, content_type='multipart/form-data')
    
    assert response.status_code == 200
    response_data = json.loads(response.data)
    report = response_data["report"]
    
    # Check if DSP totals appear correctly
    assert "DSP1\t2" in report
    assert "DSP2\t1" in report
    assert "FLEX\t1" in report
    assert "Grand Total\t4" in report 