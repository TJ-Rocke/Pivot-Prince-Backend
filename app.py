from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
import pandas as pd
import io
import zipfile
import re
from datetime import datetime
import pytz
import json

app = Flask(__name__)
# Simplify CORS configuration
CORS(app)

# Add CORS headers to all responses
@app.after_request
def add_cors_headers(response):
    response.headers.add('Access-Control-Allow-Origin', '*')
    response.headers.add('Access-Control-Allow-Headers', 'Content-Type')
    response.headers.add('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
    return response

# Add options routes to handle preflight requests
@app.route("/pnov-bridge", methods=["OPTIONS"])
def options():
    return jsonify({'status': 'success'})

@app.route("/split-day-of-ops", methods=["OPTIONS"])
def split_day_of_ops_options():
    return jsonify({'status': 'success'})

@app.route("/pnov-bridge", methods=["POST"])
def pnov_bridge():
    if "file" not in request.files:
        return jsonify({"error": "No file uploaded"}), 400

    file = request.files["file"]
    df = pd.read_csv(file)
    df.columns = df.columns.str.strip()
    
    # Replace blank/empty DSP Name values with "FLEX"
    df["DSP Name"] = df["DSP Name"].fillna("FLEX")
    df["DSP Name"] = df["DSP Name"].replace("", "FLEX")

    output_lines = []

    # 1. Total PNOV by DSP
    total_by_dsp = (
        df.groupby("DSP Name")["Tracking ID"].count().reset_index(name="Total")
    )
    total_by_dsp = total_by_dsp.sort_values(by="Total", ascending=False)
    for _, row in total_by_dsp.iterrows():
        output_lines.append(f"{row['DSP Name']}\t{row['Total']}")
    output_lines.append(f"Grand Total\t{total_by_dsp['Total'].sum()}")
    output_lines.append("")

    # 2. DAs with Over 1 MM Still Missing
    over_1_mm = (
        df.groupby(["DA Name", "DSP Name", "Route"])["Tracking ID"]
        .count()
        .reset_index(name="Total")
    )
    # Filter out FLEX/SNOW Platform
    over_1_mm = over_1_mm[(over_1_mm["DSP Name"] != "FLEX") & (over_1_mm["DSP Name"] != "SNOW Platform")]
    over_1_mm = over_1_mm[over_1_mm["Total"] > 1].sort_values(
        by="Total", ascending=False
    )
    output_lines.append("DAs with Over 1 MM still missing:")
    for _, row in over_1_mm.iterrows():
        output_lines.append(f"{row['Route']} / {row['DA Name']} / {row['Total']}")
        # output_lines.append(str(row["Total"]))
    output_lines.append("")

    # 3. High Value MM Still Missing
    if "Cost" in df.columns and "Route" in df.columns:
        # Filter to exclude FLEX drivers from high value items
        high_value = df[(df["Cost"] >= 50) & (df["DSP Name"] != "FLEX")][["Route", "DSP Name", "DA Name", "Tracking ID", "Cost"]]
        # Sort by Cost in descending order
        high_value = high_value.sort_values(by="Cost", ascending=False)
        output_lines.append("High Value MM still missing DAs")
        for _, row in high_value.iterrows():
            output_lines.append(
                f"{row['Route']}/ {row['DA Name']} / {row['DSP Name']} / {row['Tracking ID']}\t{row['Cost']:.2f}"
            )

    result_text = "\n".join(output_lines)
    response = jsonify({"report": result_text})
    
    return response


@app.route("/split-day-of-ops", methods=["POST"])
def split_day_of_ops():
    """
    Split Day of Ops Plan Excel file by DSP and return a ZIP file containing individual Excel files.
    
    1. Reads the uploaded Excel file, looking for the 'Solution' sheet
    2. Verifies that the 'DSP' column exists
    3. Groups data by DSP
    4. Creates individual Excel files for each DSP
    5. Packages all files into a ZIP archive
    6. Returns the ZIP file as an attachment
    """
    if "file" not in request.files:
        return jsonify({"error": "No file uploaded"}), 400

    file = request.files["file"]
    
    # Check if file is an Excel file
    if not file.filename.endswith(('.xlsx', '.xls')):
        return jsonify({"error": "Upload a .xlsx Day Of Ops Plan workbook."}), 400
    
    # Extract date from filename if it exists, otherwise use today's date
    date_match = re.search(r'(\d{4}-\d{2}-\d{2})', file.filename)
    if date_match:
        date_str = date_match.group(1)
    else:
        # Use today's date in America/New_York timezone
        ny_tz = pytz.timezone('America/New_York')
        date_str = datetime.now(ny_tz).strftime('%Y-%m-%d')
    
    try:
        # Try to read the Excel file
        excel_file = pd.ExcelFile(file)
        
        # Check if 'Solution' sheet exists
        if 'Solution' not in excel_file.sheet_names:
            return jsonify({"error": "Sheet 'Solution' not found. Use the standard template."}), 400
        
        # Read the 'Solution' sheet
        df = pd.read_excel(excel_file, sheet_name='Solution')
        
        # Check if 'DSP' column exists
        if 'DSP' not in df.columns:
            return jsonify({"error": "Column 'DSP' not found on sheet 'Solution'."}), 400
        
        # Clean DSP values
        df['DSP'] = df['DSP'].str.strip()
        df = df.dropna(subset=['DSP'])
        
        # Group by DSP
        dsp_groups = df.groupby('DSP')
        
        # Check if we have any valid DSP values
        if len(dsp_groups) == 0:
            return jsonify({"error": "No DSP values found. Check the 'DSP' column."}), 400
        
        # Create a BytesIO object to store the ZIP file
        zip_buffer = io.BytesIO()
        
        # Create a ZIP file
        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
            # Dictionary to store DSP counts for the summary
            dsp_counts = {}
            
            # Process each DSP group
            for dsp_name, dsp_data in dsp_groups:
                # Sanitize DSP name for filename
                sanitized_dsp = re.sub(r'[^A-Za-z0-9_-]', '', dsp_name.replace(' ', '_'))
                
                # Create filename
                filename = f"{sanitized_dsp}_Day_Of_Ops_Plan_{date_str}.xlsx"
                
                # Create a BytesIO object for the Excel file
                excel_buffer = io.BytesIO()
                
                # Write the DataFrame to the Excel file
                with pd.ExcelWriter(excel_buffer, engine='openpyxl') as writer:
                    dsp_data.to_excel(writer, sheet_name='Solution', index=False)
                
                # Reset the buffer position
                excel_buffer.seek(0)
                
                # Add the Excel file to the ZIP file
                zip_file.writestr(filename, excel_buffer.getvalue())
                
                # Store the count for the summary
                dsp_counts[dsp_name] = len(dsp_data)
        
        # Reset the ZIP buffer position
        zip_buffer.seek(0)
        
        # Create the ZIP filename
        zip_filename = f"Day_Of_Ops_Plan_{date_str}_per_DSP.zip"
        
        # Prepare the summary data
        summary = {
            "date": date_str,
            "dsps": [{"name": dsp, "count": count} for dsp, count in dsp_counts.items()],
            "totalFiles": len(dsp_counts)
        }
        
        # Return the ZIP file as an attachment with the summary in the response headers
        response = send_file(
            zip_buffer,
            mimetype='application/zip',
            as_attachment=True,
            download_name=zip_filename
        )
        response.headers['X-Summary'] = json.dumps(summary)
        return response
    
    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    app.run(debug=True, port=5000)
