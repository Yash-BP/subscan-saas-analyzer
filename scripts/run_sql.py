import sqlite3
import os

# Notice the \data\ folder added to the path here:
db_path = r'C:\subscan-saas-analyzer\data\company_database.db'
sql_path = r'C:\subscan-saas-analyzer\scripts\setup_powerbi_views.sql'

conn = sqlite3.connect(db_path)

with open(sql_path, 'r') as file:
    sql_script = file.read()

try:
    conn.executescript(sql_script)
    print("SUCCESS: Views injected into the REAL database!")
except Exception as e:
    print(f"ERROR: {e}")

conn.commit()
conn.close()