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
| Waste categories detected | Zombie licenses + terminated employee accounts + at-risk licenses |
| Audit process | Fully automated — replaces manual spreadsheet review |

---

## How It Works

```
run_pipeline.py orchestrates the full ETL in one command
    ↓
generate_billing_data.py (CSV generation)
    ↓
setup_db.py (SQLite load)
    ↓
analyze_waste.py (SQL + Pandas analysis)
    ↓
Power BI (dashboard + reporting)
```

**Step 1 — Generate** (`generate_billing_data.py`)  
Builds a realistic multi-table billing dataset using Faker — 75 employees across 6 departments, 10 SaaS tools with real pricing, and intentionally injected anomalies: terminated employees still billing, Asana and Monday.com both assigned to Marketing, Tableau pushed to HR and Finance at random.

**Step 2 — Load** (`setup_db.py`)  
Ingests the three CSVs (`employees`, `subscriptions`, `usage_logs`) into a normalized SQLite database using `pandas.to_sql`. Includes schema validation, row-count reconciliation, and foreign-key integrity checks before committing.

**Step 3 — Analyse** (`analyze_waste.py`)  
Joins all three tables via a single SQL query inside Python, applies `.env`-configured business rules to classify waste into three tiers (Terminated, Zombie, At-Risk), logs every execution step, and exports three CSVs: detail report, department rollup, and tool rollup.

**Step 4 — Report** (`setup_powerbi_views.sql`)  
Injects two SQL views directly into the database — `vw_wasted_licenses_detail` (row-level) and `vw_executive_waste_summary` (aggregated by tool with annualised cost) — so Power BI connects to pre-calculated, always-current data.

---

## Waste Detection Logic

Three tiers are flagged, all configurable via `.env`:

- **Terminated employee** — employee status is `Terminated` but subscription remains `Active`
- **Zombie license** — active paid seat, zero logins in the past N days (`INACTIVITY_THRESHOLD_DAYS=30`)
- **At-risk license** — active paid seat, 1–4 logins in the past N days (`LOW_USAGE_THRESHOLD=4`)

Business rules are fully decoupled from the codebase so they can be adjusted without touching Python.

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

All joins are validated before commit; orphaned subscription IDs are logged as warnings.

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

pip install -r requirements.txt

python scripts/run_pipeline.py
```

Optional flags:

```bash
python scripts/run_pipeline.py --skip-gen      # re-run on existing CSVs
python scripts/run_pipeline.py --only-analyze  # re-run analytics only
```

Output: `data/identified_waste_report.csv` + `data/dept_rollup.csv` + `data/tool_rollup.csv` — connect directly to Power BI.

---

## Project Structure

```
subscan-saas-analyzer/
├── scripts/
│   ├── run_pipeline.py            # One-command orchestrator with CLI flags
│   ├── generate_billing_data.py   # Synthetic dataset with injected anomalies
│   ├── setup_db.py                # CSV to SQLite with validation + integrity checks
│   ├── analyze_waste.py           # Core analytics engine, three-tier classifier
│   └── setup_powerbi_views.sql    # vw_executive_waste_summary + vw_wasted_licenses_detail
├── data/
│   └── (empty on init — all generated by run_pipeline.py)
├── .gitignore
├── requirements.txt
├── dashboard.png.png
└── README.md
```

---

**Yash Bhusari** — [LinkedIn](https://www.linkedin.com/in/yash-bhusari) · [GitHub](https://github.com/Yash-BP)