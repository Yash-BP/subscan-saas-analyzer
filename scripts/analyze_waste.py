import pandas as pd
import sqlite3
import os
import logging
from dotenv import load_dotenv

# Load environment variables
load_dotenv()
INACTIVITY_DAYS = int(os.getenv('INACTIVITY_THRESHOLD_DAYS', 30))
ZOMBIE_LABEL = os.getenv('WASTE_LABEL_ZOMBIE', 'Zero Usage in 30 Days (Zombie License)')
TERMINATED_LABEL = os.getenv('WASTE_LABEL_TERMINATED', 'Terminated Employee (Wasted License)')

# 0. Set up the enterprise logger
script_dir = os.path.dirname(os.path.abspath(__file__))
log_file_path = os.path.join(script_dir, 'execution_audit.log')

logging.basicConfig(
    filename=log_file_path, level=logging.INFO, 
    format='%(asctime)s - %(levelname)s - %(message)s', datefmt='%Y-%m-%d %H:%M:%S'
)

logging.info("--- NEW EXECUTION STARTED ---")
logging.info("Initializing SaaS Waste Analytics Engine...")

# 1. Connect to SQL Database and Load Data
data_dir = os.path.join(script_dir, '..', 'data')
db_path = os.path.join(data_dir, 'company_database.db')

logging.info("Attempting to connect to SQL database...")
try:
    # Connect to the database
    conn = sqlite3.connect(db_path)
    
    # Run SQL Queries to pull data directly into Pandas
    df_employees = pd.read_sql_query("SELECT * FROM employees", conn)
    df_subs = pd.read_sql_query("SELECT * FROM subscriptions", conn)
    df_usage = pd.read_sql_query("SELECT * FROM usage_logs", conn)
    
    conn.close()
    logging.info("All datasets successfully pulled from SQL database.")
except sqlite3.Error as e:
    logging.error(f"CRITICAL ERROR: Database connection failed - {e}")
    exit()

# 2. Join the tables together
logging.info("Merging employee, subscription, and usage data...")
df_merged = pd.merge(df_subs, df_employees, on='emp_id', how='left')
df_final = pd.merge(df_merged, df_usage, on=['sub_id', 'emp_id', 'tool_name'], how='left')

# 3. Identify the Waste
def identify_waste(row):
    if row['status'] == 'Terminated':
        return TERMINATED_LABEL
    elif row['logins_last_30_days'] == 0:
        return ZOMBIE_LABEL
    return 'Active & Used'

logging.info("Analyzing usage patterns to find wasted spend...")
df_final['waste_category'] = df_final.apply(identify_waste, axis=1)

# 4. Filter for only the wasted subscriptions
df_waste = df_final[df_final['waste_category'] != 'Active & Used'].copy()
monthly_waste = df_waste['monthly_cost'].sum()

logging.info(f"AUDIT RESULTS: Found {len(df_waste)} wasted licenses. Total Monthly Waste: ${monthly_waste:,.2f}.")

# 5. Export the clean data
output_file = os.path.join(data_dir, 'identified_waste_report.csv')
try:
    df_waste.to_csv(output_file, index=False)
    logging.info(f"Clean report successfully saved for Power BI at: {output_file}")
except Exception as e:
    logging.error(f"Failed to save output file: {e}")
    
logging.info("--- EXECUTION COMPLETED ---")