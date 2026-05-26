"""
generate_billing_data.py
────────────────────────
Generates a realistic, reproducible multi-table SaaS billing dataset for
SubScan analysis. Improvements over v1:

  • Config-driven via dataclasses — no magic numbers scattered in logic
  • Richer anomaly injection: duplicate tools, over-licensed departments,
    terminated-but-not-offboarded staff, and partial-usage ghosts
  • Precise random seeding on a local Random instance — doesn't pollute
    the global random state
  • Typed DataFrames with explicit dtypes on export for clean SQLite ingestion
  • Structured console output with per-step summaries
"""

import os
import random
import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Dict, List

import pandas as pd
from faker import Faker

# ── Configuration ─────────────────────────────────────────────────────────────

@dataclass
class DataConfig:
    seed: int = 42
    num_employees: int = 75
    terminated_rate: float = 0.08          # 8% of workforce terminated
    zombie_rate: float = 0.18              # 18% of active subs go unused
    partial_usage_rate: float = 0.12       # 12% low-usage (1-4 logins) — new category
    inactivity_days_min: int = 31
    inactivity_days_max: int = 120
    active_days_min: int = 0
    active_days_max: int = 8
    output_dir: str = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data")

    # SaaS catalogue: tool → monthly_cost_per_seat (INR analogue in USD)
    saas_catalogue: Dict[str, int] = field(default_factory=lambda: {
        "Slack": 15,
        "Zoom": 20,
        "Notion": 12,
        "Asana": 25,
        "Monday.com": 30,
        "Figma": 45,
        "Tableau": 70,
        "Salesforce": 150,
        "HubSpot": 90,
        "Adobe CC": 80,
        "Jira": 10,          # New tool — common in engineering
        "GitHub": 21,        # New tool — common in engineering
    })

    departments: List[str] = field(default_factory=lambda: [
        "Engineering", "Marketing", "Sales", "Design", "HR", "Finance"
    ])

    # Maps department → tools that department should get
    dept_tool_map: Dict[str, List[str]] = field(default_factory=lambda: {
        "Engineering": ["Slack", "Zoom", "Asana", "Notion", "Jira", "GitHub"],
        "Marketing":   ["Slack", "Zoom", "Asana", "Monday.com", "HubSpot", "Figma"],
        "Sales":       ["Slack", "Zoom", "Salesforce", "HubSpot"],
        "Design":      ["Slack", "Zoom", "Figma", "Adobe CC", "Notion"],
        "HR":          ["Slack", "Zoom", "Asana"],
        "Finance":     ["Slack", "Zoom", "Asana", "Tableau"],
    })

    # Departments that sometimes get an expensive tool they don't need
    tableau_bonus_depts: List[str] = field(default_factory=lambda: ["HR", "Finance"])
    tableau_bonus_prob: float = 0.30  # 30% chance Finance/HR gets Tableau

# ── Logging ───────────────────────────────────────────────────────────────────

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("subscan.generate")

# ── Generator ─────────────────────────────────────────────────────────────────

