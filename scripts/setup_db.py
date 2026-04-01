import pandas as pd
import sqlite3
import os

# Set up paths
script_dir = os.path.dirname(os.path.abspath(__file__))
data_dir = os.path.join(script_dir, '..', 'data')
db_path = os.path.join(data_dir, 'company_database.db')

print("Starting Database Setup...")

# 1. Load the CSVs
df_emp = pd.read_csv(os.path.join(data_dir, 'employees.csv'))
df_subs = pd.read_csv(os.path.join(data_dir, 'subscriptions.csv'))
df_usage = pd.read_csv(os.path.join(data_dir, 'usage_logs.csv'))

# 2. Connect to SQL (This creates the file if it doesn't exist)
conn = sqlite3.connect(db_path)

# 3. Push the data into SQL tables
print("Pushing data to SQL tables...")
df_emp.to_sql('employees', conn, if_exists='replace', index=False)
df_subs.to_sql('subscriptions', conn, if_exists='replace', index=False)
df_usage.to_sql('usage_logs', conn, if_exists='replace', index=False)

conn.close()
print(f"✅ Success! SQL Database created at: {db_path}")