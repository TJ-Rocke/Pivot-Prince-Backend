# PNOV Bridge Backend

This Flask backend processes CSV files for the PNOV Bridge application.

## Setup

1. Install dependencies:

```
pip install -r requirements.txt
```

2. Run the backend server:

```
python app.py
```

The server will start on http://localhost:5000

## API Endpoints

### POST /pnov-bridge

Processes a CSV file and returns a formatted report.

**Request:**

- Form data with a `file` field containing the CSV file

**Response:**

- JSON object with a `report` field containing the formatted report text

## Running Tests

Run the tests using pytest:

```
pytest test_app.py -v
```

## Key Features

- Processes CSV data to generate PNOV reports
- Handles empty DSP Name values by converting them to "FLEX"
- Generates reports showing:
  - Total PNOV by DSP
  - DAs with Over 1 MM Still Missing
  - High Value MM Still Missing
