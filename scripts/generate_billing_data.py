import pandas as pd
from faker import Faker
import random
import os
from datetime import datetime, timedelta

# Set up Faker and random seed for reproducibility
fake = Faker()
Faker.seed(42)
random.seed(42)

# Ensure the data directory exists
script_dir = os.path.dirname(os.path.abspath(__file__))
data_dir = os.path.join(script_dir, '..', 'data')
os.makedirs(data_dir, exist_ok=True)

# 1. Define the SaaS Stack & Pricing (Monthly)
saas_tools = {
    'Slack': 15,
    'Zoom': 20,
    'Notion': 12,
    'Asana': 25,
    'Monday.com': 30,  # Intentional overlap with Asana
    'Figma': 45,
    'Tableau': 70,
    'Salesforce': 150,
    'HubSpot': 90,
    'Adobe CC': 80
}

departments = ['Engineering', 'Marketing', 'Sales', 'Design', 'HR', 'Finance']

# 2. Generate Employees
print("Generating employees...")
num_employees = 75
employees = []
for _ in range(num_employees):
    employees.append({
        'emp_id': fake.unique.random_int(min=1000, max=9999),
        'name': fake.name(),
        'email': fake.company_email(),
        'department': random.choice(departments),
        'status': random.choices(['Active', 'Terminated'], weights=[0.9, 0.1])[0] # Terminated employees still consuming licenses!
    })

df_employees = pd.DataFrame(employees)

# 3. Assign Subscriptions & Generate Usage Logs
print("Assigning subscriptions and generating usage logs...")
subscriptions = []
usage_logs = []

today = datetime.today()

for _, emp in df_employees.iterrows():
    # Base tools for everyone
    assigned_tools = ['Slack', 'Zoom']
    
    # Department specific tools + Intentional Waste
    if emp['department'] == 'Design':
        assigned_tools.extend(['Figma', 'Adobe CC', 'Notion'])
    elif emp['department'] == 'Sales':
        assigned_tools.extend(['Salesforce', 'Zoom', 'HubSpot']) # Zoom duplicated intentionally sometimes
    elif emp['department'] == 'Engineering':
        assigned_tools.extend(['Asana', 'Notion'])
    elif emp['department'] == 'Marketing':
        # Waste: Giving Marketing both Asana and Monday.com
        assigned_tools.extend(['Asana', 'Monday.com', 'HubSpot', 'Figma']) 
    elif emp['department'] in ['HR', 'Finance']:
        assigned_tools.extend(['Asana'])
        if random.random() > 0.7:
            assigned_tools.append('Tableau') # Expensive tool given to people who might not need it

    # Remove duplicates just in case base logic overlapped
    assigned_tools = list(set(assigned_tools))

    for tool in assigned_tools:
        # Create subscription record
        sub_id = f"SUB-{fake.unique.random_int(min=10000, max=99999)}"
        subscriptions.append({
            'sub_id': sub_id,
            'emp_id': emp['emp_id'],
            'tool_name': tool,
            'monthly_cost': saas_tools[tool],
            'license_status': 'Active'
        })

        # Generate Usage Data
        if emp['status'] == 'Terminated':
            days_since_login = random.randint(60, 180)
            logins_last_30_days = 0
        else:
            if random.random() > 0.85: 
                days_since_login = random.randint(31, 100)
                logins_last_30_days = 0
            else:
                days_since_login = random.randint(0, 10)
                logins_last_30_days = random.randint(5, 40)

        last_login_date = today - timedelta(days=days_since_login)
        
        usage_logs.append({
            'sub_id': sub_id,
            'emp_id': emp['emp_id'],
            'tool_name': tool,
            'last_login_date': last_login_date.strftime('%Y-%m-%d'),
            'logins_last_30_days': logins_last_30_days
        })

df_subs = pd.DataFrame(subscriptions)
df_usage = pd.DataFrame(usage_logs)

# 4. Save to CSV in the data folder
print("Saving files to /data directory...")
df_employees.to_csv(os.path.join(data_dir, 'employees.csv'), index=False)
df_subs.to_csv(os.path.join(data_dir, 'subscriptions.csv'), index=False)
df_usage.to_csv(os.path.join(data_dir, 'usage_logs.csv'), index=False)

print("✅ Data generation complete! Check your 'data' folder.")