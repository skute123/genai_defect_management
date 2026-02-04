import pandas as pd
import os
from openpyxl import load_workbook
from openpyxl.styles import Alignment

# -----------------------------
# Paths
# -----------------------------
base_dir = os.path.dirname(os.path.abspath(__file__))

input_folder = os.path.join(base_dir, "../combine_sit")
output_folder = os.path.join(base_dir, "../sheet")
os.makedirs(output_folder, exist_ok=True)

output_file = os.path.join(output_folder, "defect_sheet_sit.csv")

# -----------------------------
# Combine all CSV files
# -----------------------------
csv_files = [f for f in os.listdir(input_folder) if f.endswith(".csv")]

if not csv_files:
    print(" No CSV files found in combine_sit folder.")
else:
    combined_data = []
    for file in csv_files:
        file_path = os.path.join(input_folder, file)
        print(f"🔹 Reading: {file}")
        df = pd.read_csv(file_path, low_memory=False)
        df["Source_File"] = file
        combined_data.append(df)

    combined_df = pd.concat(combined_data, ignore_index=True)
    combined_df.to_csv(output_file, index=False)
    print(f" Combined SIT CSV saved as: {output_file}")
