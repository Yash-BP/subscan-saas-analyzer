import pandas as pd
import os

# 1. Set up paths and load the data
script_dir = os.path.dirname(os.path.abspath(__file__))
data_dir = os.path.join(script_dir, '..', 'data')

print("Loading datasets...")
df_employees = pd.read_csv(os.path.join(data_dir, 'employees.csv'))
df_subs = pd.read_csv(os.path.join(data_dir, 'subscriptions.csv'))
df_usage = pd.read_csv(os.path.join(data_dir, 'usage_logs.csv'))

# 2. Join the tables together (Like a SQL JOIN)
# Merge subscriptions with employee details
df_merged = pd.merge(df_subs, df_employees, on='emp_id', how='left')
# Merge the result with usage logs
df_final = pd.merge(df_merged, df_usage, on=['sub_id', 'emp_id', 'tool_name'], how='left')

# 3. Identify the Waste (The Analytics Logic)
def identify_waste(row):
    if row['status'] == 'Terminated':
        return 'Terminated Employee (Wasted License)'
    elif row['logins_last_30_days'] == 0:
        return 'Zero Usage in 30 Days (Zombie License)'
    return 'Active & Used'

print("Analyzing usage patterns to find wasted spend...")
df_final['waste_category'] = df_final.apply(identify_waste, axis=1)

# 4. Filter for only the wasted subscriptions
df_waste = df_final[df_final['waste_category'] != 'Active & Used'].copy()

# Calculate total wasted money (Annualized)
monthly_waste = df_waste['monthly_cost'].sum()
annual_waste = monthly_waste * 12

print("-" * 30)
print(f"🚨 AUDIT RESULTS 🚨")
print(f"Total Wasted Licenses Found: {len(df_waste)}")
print(f"Total Monthly Waste: ${monthly_waste:,.2f}")
print(f"Total Annual Waste: ${annual_waste:,.2f}")
print("-" * 30)

# 5. Export the clean data for Power BI / Excel
output_file = os.path.join(data_dir, 'identified_waste_report.csv')
df_waste.to_csv(output_file, index=False)
print(f"✅ Clean report saved for Power BI: {output_file}")