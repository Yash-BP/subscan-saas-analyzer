"""
generate_billing_data.py  (Phase 1 Upgrade)
────────────────────────────────────────────
Builds all four CSV files that SubScan needs:
  - employees.csv
  - subscriptions.csv
  - usage_logs.csv          (unchanged — single snapshot, still used by existing views)
  - historical_usage_logs.csv  ← NEW: 12 months per subscription for cohort analysis

January Cohort Anomaly (intentional, for recruiter to spot):
  Employees whose subscription started in January use Salesforce heavily for
  the first two months, then 40% of them drop to 0 logins from month 3 onward.
  This simulates "feature adoption stagnation."
"""

import os
import random
from datetime import date, timedelta

import pandas as pd
from faker import Faker

# ── Reproducible output ───────────────────────────────────────────────────────
SEED = 42
random.seed(SEED)
fake = Faker()
Faker.seed(SEED)

# ── Constants ─────────────────────────────────────────────────────────────────
NUM_EMPLOYEES  = 75
DEPARTMENTS    = ["Engineering", "Sales", "Marketing", "HR", "Finance", "Operations"]

# Tools with their monthly cost per seat
TOOLS = {
    "Salesforce":  45,
    "HubSpot":     50,
    "Slack":       8,
    "Asana":       12,
    "Jira":        10,
    "Zoom":        15,
    "Tableau":     70,
    "Monday.com":  14,
    "Notion":      8,
    "Workday":     40,
}

# Which departments get which tools (realistic allocation)
DEPT_TOOLS = {
    "Engineering":  ["Jira", "Slack", "Zoom", "Notion"],
    "Sales":        ["Salesforce", "HubSpot", "Slack", "Zoom"],
    "Marketing":    ["HubSpot", "Asana", "Monday.com", "Slack"],  # Both PM tools — intentional waste
    "HR":           ["Workday", "Slack", "Tableau"],               # Tableau in HR — intentional waste
    "Finance":      ["Workday", "Tableau", "Slack"],
    "Operations":   ["Asana", "Slack", "Zoom", "Notion"],
}

# How many months back to generate cohorts (one cohort = one calendar month)
HISTORY_MONTHS = 12


# ── Helpers ───────────────────────────────────────────────────────────────────

def months_back(n: int) -> date:
    """Return the first day of the month that is n months before today."""
    today = date.today()
    month = today.month - n
    year  = today.year + (month - 1) // 12
    month = ((month - 1) % 12) + 1
    return date(year, month, 1)


def add_months(d: date, n: int) -> date:
    """Add n months to a date, returning the first of that month."""
    month = d.month + n
    year  = d.year + (month - 1) // 12
    month = ((month - 1) % 12) + 1
    return date(year, month, 1)


# ── Generation ────────────────────────────────────────────────────────────────

def generate_employees() -> pd.DataFrame:
    rows = []
    for i in range(1, NUM_EMPLOYEES + 1):
        dept   = random.choice(DEPARTMENTS)
        # ~10% terminated employees (intentional waste anomaly)
        status = "Terminated" if random.random() < 0.10 else "Active"
        rows.append({
            "emp_id":     f"E{i:03d}",
            "name":       fake.name(),
            "email":      fake.email(),
            "department": dept,
            "status":     status,
        })
    return pd.DataFrame(rows)


def generate_subscriptions(df_emp: pd.DataFrame) -> pd.DataFrame:
    """
    Each employee gets all tools assigned to their department.
    Returns a DataFrame of all subscriptions and the cohort start month per row.
    """
    rows = []
    sub_id = 1

    for _, emp in df_emp.iterrows():
        tools = DEPT_TOOLS.get(emp["department"], ["Slack"])
        for tool in tools:
            # Cohort month: randomly chosen from the past 12 months
            cohort_offset = random.randint(0, HISTORY_MONTHS - 1)
            cohort_month  = months_back(cohort_offset)

            rows.append({
                "sub_id":         f"S{sub_id:04d}",
                "emp_id":         emp["emp_id"],
                "tool_name":      tool,
                "monthly_cost":   TOOLS[tool],
                "license_status": "Active",
                "cohort_month":   cohort_month.isoformat(),   # used by Phase 1 logic below
            })
            sub_id += 1

    return pd.DataFrame(rows)


