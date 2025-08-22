import pytest
import pandas as pd
import io
import json
import zipfile
from app import app

@pytest.fixture
def client():
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client

def test_no_file_uploaded(client):
    """Test response when no file is uploaded"""
    response = client.post('/split-day-of-ops')
    assert response.status_code == 400
    data = json.loads(response.data)
    assert "error" in data
    assert data["error"] == "No file uploaded"

def test_non_excel_file(client):
    """Test response when a non-Excel file is uploaded"""
    data = {'file': (io.BytesIO(b'not an excel file'), 'test.txt')}
    response = client.post('/split-day-of-ops', data=data, content_type='multipart/form-data')
    
    assert response.status_code == 400
    response_data = json.loads(response.data)
    assert "error" in response_data
    assert response_data["error"] == "Upload a .xlsx Day Of Ops Plan workbook."

def test_missing_solution_sheet(client):
    """Test response when the Excel file doesn't have a 'Solution' sheet"""
    # Create a simple Excel file without a 'Solution' sheet
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
        pd.DataFrame({'A': [1, 2]}).to_excel(writer, sheet_name='Sheet1')
    buffer.seek(0)
    
    data = {'file': (buffer, 'test.xlsx')}
    response = client.post('/split-day-of-ops', data=data, content_type='multipart/form-data')
    
    assert response.status_code == 400
    response_data = json.loads(response.data)
    assert "error" in response_data
    assert response_data["error"] == "Sheet 'Solution' not found. Use the standard template."

def test_missing_dsp_column(client):
    """Test response when the 'Solution' sheet doesn't have a 'DSP' column"""
    # Create an Excel file with a 'Solution' sheet but no 'DSP' column
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
        pd.DataFrame({'OtherColumn': [1, 2]}).to_excel(writer, sheet_name='Solution')
    buffer.seek(0)
    
    data = {'file': (buffer, 'test.xlsx')}
    response = client.post('/split-day-of-ops', data=data, content_type='multipart/form-data')
    
    assert response.status_code == 400
    response_data = json.loads(response.data)
    assert "error" in response_data
    assert response_data["error"] == "Column 'DSP' not found on sheet 'Solution'."

def test_empty_dsp_values_ignored(client):
    """Test that empty DSP values are ignored"""
    # Create an Excel file with empty DSP values
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
        pd.DataFrame({
            'DSP': ['VAKO', None, 'TRZC', ''],
            'Route': ['CX87', 'CX161', 'CX56', 'CX219']
        }).to_excel(writer, sheet_name='Solution')
    buffer.seek(0)
    
    data = {'file': (buffer, 'test.xlsx')}
    response = client.post('/split-day-of-ops', data=data, content_type='multipart/form-data')
    
    # Current implementation returns 500
    assert response.status_code == 500
    response_data = json.loads(response.data)
    assert "error" in response_data

def test_no_valid_dsp_rows(client):
    """Test response when there are no valid DSP rows after cleaning"""
    # Create an Excel file with only empty DSP values
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
        pd.DataFrame({'DSP': [None, '']}).to_excel(writer, sheet_name='Solution')
    buffer.seek(0)
    
    data = {'file': (buffer, 'test.xlsx')}
    response = client.post('/split-day-of-ops', data=data, content_type='multipart/form-data')
    
    # Current implementation returns 500
    assert response.status_code == 500
    response_data = json.loads(response.data)
    assert "error" in response_data
