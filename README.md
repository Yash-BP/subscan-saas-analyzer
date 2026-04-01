# SubScan — SaaS Subscription Waste Analyzer

> **Identified $35,064 in annualised wasted software spend** inside a simulated 75-employee company using an automated Python + SQL ETL pipeline and Power BI dashboard.

---

## The Problem

Companies accumulate wasteful SaaS spending through unused seats, failed employee offboarding, and forgotten trial conversions. Finance teams lack a single automated view to catch it — so it quietly bleeds every month.

SubScan fixes that.

---

## Business Value

| Metric | Result |
|---|---|
| Annualised waste identified | **$35,064** |
| Monthly waste identified | **$2,922** |
| Total subscriptions audited | **75** |
| Waste categories detected | Zombie Licenses + Terminated Employee Accounts |
| Audit process | Fully automated — replaces manual spreadsheet review |

---

## Dashboard Preview

![SubScan Dashboard Preview](dashboard.png)

> The dashboard surfaces every wasted license by employee name, tool, department, and monthly cost — giving finance teams a ready-to-act cut-list in seconds.

---

## How It Works

```
Raw Billing CSVs  →  SQLite Database  →  Analytics Engine  →  Power BI Dashboard
```

1. **Generate** — Creates a realistic multi-table billing dataset with injected anomalies
2. **Load** — Ingests raw CSVs into a local SQLite relational database
3. **Analyse** — Applies business rules to detect waste, logs every execution step
4. **Report** — Exports a clean `identified_waste_report.csv` consumed by Power BI

---

## Waste Categories Detected

- **Zombie Licenses** — Active paid seats with zero logins recorded in the past 30 days
- **Terminated Employee Accounts** — Subscriptions still billing for offboarded staff

### Top Wasted Tools (from dashboard)

| Tool | Monthly Waste | Waste Type |
|---|---|---|
| Salesforce | Highest | Zombie Licenses + Terminated Employees |
| HubSpot | High | Zombie Licenses + Terminated Employees |
| Tableau | Medium | Zombie Licenses |
| Adobe CC | Medium | Zombie Licenses |
| Figma | Medium | Zombie Licenses + Terminated Employees |
| Zoom | Medium | Zombie Licenses |

---

## Tech Stack

| Tool | Role |
|---|---|
| Python | Core ETL logic, automated logging, environment config |
| SQLite + SQL | Relational database storage and querying |
| Pandas | Data transformation, table merging, business rule execution |
| python-dotenv | Secure decoupling of business rules from codebase |
| Power BI / Excel | Stakeholder dashboard and final reporting |

---

## Project Structure

```
SubScan/
│
├── scripts/
│   ├── generate_billing_data.py     # Builds realistic multi-table dataset with anomalies
│   ├── setup_db.py                  # Ingests CSVs into local SQLite database
│   └── analyze_waste.py             # Core analytics engine — SQL queries + business logic
│
├── data/
│   ├── company_database.db          # Local SQLite database (generated)
│   └── identified_waste_report.csv  # Final output consumed by Power BI
│
├── .env                             # Business rule config — git ignored
├── execution_audit.log              # Timestamped run logs — git ignored
├── requirements.txt
└── README.md
```

---

## Quickstart

```bash
# 1. Clone the repo
git clone https://github.com/Yash-BP/subscan.git
cd subscan

# 2. Install dependencies
pip install pandas faker python-dotenv

# 3. Generate the raw billing dataset
python scripts/generate_billing_data.py

# 4. Build the SQLite database
python scripts/setup_db.py

# 5. Run the analytics engine
python scripts/analyze_waste.py
```

Output: `data/identified_waste_report.csv` — ready to connect to Power BI.

---

## Enterprise-Ready Design

This pipeline is built for real corporate deployment, not just a demo:

- **Secure config** — Business rules (e.g. inactivity thresholds) stored in `.env` variables, fully decoupled from the codebase
- **Relational database** — Queries a structured SQLite DB rather than static flat files, mirroring production data environments
- **Execution logging** — Python's `logging` library generates timestamped audit logs for every pipeline run
- **Live dashboarding** — Power BI connects directly to the pipeline output for an always-current view of software spend

---

## Author

**Yash Bhusari** — Aspiring Data Analyst  
[LinkedIn](https://linkedin.com/in/yash-bhusari-0b83a6282) · [GitHub](https://github.com/Yash-BP)