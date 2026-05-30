import sqlite3
import os

# Set up the exact paths to your database and SQL file
script_dir = os.path.dirname(os.path.abspath(__file__))
db_path = os.path.join(script_dir, "..", "data", "company_database.db")
sql_path = os.path.join(script_dir, "setup_powerbi_views.sql")

def main():
    # 1. Check if the database exists
    if not os.path.exists(db_path):
        print(f"ERROR: Database not found at {db_path}. Run the pipeline first.")
        return
    
    # 2. Read your SQL code
    try:
        with open(sql_path, 'r') as file:
            sql_script = file.read()
    except FileNotFoundError:
        print(f"ERROR: SQL file not found at {sql_path}")
        return

    # 3. Connect to the database and inject the views
    with sqlite3.connect(db_path) as conn:
        try:
            conn.executescript(sql_script)
            print("SUCCESS: Power BI views successfully injected into the database!")
        except Exception as e:
            print(f"ERROR executing SQL: {e}")

if __name__ == "__main__":
    main()