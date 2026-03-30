# 🔍 SubScan: SaaS Subscription Waste Analyzer

SubScan solves a major business headache: wasted software spend. It uses Python to audit SaaS billing data and flag unused licenses. These insights are transformed into a clean Power BI dashboard and Excel report, giving stakeholders a prioritized cut-list to instantly reduce hidden costs and improve their company's bottom line.

## 🎯 Business Value Demonstrated
* **Cost Reduction:** Identified **$35,064** in annualized wasted spend within a simulated 75-employee company.
* **Process Automation:** Built a reproducible Python pipeline to replace manual spreadsheet auditing.
* **Actionable Insights:** Categorized waste into "Zombie Licenses" (zero usage) and "Terminated Employees" (failed offboarding).

## 🛠️ Tech Stack
* **Python:** Core logic, synthetic data generation (`Faker`), and pipeline execution.
* **Pandas:** Data ingestion, table joins (simulating SQL logic), and data cleaning.
* **Power BI / Excel:** Final stakeholder reporting and visualization *(Dashboard in progress)*.

## 📁 Project Structure
* `/scripts/generate_billing_data.py`: Engineers a realistic, multi-table relational dataset (Employees, Subscriptions, Usage Logs) with intentionally injected business anomalies.
* `/scripts/analyze_waste.py`: The analytics engine. Merges tables and applies business logic to categorize and calculate wasted spend.
* `/data/`: Contains the generated CSVs and the final `identified_waste_report.csv`.

## 🚀 How to Run
1. Clone the repository.
2. Install requirements: `pip install pandas faker`
3. Generate the data: `python scripts/generate_billing_data.py`
4. Run the audit: `python scripts/analyze_waste.py`