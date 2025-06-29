from flask import Flask, request, jsonify
from flask_cors import CORS
import pandas as pd
import io

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

# Add an options route to handle preflight requests
@app.route("/pnov-bridge", methods=["OPTIONS"])
def options():
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


if __name__ == "__main__":
    app.run(debug=True, port=5000)