def generate_usage_logs(df_subs: pd.DataFrame) -> pd.DataFrame:
    """
    Original single-snapshot usage_logs table.
    Kept for backward compatibility with existing views and analyze_waste.py.
    """
    rows = []
    for _, sub in df_subs.iterrows():
        # ~20% chance of zombie license
        if random.random() < 0.20:
            logins = 0
            last_login = date.today() - timedelta(days=random.randint(45, 120))
        else:
            logins = random.randint(1, 50)
            last_login = date.today() - timedelta(days=random.randint(1, 29))

        rows.append({
            "sub_id":             sub["sub_id"],
            "emp_id":             sub["emp_id"],
            "tool_name":          sub["tool_name"],
            "last_login_date":    last_login.isoformat(),
            "logins_last_30_days": logins,
        })
    return pd.DataFrame(rows)


def generate_historical_usage_logs(df_subs: pd.DataFrame) -> pd.DataFrame:
    """
    NEW TABLE for Phase 1.

    For every subscription, generate one row per month from its cohort_month
    up to today (max 12 months). Each row has a login_count for that month.

    January Cohort Anomaly
    ──────────────────────
    If the cohort_month is in January AND the tool is Salesforce:
      - Month 0 and Month 1: normal heavy usage (15–40 logins)
      - Month 2 onwards:     40% of these employees drop to 0 logins
    This creates a visible "cliff" in the Power BI retention heatmap.
    """
    rows = []

    # Pre-decide which employees are "stagnators" for the Jan/Salesforce anomaly.
    # We pick them randomly but consistently (seed is fixed).
    jan_salesforce_subs = df_subs[
        (df_subs["cohort_month"].str.startswith(str(date.today().year - 1) + "-01") |
         df_subs["cohort_month"].str.startswith(str(date.today().year) + "-01")) &
        (df_subs["tool_name"] == "Salesforce")
    ]["sub_id"].tolist()

    # 40% of them will stagnate at month 3.
    # max(..., 1) guarantees at least 1 stagnator even in small cohorts,
    # so the drop-off is always visible in Power BI.
    if jan_salesforce_subs:
        stagnator_count = max(1, int(len(jan_salesforce_subs) * 0.40))
        stagnators = set(random.sample(jan_salesforce_subs, k=stagnator_count))
    else:
        stagnators = set()

    for _, sub in df_subs.iterrows():
        cohort_date = date.fromisoformat(sub["cohort_month"])

        for month_offset in range(HISTORY_MONTHS):
            billing_month = add_months(cohort_date, month_offset)

            # Don't generate future months
            if billing_month > date.today():
                break

            months_active = month_offset  # 0 = cohort month, 1 = next month, etc.

            # ── January Cohort Anomaly ──────────────────────────────────────
            if sub["sub_id"] in stagnators and months_active >= 2:
                login_count = 0          # stagnated — simulates feature abandonment

            elif sub["sub_id"] in jan_salesforce_subs and months_active < 2:
                login_count = random.randint(15, 40)   # heavy early usage

            # ── Normal behaviour for everyone else ──────────────────────────
            else:
                # Slight decay in logins over time (realistic)
                base = max(1, 30 - months_active * 2)
                login_count = random.randint(0, base)

            rows.append({
                "sub_id":        sub["sub_id"],
                "emp_id":        sub["emp_id"],
                "tool_name":     sub["tool_name"],
                "billing_month": billing_month.isoformat(),
                "login_count":   login_count,
            })

    return pd.DataFrame(rows)


# ── Orchestrator ──────────────────────────────────────────────────────────────

def generate(data_dir: str | None = None) -> None:
    script_dir = os.path.dirname(os.path.abspath(__file__))
    data_dir   = data_dir or os.path.join(script_dir, "..", "data")
    os.makedirs(data_dir, exist_ok=True)

    print("SubScan — generating synthetic data …")

    df_emp  = generate_employees()
    df_subs = generate_subscriptions(df_emp)
    df_usage        = generate_usage_logs(df_subs)
    df_hist_usage   = generate_historical_usage_logs(df_subs)

    # Drop cohort_month from subscriptions before saving
    # (it was only needed internally for the historical generator)
    df_subs_clean = df_subs.drop(columns=["cohort_month"])

    # Save all four CSVs
    df_emp.to_csv(            os.path.join(data_dir, "employees.csv"),              index=False)
    df_subs_clean.to_csv(     os.path.join(data_dir, "subscriptions.csv"),          index=False)
    df_usage.to_csv(          os.path.join(data_dir, "usage_logs.csv"),             index=False)
    df_hist_usage.to_csv(     os.path.join(data_dir, "historical_usage_logs.csv"),  index=False)

    print(f"  employees.csv              → {len(df_emp)} rows")
    print(f"  subscriptions.csv          → {len(df_subs_clean)} rows")
    print(f"  usage_logs.csv             → {len(df_usage)} rows")
    print(f"  historical_usage_logs.csv  → {len(df_hist_usage)} rows")
    print("  ✓ Done — all CSVs written to:", data_dir)


if __name__ == "__main__":
    generate()