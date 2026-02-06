import pandas as pd
import mysql.connector

# =========================
# Configurations
# =========================
files_and_tables = {
    "output/filtered_output_acc.xlsx": "defects_table_acc",
    "output/filtered_output_sit.xlsx": "defects_table_sit"
}
primary_key_col = "Issue key"

# =========================
# Connect to MySQL
# =========================
conn = mysql.connector.connect(
    host='localhost',
    user='root',
    password='admin',
    database='defect_db'
)
cursor = conn.cursor()

# =========================
# Function to load data into MySQL
# =========================
def load_excel_to_mysql(file_path, table_name):
    print(f"\n Processing {file_path} → {table_name}")

    # Step 1: Load Excel file
    df = pd.read_excel(file_path)

    # Step 2: Check if table exists
    cursor.execute(f"""
        SELECT COUNT(*)
        FROM information_schema.tables
        WHERE table_schema = DATABASE()
        AND table_name = '{table_name}'
    """)
    table_exists = cursor.fetchone()[0]

    # Step 3: Create table if not exists
    if not table_exists:
        columns = []
        for col in df.columns:
            if col == primary_key_col:
                columns.append(f"`{col}` VARCHAR(255) PRIMARY KEY")
            elif col == "Comment": # Assuming 'Comment' can be long text
                columns.append(f"`{col}` LONGTEXT")
            else:
                columns.append(f"`{col}` VARCHAR(1000)")
        columns_sql = ", ".join(columns)
        create_query = f"CREATE TABLE {table_name} ({columns_sql})"
        cursor.execute(create_query)
        print(f" Table '{table_name}' created with PRIMARY KEY on '{primary_key_col}'.")
    else:
        print(f"ℹ Table '{table_name}' already exists. Proceeding with safe appending...")

    # Step 4: Insert with IGNORE to skip duplicates
    inserted, skipped = 0, 0
    for _, row in df.iterrows():
        placeholders = ", ".join(["%s"] * len(row))
        column_names = ", ".join([f"`{col}`" for col in df.columns])
        insert_query = f"INSERT IGNORE INTO {table_name} ({column_names}) VALUES ({placeholders})"
        cursor.execute(insert_query, tuple(row.astype(str)))

        if cursor.rowcount == 1:
            inserted += 1
        else:
            skipped += 1

    conn.commit()
    print(f" {inserted} new rows inserted into {table_name}.")
    print(f" {skipped} rows skipped due to duplicate '{primary_key_col}' values.")


# =========================
# Process Both Files
# =========================
for file_path, table_name in files_and_tables.items():
    load_excel_to_mysql(file_path, table_name)

# =========================
# Cleanup
# =========================
cursor.close()
conn.close()
print("\n Data loading complete for all files.")
