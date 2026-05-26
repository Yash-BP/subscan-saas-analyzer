# SubScan — SaaS Subscription Waste Analyzer

Identified **$35,064 in annualised wasted software spend** across a simulated 75-employee company using a Python + SQL ETL pipeline and Power BI dashboard.

---

## The Problem

Companies bleed money through SaaS subscriptions that no one uses — terminated employees still billing, paid seats sitting idle, tools provisioned to departments that don't need them. Finance teams have no automated way to catch it.

SubScan automates the audit entirely.

---

## Business Results

| Metric | Result |
|---|---|
| Annualised waste identified | $35,064 |
| Monthly waste identified | $2,922 |
| Subscriptions audited | 375 across 75 employees |
| Waste categories detected | Zombie licenses + terminated employee accounts |
| Audit process | Fully automated — replaces manual spreadsheet review |

---

## How It Works

```
generate_billing_data.py  →  setup_db.py  →  analyze_waste.py  →  Power BI
       (CSV generation)       (SQLite load)    (SQL + Pandas)     (Dashboard)
```

**Step 1 — Generate** (`generate_billing_data.py`)  
Builds a realistic multi-table billing dataset using Faker — 75 employees across 6 departments, 10 SaaS tools with real pricing, and intentionally injected anomalies: terminated employees still billing, Asana and Monday.com both assigned to Marketing, Tableau pushed to HR and Finance at random.

**Step 2 — Load** (`setup_db.py`)  
Ingests the three CSVs (`employees`, `subscriptions`, `usage_logs`) into a normalized SQLite database using `pandas.to_sql`.

**Step 3 — Analyse** (`analyze_waste.py`)  
Joins all three tables via SQL queries inside Python, applies `.env`-configured business rules to classify waste, logs every execution step to `execution_audit.log`, and exports `identified_waste_report.csv` for Power BI.

**Step 4 — Report** (`setup_powerbi_views.sql`)  
Injects two SQL views directly into the database — `vw_wasted_licenses_detail` (row-level) and `vw_executive_waste_summary` (aggregated by tool with annualised cost) — so Power BI connects to pre-calculated, always-current data.

---

## Waste Detection Logic

Two categories are flagged, both configurable via `.env`:

- **Zombie license** — active paid seat, zero logins in the past 30 days (`INACTIVITY_THRESHOLD_DAYS=30`)
- **Terminated employee** — employee status is `Terminated` but subscription remains `Active`

The inactivity threshold is decoupled from the codebase so business rules can be adjusted without touching any Python.

---

## Database Schema

Three normalized tables:

```
employees       subscriptions        usage_logs
----------      -------------        ----------
emp_id    <──── emp_id               sub_id
name            sub_id  <────────── sub_id
department      tool_name            emp_id
status          monthly_cost         tool_name
email           license_status       last_login_date
                                     logins_last_30_days
```

---

## Power BI Views

`vw_wasted_licenses_detail` — employee-level detail: name, department, tool, monthly cost, last login, login count. Filtered to active subscriptions with zero usage.

`vw_executive_waste_summary` — aggregated by tool: unused license count, total monthly waste, total annualised waste. Ordered by cost descending — Salesforce and HubSpot surface first.

---

## Tech Stack

| Tool | Role |
|---|---|
| Python | ETL orchestration, logging, environment config |
| SQLite + SQL | Relational data storage, JOIN queries, Power BI views |
| Pandas | Table merging, business rule application, CSV export |
| Faker | Realistic synthetic dataset generation |
| python-dotenv | Business rule config decoupled from codebase |
| Power BI + Excel | Stakeholder dashboard and cut-list reporting |

---

## Quickstart

```bash
git clone https://github.com/Yash-BP/subscan-saas-analyzer.git
cd subscan-saas-analyzer

pip install pandas faker python-dotenv

python scripts/generate_billing_data.py
python scripts/setup_db.py
python scripts/analyze_waste.py
```

Output: `data/identified_waste_report.csv` — connect directly to Power BI.

To inject the executive views: `python scripts/run_sql.py`

---

## Project Structure

```
subscan-saas-analyzer/
├── scripts/
│   ├── generate_billing_data.py   # Synthetic dataset with injected anomalies
│   ├── setup_db.py                # CSV to SQLite ingestion
│   ├── analyze_waste.py           # Core analytics engine
│   ├── setup_powerbi_views.sql    # vw_executive_waste_summary + vw_wasted_licenses_detail
│   └── run_sql.py                 # View injection runner
├── data/
│   ├── employees.csv
│   ├── subscriptions.csv
│   ├── usage_logs.csv
│   └── identified_waste_report.csv
├── .env.example
└── README.md
```

---

**Yash Bhusari** — [LinkedIn](https://www.linkedin.com/in/yash-bhusari) · [GitHub](https://github.com/Yash-BP)
