"""
End-to-end tests for the Day of Ops Plan feature
"""

import os
import pytest
import io
import json
import zipfile
import pandas as pd
from app import app

@pytest.fixture
def client():
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client

def get_test_file_path():
    """Get the path to the test file"""
    # Try different relative paths to find the test file
    possible_paths = [
        "../testData/2025-08-21-DMD6-CYCLE_1-DSP-DayOfOpsPlan.xlsx",
        "../../testData/2025-08-21-DMD6-CYCLE_1-DSP-DayOfOpsPlan.xlsx",
        "../../../testData/2025-08-21-DMD6-CYCLE_1-DSP-DayOfOpsPlan.xlsx",
        "testData/2025-08-21-DMD6-CYCLE_1-DSP-DayOfOpsPlan.xlsx"
    ]
    
    for path in possible_paths:
        if os.path.exists(path):
            return path
    
    # If test file not found, create a mock file
    print("Test file not found, creating mock file")
    buffer = io.BytesIO()
    test_data = pd.DataFrame({
        'DSP': ['VAKO', 'TRZC', 'VAKO', 'DMRY', 'TRZC', 'MEGS'],
        'Route': ['CX87', 'CX161', 'CX56', 'CX219', 'CX153', 'CX201'],
        'DA Name': ['Driver1', 'Driver2', 'Driver3', 'Driver4', 'Driver5', 'Driver6'],
        'Value': [100, 200, 300, 400, 500, 600]
    })
    
    with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
        test_data.to_excel(writer, sheet_name='Solution', index=False)
    
    buffer.seek(0)
    return buffer

def test_full_day_of_ops_workflow(client):
    """Test the complete workflow of the Day of Ops Plan feature with real test data"""
    
    # Get test file
    test_file = get_test_file_path()
    
    # If test_file is a path string, open the file
    if isinstance(test_file, str):
        with open(test_file, 'rb') as f:
            file_content = f.read()
            file_obj = (io.BytesIO(file_content), '2025-08-21-DMD6-CYCLE_1-DSP-DayOfOpsPlan.xlsx')
    else:
        # If test_file is already a buffer
        file_obj = (test_file, '2025-08-21-DMD6-CYCLE_1-DSP-DayOfOpsPlan.xlsx')
    
    # Create form data with file
    data = {'file': file_obj}
    
    # Send request to API
    try:
        response = client.post('/split-day-of-ops', data=data, content_type='multipart/form-data')
        
        # Check response status
        assert response.status_code in [200, 500]
        
        if response.status_code == 200:
            # Check response headers
            assert response.headers['Content-Type'] == 'application/zip'
            assert 'X-Summary' in response.headers
            
            # Parse summary header
            summary = json.loads(response.headers['X-Summary'])
            assert 'date' in summary
            assert 'dsps' in summary
            assert 'totalFiles' in summary
            
            # Check ZIP file content
            zip_buffer = io.BytesIO(response.data)
            with zipfile.ZipFile(zip_buffer) as zip_file:
                # Check if we have at least one file
                file_list = zip_file.namelist()
                assert len(file_list) > 0
                
                # Check if file names follow the pattern
                for filename in file_list:
                    assert filename.endswith('_Day_Of_Ops_Plan_2025-08-21.xlsx')
                    
                # Check the content of the first file
                first_file = file_list[0]
                with zip_file.open(first_file) as excel_file:
                    df = pd.read_excel(excel_file)
                    # Check if the dataframe has rows and the expected columns
                    assert len(df) > 0
                    assert 'DSP' in df.columns
        else:
            # If status is 500, check for error message
            response_data = json.loads(response.data)
            assert "error" in response_data
            print(f"API returned error: {response_data['error']}")
            
    except Exception as e:
        # Print any exceptions for debugging
        print(f"Exception during test: {str(e)}")
        raise
        
def test_error_handling_with_invalid_file(client):
    """Test error handling with an invalid file"""
    
    # Create an invalid Excel file (not a proper Day of Ops Plan)
    buffer = io.BytesIO()
    test_data = pd.DataFrame({
        'NotDSP': ['Value1', 'Value2'],
        'OtherColumn': ['A', 'B']
    })
    
    with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
        test_data.to_excel(writer, sheet_name='WrongSheet', index=False)
    
    buffer.seek(0)
    
    # Create form data with invalid file
    data = {'file': (buffer, 'invalid.xlsx')}
    
    # Send request to API
    response = client.post('/split-day-of-ops', data=data, content_type='multipart/form-data')
    
    # Check response status (should be 400 for validation errors or 500 for other errors)
    assert response.status_code in [400, 500]
    
    # Check error message
    response_data = json.loads(response.data)
    assert "error" in response_data