def generate(cfg: DataConfig) -> None:
    rng = random.Random(cfg.seed)
    fake = Faker("en_IN")
    Faker.seed(cfg.seed)

    today = datetime.today()
    os.makedirs(cfg.output_dir, exist_ok=True)

    # ── 1. Employees ──────────────────────────────────────────────────────────
    log.info("Generating %d employees …", cfg.num_employees)
    employees = []
    for _ in range(cfg.num_employees):
        status = (
            "Terminated"
            if rng.random() < cfg.terminated_rate
            else "Active"
        )
        employees.append({
            "emp_id":     rng.randint(1000, 9999),
            "name":       fake.unique.name(),
            "email":      fake.company_email(),
            "department": rng.choice(cfg.departments),
            "status":     status,
        })

    df_employees = pd.DataFrame(employees).astype({
        "emp_id":     "int64",
        "name":       "string",
        "email":      "string",
        "department": "string",
        "status":     "string",
    })

    terminated = (df_employees["status"] == "Terminated").sum()
    log.info("  Active: %d  |  Terminated: %d", len(df_employees) - terminated, terminated)

    # ── 2. Subscriptions + Usage Logs ─────────────────────────────────────────
    log.info("Assigning subscriptions and generating usage logs …")

    subscriptions, usage_logs = [], []
    used_sub_ids: set = set()

    def unique_sub_id() -> str:
        while True:
            sid = f"SUB-{rng.randint(10000, 99999)}"
            if sid not in used_sub_ids:
                used_sub_ids.add(sid)
                return sid

    anomaly_counts = {"zombie": 0, "terminated": 0, "partial": 0, "duplicate_tool": 0}

    for _, emp in df_employees.iterrows():
        tools = list(cfg.dept_tool_map.get(emp["department"], ["Slack", "Zoom"]))

        # Anomaly: duplicate tool overlap for Marketing (Asana + Monday.com both assigned)
        # — already in the dept_tool_map, intentional.

        # Anomaly: occasionally give Tableau to HR/Finance employees (over-licensing)
        if emp["department"] in cfg.tableau_bonus_depts:
            if rng.random() < cfg.tableau_bonus_prob and "Tableau" not in tools:
                tools.append("Tableau")
                anomaly_counts["duplicate_tool"] += 1

        for tool in tools:
            sub_id = unique_sub_id()

            # ── Determine login pattern ────────────────────────────────────────
            if emp["status"] == "Terminated":
                # Terminated employee: account still active, no recent logins
                days_since = rng.randint(45, 180)
                logins = 0
                anomaly_counts["terminated"] += 1

            elif rng.random() < cfg.zombie_rate:
                # Zombie: active employee, zero logins in past 30 days
                days_since = rng.randint(cfg.inactivity_days_min, cfg.inactivity_days_max)
                logins = 0
                anomaly_counts["zombie"] += 1

            elif rng.random() < cfg.partial_usage_rate:
                # Partial: technically used but barely — worth flagging separately
                days_since = rng.randint(5, 25)
                logins = rng.randint(1, 4)
                anomaly_counts["partial"] += 1

            else:
                # Healthy usage
                days_since = rng.randint(cfg.active_days_min, cfg.active_days_max)
                logins = rng.randint(5, 40)

            last_login = (today - timedelta(days=days_since)).strftime("%Y-%m-%d")

            subscriptions.append({
                "sub_id":         sub_id,
                "emp_id":         emp["emp_id"],
                "tool_name":      tool,
                "monthly_cost":   cfg.saas_catalogue[tool],
                "license_status": "Active",
            })
            usage_logs.append({
                "sub_id":              sub_id,
                "emp_id":              emp["emp_id"],
                "tool_name":           tool,
                "last_login_date":     last_login,
                "logins_last_30_days": logins,
            })

    df_subs = pd.DataFrame(subscriptions).astype({
        "sub_id":         "string",
        "emp_id":         "int64",
        "tool_name":      "string",
        "monthly_cost":   "int64",
        "license_status": "string",
    })
    df_usage = pd.DataFrame(usage_logs).astype({
        "sub_id":              "string",
        "emp_id":              "int64",
        "tool_name":           "string",
        "last_login_date":     "string",
        "logins_last_30_days": "int64",
    })

    # ── 3. Summary ────────────────────────────────────────────────────────────
    total_monthly = df_subs["monthly_cost"].sum()
    log.info("  Total subscriptions: %d  |  Total monthly spend: $%d", len(df_subs), total_monthly)
    log.info(
        "  Anomalies injected — zombie: %d | terminated: %d | partial: %d | over-licensed: %d",
        anomaly_counts["zombie"], anomaly_counts["terminated"],
        anomaly_counts["partial"], anomaly_counts["duplicate_tool"],
    )

    # ── 4. Export ─────────────────────────────────────────────────────────────
    paths = {
        "employees":    os.path.join(cfg.output_dir, "employees.csv"),
        "subscriptions": os.path.join(cfg.output_dir, "subscriptions.csv"),
        "usage_logs":   os.path.join(cfg.output_dir, "usage_logs.csv"),
    }
    df_employees.to_csv(paths["employees"],    index=False)
    df_subs.to_csv(paths["subscriptions"],     index=False)
    df_usage.to_csv(paths["usage_logs"],       index=False)

    log.info("Data saved to: %s", cfg.output_dir)
    log.info("✓ Data generation complete.")


if __name__ == "__main__":
    generate(DataConfig())